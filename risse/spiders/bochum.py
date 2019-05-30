# -*- coding: utf-8 -*-

from risse.spiders.base import *

from lxml import html

# full run 293.3MB ~1h
#   for testing Bezirksvertretung Bochum-Mitte
#      37.2MB 37.2 MB

class BochumSpider(RisseSpider):
    name = "bochum"

    def extract_top(self, index, trs):
        """ Since since a TOp can span multiple rows, it's necessary
        to search for the right TOp for every Vorlage. This function iterates up
        in the list or rows (trs) until it finds a row with a TOP and returns it. 
        If no TOP is found, 'kein_TOP' is returned. """

        while index > 0:
            tree = html.fromstring(trs[index].get())
            top = tree.xpath('//tr/td[contains(@class, "smc_tophn")]/text()') 

            if top != []:
                return top[0]
            index -= 1

        return "kein_TOP"

    def extract_topic(self, index, trs):
        """ As for TOPs, a topic can span multiple rows with Vorlagen.
        This function up iterates over the list of rows (trs) until a valid topic
        can be extracted. If there is none, it returns 'kein_TOPIC' instead.  """

        while index > 0:
            tree = html.fromstring(trs[index].get())
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

            trs = response.xpath('//tr[contains(@class, "smc_toph")]')

            for j in range(len(trs)):
                if pdfs[i].split('&')[0] in trs[j].get():
                    break;

            top = self.extract_top(j, trs)
            topic = self.extract_topic(j, trs)

            full_path = response.meta['path'] + [top, topic]

            self.create_directories(os.path.join(*full_path))

            request = scrapy.Request(response.urljoin(pdfs[i]),
                callback=self.save_pdf)
            # DRAGONS: the filenames are not resolved like in the browser;
            # for Linux i had to replace /
            request.meta['path'] = os.path.join(*full_path, filenames[i].replace('/', '').replace(':', '') + '.pdf')

            yield request

    def get_gremium_data(self, response):
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

        return urls, dates, niederschriften, einladungen

    def parse_gremium(self, response):
        urls, dates, niederschriften, einladungen = get_gremium_data(response)

        for i in range(len(urls)):
            # it's bad to use path both as list and string
            date = dates[i].split('.')

            # only parse the current sitzung url of the date fits to the parameters
            if self.year and self.year != date[-1] or self.month and self.month != date[1].lstrip('0'):
                continue;

            path = [self.root, date[-1], response.meta['name'], '-'.join(date[::-1]), '__Dokumente']
            self.create_directories(os.path.join(*path))

            if einladungen[i]:
                request = self.build_request(response.urljoin(einladungen[i]), 
                    self.save_pdf, os.path.join(*path, "Einladung.pdf"))

                yield request

            if niederschriften[i]:
                request = self.build_request(response.urljoin(niederschriften[i]), 
                    self.save_pdf, os.path.join(*path, "Niederschrift_oeffentlich.pdf"))

                yield request    

            request = self.build_request(response.urljoin(urls[i]), 
                self.parse_ausschuss, path[:-1])

            yield request      

    def parse_gremien(self, response):
        """ Find URLs for all Gremien and form a request for each of them.
        Site: https://session.bochum.de/bi/gr0040.asp """

        # e.g. '<a href="si0041.asp?__ctopic=gr&amp;__kgrnr=977997" title="zu Ausschuss für Arbeit, Gesundheit und Soziales: Sitzungen\r\nDiese Seite liefert eine Übersicht der Sitzungen eines Gremiums. Als Filterkriterien sind Zeiträume verfügbar. " class="smccontextmenulink smcmenucontext_fct_sitzungen">Sitzungen</a>'
        urls = response.xpath('//a[contains(@class, "smccontextmenulink smcmenucontext_fct_sitzungen")]/@href').getall()
        names = response.xpath('//a[contains(@class, "smccontextmenulink smcmenucontext_fct_sitzungen")]/@title').getall()
        names = [name.strip('zu ').split(':')[0] for name in names]
        names = [self.mapping[name] if name in self.mapping else name for name in names]

        for i in range(len(urls)):
            # TESTING!
            if names[i] == "Bezirksvertretung Bochum-Mitte":
                request = self.build_request(response.urljoin(urls[i]), self.parse_gremium, '')
                request.meta['name'] = names[i]

                yield request   

    def parse(self, response):
        """Find the URL to 'Gremien' on the main page and form a request with it.
        Site: https://session.bochum.de/bi/infobi.asp """

        #e.g. '<a href="gr0040.asp" title="Diese Seite zeigt eine Liste der Gremien, für die im Sitzungsdienst Informationen verwaltet werden. Als Filter stehen die Zeiträume zur Verfügung. " class="smcuser_nav_gremien">Gremien</a>'
        url = response.xpath('//a[contains(@class, "smcuser_nav_gremien")]/@href').get()
        yield self.build_request(response.urljoin(url), self.parse_gremien, '')  