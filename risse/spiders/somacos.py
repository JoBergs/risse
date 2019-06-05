# -*- coding: utf-8 -*-

from risse.spiders.base import *

from lxml import html


class SomacosSpider(RisseSpider):
    name = "somacos"

    def find_top_and_topic(self, index, trs):
        """ Since since a TOP can span multiple rows, it's necessary to search
         for the right TOP and topic for every Vorlage. This function iterates up
        in the list or rows (trs) until it finds a row with a TOP and a topic and 
        returns them. If no TOP or topic is found, 'kein_TOP' resp. "kein_TOPIC"
        is returned. """

        top_result = "kein_TOP" 
        topic_result = "kein_TOPIC" 

        while index > 0:
            tree = html.fromstring(trs[index].get())
            top = tree.xpath('//tr/td[contains(@class, "smc_tophn")]/text()') 
            topic = tree.xpath('//tr/td/a[contains(@class, "smc_doc smc_field_voname smc_datatype_vo")]/text()') 

            if top != [] and top_result == "kein_TOP":
                top_result = top[0]
            if topic != [] and topic_result == "kein_TOPIC":
                topic_result = topic[0]

            index -= 1

        return top_result, topic_result        

    def parse_sitzung(self, response):
        ''' Function to parse all PDFs of a single Sitzung.
        Site: https://session.bochum.de/bi/to0040.asp?__ksinr=10218 '''

        # e.g. '<a href="getfile.asp?id=398523&amp;type=do&amp;" title="Beschlussvorlage der Verwaltung " target="_blank">Beschlussvorlage der Verwaltung <span class="smcwrapsmall smcdosize" title="Dateigröße">347\xa0KB </span></a>'
        pdfs = response.xpath('//td[contains(@class, "smc_doc smcdocname smcdocname1")]/a[contains(@href, "getfile.asp")]/@href').getall()
        filenames = response.xpath('//a[contains(@href, "getfile.asp")]/text()').getall()

        for i in range(len(pdfs)):
            # e.g. <a href="vo0050.asp?__kvonr=7068726&amp;voselect=10218" title="Vorlage anzeigen: Veranstaltungen der Bezirksvertretung Bochum-Mitte " class="smc_doc smc_field_voname smc_datatype_vo">20180032</a>
            topic_xpath = '//a[contains(@href, "' + pdfs[i] + '")]/ancestor::*/*/a[contains(@class, "smc_doc smc_field_voname smc_datatype_vo")]/text()'
            tmp = response.xpath('//a[contains(@href, "' + pdfs[i] + '")]/ancestor::*/*/a[contains(@class, "smc_doc smc_field_voname smc_datatype_vo")]').get()
            topic = response.xpath(topic_xpath).get()

            trs = response.xpath('//tr[contains(@class, "smc_toph")]')

            # find index of the current pdf in table rows to extract topic and top later
            for j in range(len(trs)):
                if pdfs[i].split('&')[0] in trs[j].get():
                    break; 

            top, topic = self.find_top_and_topic(j, trs)
            full_path = response.meta['path'] + [top, topic]
            self.create_directories(os.path.join(*full_path))

            # DRAGONS: filenames are resolved badly in browser; for Linux i had to replace / and :
            request = self.build_request(response.urljoin(pdfs[i]), self.save_pdf, 
                os.path.join(*full_path, filenames[i].replace('/', '').replace(':', '') + '.pdf'))

            yield request 

    def parse_gremium(self, response):
        """ Function to scrape all Sitzungen of a Gremium. Validates that the Sitzung
        fits the CLI parameters and scrapes Einladung, Niederschrift and Auschuss.
        Site:https://session.bochum.de/bi/si0041.asp?__ctopic=gr&__kgrnr=103973 """

        urls, dates, niederschriften, einladungen = self.get_gremium_data(response)

        for i in range(len(urls)):
            date = dates[i].split('.')

            # only parse the current sitzung url of the date fits to the parameters
            if self.year and self.year != date[-1] or self.month and self.month != date[1].lstrip('0'):
                continue;

            path = [self.root, date[-1], response.meta['name'], '-'.join(date[::-1]), '__Dokumente']
            self.create_directories(os.path.join(*path))

            for request in self.build_gremium_requests(response,
                                path, urls[i], einladungen[i], niederschriften[i]):
                yield request

    def get_gremium_data(self, response):
        """ Function to extract all data which is required to scrape a Gremium.
        urls contains the Ausschuss urls, dates is necessary to see if the current Sitzung
        fits the CLI parameters, einladungen is a list of URLs to Einladung PDFs
        and niederschriften a list of URLs to Niederschrift PDFs. """

        # e.g. <td class="smc_td smc_field_silink"><a href="to0040.asp?__ksinr=11487" title="Details anzeigen: Bezirksvertretung Bochum-Mitte 16.05.2019 " class="smc_doc smc_datatype_si">16.05.2019</a><!--SMCINFO:si.bi.1.4.1.1.16.1.3 --> 15:00-18:09</td>
        urls = response.xpath('//tr[contains(@class, "smcrow1") or contains(@class, "smcrow2") or contains(@class, "smcrown")]/*/a/@href').getall()
        dates = response.xpath('//tr[contains(@class, "smcrow1") or contains(@class, "smcrow2") or contains(@class, "smcrown")]/*/a/text()').getall()

        # e.g. <a href="getfile.asp?id=426409&amp;type=do&amp;" title="Einladung " target="_blank">Einladung <span class="smcwrapsmall smcdosize" title="Dateigröße">266\xa0KB </span></a>
        einladungen = response.xpath('//a[contains(text(), "Einladung")]/@href').getall()
        # e.g. <a href="getfile.asp?id=427859&amp;type=do&amp;" title="Niederschrift öffentlich " target="_blank">Niederschrift öffentlich <span class="smcwrapsmall smcdosize" title="Dateigröße">570\xa0KB </span></a>
        niederschriften = response.xpath('//a[contains(text(), "Niederschrift")]/@href').getall()

        # table layout in one table row; has either no, just one, or both Einladung and Niederschrift
        tables = response.xpath('//table[contains(@class, "smcdocbox smcdocboxright")]').getall()

        # not all einladungen have niederschriften vv. insert None accordingly
        for i in range(len(tables)):
            if "Niederschrift" not in tables[i]:
                niederschriften.insert(i, None)
            if "Einladung" not in tables[i]:
                einladungen.insert(i, None)

        return urls, dates, niederschriften, einladungen

    def build_gremium_requests(self, response, path, url, einladung, niederschrift):
        """ For each Gremium, three requests need to be build: one request
        for the Einladung, one request for the Niederschrift and one request
        for parsing the Sitzung. """

        if einladung:
            request1 = self.build_request(response.urljoin(einladung), 
                self.save_pdf, os.path.join(*path, "Einladung.pdf"))

        if niederschrift:
            request2 = self.build_request(response.urljoin(niederschrift), 
                self.save_pdf, os.path.join(*path, "Niederschrift_oeffentlich.pdf"))  

        request3 = self.build_request(response.urljoin(url), 
            self.parse_sitzung, path[:-1])

        return [request1, request2, request3]   

    def parse_gremien(self, response):
        """ Find URLs for all Gremien and form a request for each of them.
        Site: https://session.bochum.de/bi/gr0040.asp """

        # e.g. '<a href="si0041.asp?__ctopic=gr&amp;__kgrnr=977997" title="zu Ausschuss für Arbeit, Gesundheit und Soziales: Sitzungen\r\nDiese Seite liefert eine Übersicht der Sitzungen eines Gremiums. Als Filterkriterien sind Zeiträume verfügbar. " class="smccontextmenulink smcmenucontext_fct_sitzungen">Sitzungen</a>'
        urls = response.xpath('//a[contains(@class, "smccontextmenulink smcmenucontext_fct_sitzungen")]/@href').getall()
        names = response.xpath('//a[contains(@class, "smccontextmenulink smcmenucontext_fct_sitzungen")]/@title').getall()
        names = [name.strip('zu ').split(':')[0] for name in names]
        names = [self.mapping[name] if name in self.mapping else name for name in names]

        for i in range(len(urls)):
                request = self.build_request(response.urljoin(urls[i]), self.parse_gremium, '')
                request.meta['name'] = names[i]

                yield request   

    def parse(self, response):
        """Find the URL to 'Gremien' on the main page and form a request with it.
        Site: https://session.bochum.de/bi/infobi.asp """

        #e.g. '<a href="gr0040.asp" title="Diese Seite zeigt eine Liste der Gremien, für die im Sitzungsdienst Informationen verwaltet werden. Als Filter stehen die Zeiträume zur Verfügung. " class="smcuser_nav_gremien">Gremien</a>'
        url = response.xpath('//a[contains(@class, "smcuser_nav_gremien")]/@href').get()
        yield self.build_request(response.urljoin(url), self.parse_gremien, '')  