# -*- coding: utf-8 -*-

from risse.spiders.base import *


class DortmundSpider(RisseSpider):
    name = "dortmund"

    def parse_iframe(self, response):
        links = response.xpath('//a[contains(@href, "pdf?OpenElement")]')

        # THIS SHOULD BE A FUNCTION (maybe)
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
        if name in self.mapping:
            name = self.mapping[name]
        date = response.meta['date'].split('.')

        # check for command line arguments year and or date
        if (self.year == None or date[-1] == self.year) and \
            (self.month == None or date[1].lstrip('0') == self.month):

            # /root-path-for-documents/2019/name-of-commitee/2019-03-28/Number-of-Topic/
            path = [self.root, date[-1], name, '-'.join(date[::-1])]

            self.create_directories(os.path.join(*path))

            # test if we overwrite
            full_path = os.path.join(*path, name + '.html')
            if self.overwrite == True or not os.path.isfile(full_path):
                with open(full_path, 'w') as f:
                    f.write(response.text)

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
                request = scrapy.Request(response.urljoin(links[i].attrib['href']),
                                         callback=self.parse_niederschrift)

                # parse name of current committee if available
                tmp = response.xpath('//img[contains(@alt, "Details verbergen für")]')
                if tmp != []:
                    name = tmp.attrib['alt'].lstrip("Details verbergen für")

                request.meta['name'] = name
                request.meta['date'] = dates[i].lstrip("Niederschrift (öffentlich), ")

                yield request

        next_page = response.xpath('//*[.=">>"]/parent::*/a') 
        if next_page is not None:
            next_page = response.urljoin(next_page.attrib['href'])
            request = scrapy.Request(next_page, callback=self.parse_gremien)
            request.meta['name'] = name

            yield request

    def parse(self, response):
        yield scrapy.Request(response.urljoin('/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView&ExpandView'), callback=self.parse_gremien)
