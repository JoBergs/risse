# -*- coding: utf-8 -*-

from risse.spiders.base import *

DATA = './data.txt'


class DoratSpider(RisseSpider):
    name = "dorat"

    def parse_iframe(self, response):
        """ Parse the site for URLs to Anlagen and form requests for them.
        Site: https://dosys01.digistadtdo.de/dosys/gremrech.nsf/(embAttOrg)?OpenView&RestrictToCategory=C1256F35004CEDB0C12582580023CA24"""

        # e.g. <a href="https://dosys01.digistadtdo.de/dosys/gremrech.nsf/(embAttOrg)/98540772714EEE7DC125825800281C7E/%24FILE/EA%20zu%20TOP%2010.4.pdf?OpenElement" target="_blank">EA zu TOP 10.4.pdf</a>
        links = response.xpath('//a[contains(@href, "pdf?OpenElement")]')

        for i in range(len(links)):
            request = self.build_request(response.urljoin(links[i].attrib['href']), self.save_pdf, 
                os.path.join(response.meta['path'], links[i].attrib['href'].split('/')[-1].rstrip('?OpenElement')))

            yield request

    def parse_drucksache(self, response):
        """ Check if a Drucksache has a link to Anlangen. If so, form a request for it.
        Site: https://dosys01.digistadtdo.de/dosys/gremrech.nsf/TOPWEB/09848-18-E1"""

        self.create_directories(os.path.join(*response.meta['path'], response.meta['id']))

        # not all Drucksachen have attachments
        try:
            # e.g. <iframe src="https://dosys01.digistadtdo.de/dosys/gremrech.nsf/(embAttOrg)?OpenView&amp;RestrictToCategory=C1256F35004CEDB0C12582580023CA24" height="250" width="600" name="unterfenster" marginheight="0" marginwidth="0" frameborder="0">Alternativtext</iframe>
            iframe = response.xpath('//iframe').attrib["src"]

            request = self.build_request(iframe, self.parse_iframe, 
                os.path.join(*response.meta['path'], response.meta['id']))

            yield request
        except:
            pass

    def parse_niederschrift(self, response):
        """ Check if a Sitzung fits in the CLI data range. If so, store its HTML and
        generate requests for all Anlagen.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/034bc6e876399f96c1256e1d0035a1e9/c1256a150047cd47c1256b7a00291f6d?OpenDocument """

        # move this into base class
        name = self.mapping.get(response.meta['name'], response.meta['name'])
        date = response.meta['date'].split('.')

        # /root-path-for-documents/2019/name-of-commitee/2019-03-28/Number-of-Topic/
        path = [self.root, date[-1], name, '-'.join(date[::-1])]

        self.create_directories(os.path.join(*path))

        # store the text of the Sitzung
        self.save_file(os.path.join(*path, name + '.html'), response.text, True) 

        for request in self.build_drucksache_requests(response, path):
            yield request

    def build_drucksache_requests(self, response, path):
        """ Scan a Sitzung for Drucksachen and build requests for them.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/034bc6e876399f96c1256e1d0035a1e9/e0904ca267a306b1c125829c003fb320?OpenDocument"""

        requests = []

        base_url = 'https://dosys01.digistadtdo.de/dosys/gremrech.nsf/TOPWEB/'
        # e.g. <font size="2" face="Arial">\t(Drucksache Nr.: 10033-18)  </font>
        ids = response.xpath('//font/text()').re(r'\(Drucksache Nr.: (\S*)\)')

        for drucksache in ids:
            request = self.build_request(base_url + drucksache, self.parse_drucksache, path)
            request.meta['id'] = drucksache

            requests.append(request)

        return requests

    def generate_niederschrift_requests(self, response, data):
        """Build requests to scrape all Niederschriften found on a specific page
        with extract_page_data.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&Start=1.29&ExpandView"""

        requests = []

        for niederschriften in data:
            name = niederschriften[0]
            for niederschrift in niederschriften[1]:
                request = self.build_request(response.urljoin(niederschrift[1]), 
                    self.parse_niederschrift, '')
                request.meta['name'] = name
                request.meta['date'] = niederschrift[0]

                requests.append(request)

        return requests

    def parse_page(self, response):
        """ Function for parsing a single page of Niederschriften and then
        opening the next page.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&Start=1.29&ExpandView"""

        data  = self.extract_page_data(response)

        for request in self.generate_niederschrift_requests(response, data):
            yield request

        # e.g. <a href="/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&amp;Start=1.58&amp;ExpandView"><b><font size="2" color="#000080" face="Arial">&gt;&gt;</font></b></a>
        next_page = response.xpath('//*[.=">>"]/parent::*/a') 
        if next_page is not None:
            request = self.build_request(response.urljoin(next_page.attrib['href']), 
                self.parse_page, '')
            request.meta['name'] = data[-1][0]

            yield request   

    def extract_page_data(self, response):
        """ Function for extracting all niederschriften from a given page.
        # The result is a list [(GremiumName, [(NiederschriftDatum, NiederschriftURL)])]
        Site:  https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&Start=1.29&ExpandView"""

        data = [(response.meta['name'], [])]  # (name,[(url, date), ...])
        rows = response.xpath('//tr/td/font | //tr/td/a/img').getall()

        for row in rows:
            if "Details verbergen für" in row:
                name = row.split("Details verbergen für ")[-1].split('"')[0]
                if name != data[-1][0]:
                    data.append((name, []))
            elif "Niederschrift (öffentlich)" in row:
                date = row.split("Niederschrift (öffentlich), ")[-1].split('<')[0]
                url = row.split('<font size="2"><a href="')[-1].split('"')[0]
                day, month, year = date.split('.')
                if (self.month == None or month.lstrip('0') == self.month) and \
                        (self.year == None or year == self.year):

                    data[-1][1].append((date, url))

        return data

    def parse_all(self, response):
        """ In order to start the scraping prozess, the name of the first Gremium
        is required. This function extracts it and starts the page scraping. """

        # e.g. <img src="/dosys/gremniedweb1.nsf/%24PlusMinus?OpenImageResource&amp;ImgIndex=1" border="0" alt="Details verbergen für Rat der Stadt">
        name = response.xpath('//img[contains(@alt, "Details verbergen für")]').attrib['alt'].lstrip("Details verbergen für")
        response.meta['name'] = name
        for request in self.parse_page(response):
            yield request

    def parse(self, response):
        """ Find the URL that opens the detailed view of all Gremien and form a request.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView """

        url = '/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView'
        yield self.build_request(response.urljoin(url), self.parse_all, '')
