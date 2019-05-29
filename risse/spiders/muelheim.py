# -*- coding: utf-8 -*-

# scrapy crawl muelheim -a stadt=Mülheim -a url=https://ratsinfo.muelheim-ruhr.de/buerger/allris.net.asp -a root=test -a year=2018 -a month=3 -a overwrite=True

import  datetime, os, logging

import scrapy

from risse.spiders.base import RisseSpider

current_year = datetime.datetime.now().year

all_years = range(1998, current_year + 1)


# ADD OVERWRITE TESTS to write HTML and move write HTML into base class -> is a generic write_file possible?

# move path creation into base class?

# it would be nice to have a general method for building requests in the base class
#   and overwrite it for muelheim
class MuelheimSpider(RisseSpider):
    name = "muelheim"
    # download_delay = 1.5  # prolly not necessary

    def parse_vorlage(self, response):    
        dolfdnrs = response.xpath('//input[contains(@name, "DOLFDNR")]')
        titles = response.xpath('//input[contains(@class, "il2_p")]')

        for i in range(len(dolfdnrs)):
            request = scrapy.FormRequest(response.urljoin("do027.asp?"),
                formdata={'DOLFDNR': dolfdnrs[i].attrib['value'], 'options': "64"},
                callback=self.save_pdf)

            request.meta['path'] = os.path.join(response.meta['path'], titles[i].attrib['title'].split(" (Öffnet")[0])
            logging.info('Saving PDF %s', request.meta['path'])

            yield request      

        # ACHTUNG: Anlagen können nicht verfügbar sein
        anlagen = response.xpath('//a[contains(@href, ".pdf")]')
        anlagen = anlagen[:len(anlagen)//2]

        for anlage in anlagen:
            request = scrapy.Request(response.urljoin(anlage.attrib['href']),
                callback=self.save_pdf)
            filename = os.path.basename(anlage.attrib['href'])
            request.meta['path'] = os.path.join(response.meta['path'], filename)
            logging.info('Saving PDF %s', request.meta['path'])

            yield request 

    def parse_beschluss(self, response):
        # print("beschluss path ", response.meta['path'])
        # if "2019" in response.meta['path']:
        #     import ipdb
        #     ipdb.set_trace()
        self.create_directories(response.meta['path'])

        try:
            beschluss = response.xpath('//span[text()="Beratungsverlauf:"]/parent::node()/parent::node()').get()
        except:
            beschluss = "Enthält nicht transferierbare Sonderzeichen."

        # FUSE THIS WITH HTML WRITING IN dortmund.py; add automated overwrite test here and for pdf
        beschluss_path = os.path.join(response.meta['path'], "beratungsverlauf.html")
        logging.info('Saving HTML %s', beschluss_path)
        with open(beschluss_path, 'w') as f:
            f.write(beschluss)  # if there is no beschluss (BAD)

        # mostly öffentliche Niederschrift
        anlagen = response.xpath('//a[contains(@href, ".pdf")]')

        for anlage in anlagen:

            request = scrapy.Request(response.urljoin(anlage.attrib['href']),
                callback=self.save_pdf)

            request.meta['path'] = os.path.join(response.meta['path'], anlage.attrib['href'].split('/')[-1])
            logging.info('Saving PDF %s', request.meta['path'])

            yield request

        volfdnr = response.xpath('//input[contains(@name, "VOLFDNR")]').attrib['value']

        request = scrapy.FormRequest(response.urljoin('vo020.asp'),
            formdata={'VOLFDNR': volfdnr},
            callback=self.parse_vorlage)

        request.meta['path'] = response.meta['path']

        yield request

    def parse_sitzung(self, response):
        name = response.xpath('//a[contains(@href, "Gremium")]/text()').extract()[-1]
        # print(name)
        # if name == "Planungsausschuss":
        #     import ipdb
        #     ipdb.set_trace()

        # not every sitzung has a öffentliche Niederschrift?
        dolfdnr = None
        try:
            dolfdnr = response.xpath('//input[contains(@name, "DOLFDNR")]').attrib['value']
        except:
            pass
        date = response.xpath('//a[contains(@title, "Sitzungskalender")]/text()').get().split('.')

        if name in self.mapping:
            name = self.mapping[name]

        # move joining in base class, pass root (not really necessary), name and date
        path = [self.root, date[-1], name, '-'.join(date[::-1]), '__Dokumente']
        self.create_directories(os.path.join(*path))
        # print("created ", os.path.join(*path))
        # if "2019" in os.path.join(*path):
        #     import ipdb
        #     ipdb.set_trace()

        # not all Sitzungen have an oeffentliche Niederschrift
        if dolfdnr:
            request = scrapy.FormRequest(response.urljoin("do027.asp?"),
                formdata={'DOLFDNR': dolfdnr, 'options': "64"},
                callback=self.save_pdf)

            request.meta['path'] = os.path.join(*path, 'oeffentliche_Niederschrift.pdf')
            logging.info('Saving PDF %s', request.meta['path'])

            yield request

        trs = response.xpath('//tr[contains(@class, "zl11") or contains(@class, "zl12")]')
        urls = response.xpath('//a[contains(@href, "to020.asp")]/@href').getall() 

        # remove urls that have no topic link
        trs = [tr for tr in trs if "to020.asp" in tr.get()]
        for i in reversed([*range(len(trs))] ):
            if "vo020.asp" not in trs[i].get():
                urls.pop(i)

        topics = response.xpath('//a[contains(@href, "vo020.asp")]/text()').getall()

        for i in range(len(urls)):            
            request = scrapy.FormRequest(response.urljoin(urls[i]),
                formdata={'TOLFDNR': urls[i].strip('to020.asp?TOLFDNR=')},
                callback=self.parse_beschluss)

            try:
                top = response.xpath('//a[contains(@href, "' + urls[i] + '")]/parent::*/parent::*/td[contains(@class, "text4")]/a/text()').get().strip('Ö\xa0') .lstrip('0')
            
            except: 
                top = response.xpath('//a[contains(@href, "' + urls[i] + '")]/parent::*/parent::*/td[contains(@class, "text4")]/span/a/text()').get().strip('Ö\xa0') .lstrip('0')

            request.meta['path'] = os.path.join(*path[:-1], top or "kein_TOP", topics[i])

            yield request
                 
    def parse_year(self, response):
        ids = response.xpath('//a').re(r'"to010.asp\?SILFDNR=(\S*)"')
        # print(len(ids))

        for current in ids:
            request = scrapy.FormRequest(response.urljoin("to010.asp?"),
                formdata={'SILFDNR': current},  # for debugging
                callback=self.parse_sitzung)

            request.meta['SILFDNR'] = current

            yield request

    def get_dates(self, year, month):
        last_day = "31."

        if int(month) % 2 == 0:
            last_day = "30."

        if int(month) == 2:
            last_day = "28."

        if month:
            tmp = month
            if len(tmp) == 1:
                tmp = '0' + tmp
            return "01." + month + "." + year, last_day + month + "." + year
        return "01.01." + year, last_day + year

    def parse_calender(self, response):

        if self.year:
            all_years = [self.year]

        # move all_years into self
        for year in all_years:
            from_day, to_day = self.get_dates(str(year), self.month)
            yield scrapy.FormRequest(
                response.url,
                formdata={
                    'kaldatvon': from_day,
                    'kaldatbis': to_day,                   
                },
                callback=self.parse_year
            )

    def parse(self, response):
        url = response.xpath('//a[contains(@href, "si010_j.asp")]/@href').get()
        request = scrapy.Request(response.urljoin(url), callback=self.parse_calender)

        yield request  