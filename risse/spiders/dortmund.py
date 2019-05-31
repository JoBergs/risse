# -*- coding: utf-8 -*-

from risse.spiders.base import *

# "Integrationsrat" is not being parsed???

# first run: 113.9 MB; second run 140.9Mb and not finished?

class DortmundSpider(RisseSpider):
    name = "dortmund"

    def parse_iframe(self, response):
        links = response.xpath('//a[contains(@href, "pdf?OpenElement")]')

        # THIS SHOULD BE A FUNCTION!!! a lot of stuff can be fused with this in the base class!
        for i in range(len(links)):
            request = scrapy.Request(response.urljoin(links[i].attrib['href']),
                callback=self.save_pdf)
            request.meta['path'] = os.path.join(response.meta['path'], links[i].attrib['href'].split('/')[-1].rstrip('?OpenElement'))

            yield request

    def parse_drucksache(self, response):
        self.create_directories(os.path.join(*response.meta['path'], response.meta['id']))

        # not all Drucksachen have attachments
        try:
            iframe = response.xpath('//iframe').attrib["src"]

            request = scrapy.Request(iframe, callback=self.parse_iframe)
            request.meta['path'] = os.path.join(*response.meta['path'], response.meta['id'])

            yield request
        except:
            pass

    def parse_sitzung(self, response):
        name = response.meta['name']

        # move this into base class
        if name in self.mapping:
            name = self.mapping[name]
        date = response.meta['date'].split('.')

        # check for command line arguments year and or date
        if (self.year == None or date[-1] == self.year) and \
            (self.month == None or date[1].lstrip('0') == self.month):

            # /root-path-for-documents/2019/name-of-commitee/2019-03-28/Number-of-Topic/
            path = [self.root, date[-1], name, '-'.join(date[::-1])]

            self.create_directories(os.path.join(*path))

            self.save_file(os.path.join(*path, name + '.html'), response.text, True) 

            ids = response.xpath('//font/text()').re(r'\(Drucksache Nr.: (\S*)\)')

            base_url = 'https://dosys01.digistadtdo.de/dosys/gremrech.nsf/TOPWEB/'

            for drucksache in ids:
                request = scrapy.Request(base_url + drucksache,
                    callback=self.parse_drucksache)
                request.meta['path'] = path
                request.meta['id'] = drucksache

                yield request

    def parse_gremien(self, response):
        """ Function to parse all Gremien on all pages.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView """

        # e.g. <a href="/dosys/gremniedweb1.nsf/034bc6e876399f96c1256e1d0035a1e9/764a822ae6adae29c125840700252a09?OpenDocument"><b><script language="JavaScript">\nfunction NeuFenster764A822AE6ADAE29C125840700252A09()\n{\nMeinFenster =\n window.open("dosys\\gremniedweb1.nsf/NiederschriftenWeb/764A822AE6ADAE29C125840700252A09?OpenDocument", "Zweitfenster", "width=800,height=600,toolbar=no,userbar=no,location=no,status=no,menubar=no,scrollbars,offsetX=5,offsetY=5 ");\n MeinFenster.focus();\n}\n</script>\n<a href="javascript:NeuFenster764A822AE6ADAE29C125840700252A09()">Festgestellte Tagesordnung (öffentlich), 23.05.2019</a></b> <br></a>
        links = response.xpath('//a[contains(@href, "OpenDocument")]')
        # e.g. <a href="javascript:NeuFenster764A822AE6ADAE29C125840700252A09()">Festgestellte Tagesordnung (öffentlich), 23.05.2019</a>
        dates = links.xpath('//a[contains(@href, "javascript")]/text()').getall() 

        # name = None

        # if 'name' in response.meta.keys():
        #     name = response.meta['name']

        name = response.meta.get('name', None)

        for request in self.parse_gremium(response, name, links, dates):
            yield request

        yield self.parse_next_gremium(response, name)

    def parse_gremium(self, response, name, links, dates):
        """ Function to make a request for parsing every Sitzung of the current Gremium.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView """
        requests = []

        for i in range(len(links)):
            if "Tagesordnung" not in links[i].get():
                request = self.build_request(response.urljoin(links[i].attrib['href']), 
                    self.parse_sitzung, '')

                # e.g. <img src="/dosys/gremniedweb1.nsf/%24PlusMinus?OpenImageResource&amp;ImgIndex=1" border="0" alt="Details verbergen für Rat der Stadt">
                tmp = response.xpath('//img[contains(@alt, "Details verbergen für")]')
                if tmp != []:
                    name = tmp.attrib['alt'].lstrip("Details verbergen für")

                request.meta['name'] = name
                request.meta['date'] = dates[i].lstrip("Niederschrift (öffentlich), ")
                
                # TESTING
                print(name)
                if name == "Hauptausschuss und Ältestenrat":
                    requests.append(request)

        return requests

    def parse_next_gremium(self, response, name):
        """ Function to make a request for parsing the next Gremium on the next page.
        Site: https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView """

        # TESTING
        if name == "Ausschuss für Bauen, Verkehr und Grün":
            return
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
