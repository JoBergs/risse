# -*- coding: utf-8 -*-

from risse.spiders.base import *


class DortmundSpider(RisseSpider):
    name = "dortmund"

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

            # request = scrapy.Request(iframe, callback=self.parse_iframe)
            request = self.build_request(iframe, self.parse_iframe, 
                os.path.join(*response.meta['path'], response.meta['id']))
            # request.meta['path'] = os.path.join(*response.meta['path'], response.meta['id'])

            yield request
        except:
            pass

    def parse_sitzung(self, response):
        """ Check if a Sitzung fits in the CLI data range. If so, store its HTML and
        generate requests for all Anlagen.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/034bc6e876399f96c1256e1d0035a1e9/c1256a150047cd47c1256b7a00291f6d?OpenDocument """


        # move this into base class
        name = self.mapping.get(response.meta['name'], response.meta['name'])
        date = response.meta['date'].split('.')


        # if "Hauptausschuss und Ältestenrat" in response.meta['name']:
        #     print(date)
        #     print((self.month == None or date[1].lstrip('0') == self.month) and \
        #         (self.year == None or date[-1] == self.year))
        #     import ipdb
        #     ipdb.set_trace()

        # move into base class in all scrapers
        if (self.month == None or date[1].lstrip('0') == self.month) and \
                (self.year == None or date[-1] == self.year):

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

    def parse_gremien(self, response):
        """ Function to parse all Gremien on all pages.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView """

        # e.g. <a href="/dosys/gremniedweb1.nsf/034bc6e876399f96c1256e1d0035a1e9/764a822ae6adae29c125840700252a09?OpenDocument"><b><script language="JavaScript">\nfunction NeuFenster764A822AE6ADAE29C125840700252A09()\n{\nMeinFenster =\n window.open("dosys\\gremniedweb1.nsf/NiederschriftenWeb/764A822AE6ADAE29C125840700252A09?OpenDocument", "Zweitfenster", "width=800,height=600,toolbar=no,userbar=no,location=no,status=no,menubar=no,scrollbars,offsetX=5,offsetY=5 ");\n MeinFenster.focus();\n}\n</script>\n<a href="javascript:NeuFenster764A822AE6ADAE29C125840700252A09()">Festgestellte Tagesordnung (öffentlich), 23.05.2019</a></b> <br></a>
        links = response.xpath('//a[contains(@href, "OpenDocument")]')
        # e.g. <a href="javascript:NeuFenster764A822AE6ADAE29C125840700252A09()">Festgestellte Tagesordnung (öffentlich), 23.05.2019</a>
        dates = links.xpath('//a[contains(@href, "javascript")]/text()').getall() 

        name = response.meta.get('name', None)

        for request in self.parse_gremium(response, name, links, dates):
            yield request

        yield self.parse_next_page(response, name)

    def parse_gremium(self, response, name, links, dates):
        """ Function to make a request for parsing every Sitzung of the current Gremium.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView """
        requests = []

        # this function does not do what it should
        #   e.g.: what happens if there are two Details verbergen images on one page
        #   also, the name doesn't need to be calculated frequently, once is enough
        #   i might need a different control logic
        #   like, name found? if so, iterate over pages until the next name is found

        for i in range(len(links)):
            if "Tagesordnung" not in links[i].get():
                request = self.build_request(response.urljoin(links[i].attrib['href']), 
                    self.parse_sitzung, '')

                # e.g. <img src="/dosys/gremniedweb1.nsf/%24PlusMinus?OpenImageResource&amp;ImgIndex=1" border="0" alt="Details verbergen für Rat der Stadt">
                tmp = response.xpath('//img[contains(@alt, "Details verbergen für")]')
                if tmp != []:
                    name = tmp.attrib['alt'].lstrip("Details verbergen für")

                # try:
                #     print(response.xpath('//img[contains(@alt, "Details verbergen für")]').get())
                #     print(name)
                # except:
                #     pass

                request.meta['name'] = name
                request.meta['date'] = dates[i].lstrip("Niederschrift (öffentlich), ")

                requests.append(request)

        return requests

    def parse_next_page(self, response, name):
        """ Function to make a request for parsing the next page.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView """

        # e.g. '<a href="/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&amp;Start=1.29&amp;ExpandView"><b><font size="2" color="#000080" face="Arial">&gt;&gt;</font></b></a>'
        next_page = response.xpath('//*[.=">>"]/parent::*/a') 
        if next_page is not None:
            request = self.build_request(response.urljoin(next_page.attrib['href']), 
                self.parse_gremien, '')
            request.meta['name'] = name

            return request

    def parse(self, response):
        """ Find the URL that opens the detailed view of all Gremien and form a request.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView """

        url = '/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView'
        yield self.build_request(response.urljoin(url), self.parse_gremien, '')
