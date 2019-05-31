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

    def parse_niederschrift(self, response):
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
        links = response.xpath('//a[contains(@href, "OpenDocument")]')
        dates = links.xpath('//a[contains(@href, "javascript")]/text()').getall() 

        name = None

        if 'name' in response.meta.keys():
            name = response.meta['name']

        for i in range(len(links)):
            if "Tagesordnung" not in links[i].get():
                # request = scrapy.Request(response.urljoin(links[i].attrib['href']),
                #                          callback=self.parse_niederschrift)
                request = self.build_request(response.urljoin(links[i].attrib['href']), 
                    self.parse_niederschrift, '')

                # parse name of current committee if available
                tmp = response.xpath('//img[contains(@alt, "Details verbergen für")]')
                if tmp != []:
                    name = tmp.attrib['alt'].lstrip("Details verbergen für")

                request.meta['name'] = name
                request.meta['date'] = dates[i].lstrip("Niederschrift (öffentlich), ")
                
                # TESTING
                print(name)
                if name == "Hauptausschuss und Ältestenrat":
                    yield request

        yield self.next_gremium(response, name)

    def next_gremium(self, response, name):
        """ Function to parse the next Gremium on the next page.
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
