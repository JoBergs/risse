# -*- coding: utf-8 -*-

# scrapy crawl bochum -a stadt=Bochum -a url=https://session.bochum.de/bi/infobi.asp -a root=test -a year=2018 -a month=3 -a overwrite=True

import os, logging

import scrapy

from risse.spiders.base import RisseSpider

from lxml import html

class BochumSpider(RisseSpider):
    name = "bochum"
    # download_delay = 1.5  # prolly not necessary

    def extract_top(self, index, trs):
        while index > 0:
            row = trs[index].get()
            tree = html.fromstring(row)
            top = tree.xpath('//tr/td[contains(@class, "smc_tophn")]/text()') 

            if top != []:
                return top[0]
            index -= 1

        return "kein_TOP"

    def extract_topic(self, index, trs):
        while index > 0:
            row = trs[index].get()
            tree = html.fromstring(row)
            top = tree.xpath('//tr/td/a[contains(@class, "smc_doc smc_field_voname smc_datatype_vo")]/text()') 

            if top != []:
                return top[0]
            index -= 1

        return "kein_TOPIC"

    def parse_ausschuss(self, response):
        pdfs = response.xpath('//td[contains(@class, "smc_doc smcdocname smcdocname1")]/a[contains(@href, "getfile.asp")]/@href').getall()
        filenames = response.xpath('//a[contains(@href, "getfile.asp")]/text()').getall()

        for i in range(len(pdfs)):
            topic_xpath = '//a[contains(@href, "' + pdfs[i] + '")]/ancestor::*/*/a[contains(@class, "smc_doc smc_field_voname smc_datatype_vo")]/text()'
            topic = response.xpath(topic_xpath).get()

            # top_xpath = '//a[contains(@href, "' + pdfs[i] + '")]/parent::td/parent::tr/parent::*/parent::*/parent::*/parent::*/td[contains(@class, "smc_tophn")]/text()'
            # top = response.xpath(top_xpath).get()

            trs = response.xpath('//tr[contains(@class, "smc_toph")]')

            for j in range(len(trs)):
                if pdfs[i].split('&')[0] in trs[j].get():
                    break;

            top = self.extract_top(j, trs)
            topic = self.extract_topic(j, trs)

            full_path = response.meta['path'] + [top, topic]

            # if topic == None or top == None:
            #     import ipdb
            #     ipdb.set_trace()

            self.create_directories(os.path.join(*full_path))

            request = scrapy.Request(response.urljoin(pdfs[i]),
                callback=self.save_pdf)
            # DRAGONS: the filenames are not resolved like in the browser;
            # for Linux i had to replace /
            request.meta['path'] = os.path.join(*full_path, filenames[i].replace('/', '').replace(':', '') + '.pdf')
            logging.info('Saving PDF %s', request.meta['path'])

            yield request

    def parse_gremium(self, response):
        urls = response.xpath('//tr[contains(@class, "smcrow1") or contains(@class, "smcrow2") or contains(@class, "smcrown")]/*/a/@href').getall()
        dates = response.xpath('//tr[contains(@class, "smcrow1") or contains(@class, "smcrow2") or contains(@class, "smcrown")]/*/a/text()').getall()

        einladungen = response.xpath('//a[contains(text(), "Einladung")]/@href').getall()
        niederschriften = response.xpath('//a[contains(text(), "Niederschrift")]/@href').getall()

        tables = response.xpath('//table[contains(@class, "smcdocbox smcdocboxright")]').getall()

        # not all einladungen have niederschriften vv. insert None accordingly
        for i in range(len(tables)):
            if "Niederschrift" not in tables[i]:
                niederschriften.insert(i, None)
            if "Einladung" not in tables[i]:
                einladungen.insert(i, None)

        for i in range(len(urls)):
            # it's bad to use path both as list and string
            date = dates[i].split('.')

            # only parse the current sitzung url of the date fits to the parameters
            if self.year and self.year != date[-1] or self.month and self.month != date[1].lstrip('0'):
                continue;

            path = [self.root, date[-1], response.meta['name'], '-'.join(date[::-1]), '__Dokumente']
            self.create_directories(os.path.join(*path))

            if einladungen[i]:
                request = scrapy.Request(response.urljoin(einladungen[i]),
                    callback=self.save_pdf)
                request.meta['path'] = os.path.join(*path, "Einladung.pdf")
                logging.info('Saving PDF %s', request.meta['path'])

                yield request

            if niederschriften[i]:
                request = scrapy.Request(response.urljoin(niederschriften[i]),
                    callback=self.save_pdf)
                request.meta['path'] = os.path.join(*path, "Niederschrift_oeffentlich.pdf")
                logging.info('Saving PDF %s', request.meta['path'])

                yield request    

            request = scrapy.Request(response.urljoin(urls[i]),
                callback=self.parse_ausschuss)
            request.meta['path'] = path[:-1]

            yield request      

    def parse_gremien(self, response):
        urls = response.xpath('//a[contains(@class, "smccontextmenulink smcmenucontext_fct_sitzungen")]/@href').getall()
        names = response.xpath('//a[contains(@class, "smccontextmenulink smcmenucontext_fct_sitzungen")]/@title').getall()
        names = [name.strip('zu ').split(':')[0] for name in names]
        names = [self.mapping[name] if name in self.mapping else name for name in names]

        for i in range(len(urls)):
            # TESTING!
            # if names[i] == "Rat":
            request = scrapy.Request(response.urljoin(urls[i]),
                callback=self.parse_gremium)
            request.meta['name'] = names[i]

            yield request   

    def parse(self, response):
        url = response.xpath('//a[contains(@class, "smcuser_nav_gremien")]/@href').get()
        request = scrapy.Request(response.urljoin(url), callback=self.parse_gremien)

        yield request  