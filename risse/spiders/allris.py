# -*- coding: utf-8 -*-

from risse.spiders.base import *


class AllrisSpider(RisseSpider):
    name = "allris"
    all_years = range(1998, datetime.datetime.now().year + 1)
 
    def parse_vorlage(self, response): 
        """ Herein, all Anlagen of a Vorlage are extracted. 
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/vo020.asp?VOLFDNR=20431"""

        # e.g. <input type="hidden" name="DOLFDNR" value="563803">
        dolfdnrs = response.xpath('//input[contains(@name, "DOLFDNR")]')
        # e.g. <input type="submit" class="il2_p" value="Vorlage" title="Vorlage (Öffnet PDF-Datei in neuem Fenster)">
        titles = response.xpath('//input[contains(@class, "il2_p")]')

        for i in range(len(dolfdnrs)):
            request = self.build_request(response.urljoin("do027.asp?"), self.save_pdf, 
                os.path.join(response.meta['path'], titles[i].attrib['title'].split(" (Öffnet")[0] + '.pdf'),
                {'DOLFDNR': dolfdnrs[i].attrib['value'], 'options': "64"})

            yield request 

        for request in self.build_anlagen_requests(response):
            yield request

    def build_anlagen_requests(self, response):
        """Extract all Anlagen and create a request for each of them """

        # e.g. '<a href="___tmp/tmp/450810361031878127/1031878127/00565584/84-Anlagen/01/B18_0134-01.pdf" target="_blank" title="Dauer ca. 2 sec [DSL] / 29 sec [ISDN] / 33 sec [56K] (Öffnet Dokument in neuem Fenster)" onmouseover="status=\'B 18_0134-01 (235 KB)\'; return true;" onmouseout="status=\'\'; return true;">B 18_0134-01 (235 KB)</a>'
        anlagen = response.xpath('//a[contains(@href, ".pdf")]')
        # remove duplicates
        anlagen = list(set([anlage.attrib['href'] for anlage in anlagen]))

        requests = []

        for anlage in anlagen:
            request = self.build_request(response.urljoin(anlage), self.save_pdf,
                os.path.join(response.meta['path'], os.path.basename(anlage)))

            requests.append(request)

        return requests 

    def parse_beratungsverlauf(self, response):  
        """Try to parse the HTML Beratungsverlauf and store it in a file.
        If there are non-transferable special characters in that file, save a 
        warning instead. 
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/to020.asp?TOLFDNR=89848"""

        try:
            beratungsverlauf = response.xpath('//span[text()="Beratungsverlauf:"]/parent::node()/parent::node()').get()
        except:
            beratungsverlauf = "Enthält nicht transferierbare Sonderzeichen."

        if beratungsverlauf:  # Not every Topic has a Beratungsverlauf
            beratungsverlauf_path = os.path.join(response.meta['path'], "beratungsverlauf.html")
            self.save_file(beratungsverlauf_path, beratungsverlauf, True)    

    def parse_beschluss(self, response):
        """ For every topic, the related Beschluss with its Beratungsverlauf (HTML),
        Vorlage and Anlagen has to be parsed. 
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/to020.asp?TOLFDNR=89835"""

        # current_path = response.meta['path'].replace('/', '-').replace('\\', '-')
        self.create_directories(response.meta['path'])

        self.parse_beratungsverlauf(response)

        for request in self.build_anlagen_requests(response):
            yield request

        # e.g. <input type="hidden" name="VOLFDNR" value="20431">
        volfdnr = response.xpath('//input[contains(@name, "VOLFDNR")]').attrib['value']

        request = self.build_request(response.urljoin('vo020.asp'),
            self.parse_vorlage, response.meta['path'], {'VOLFDNR': volfdnr})

        yield request

    def build_niederschrift_requests(self, response, path):
        """ Returns a request for the oeffentliche Niederschrift PDF """

        try:
            # e.g. <input type="hidden" name="DOLFDNR" value="564806">
            dolfdnr = response.xpath('//input[contains(@name, "DOLFDNR")]').attrib['value']

            request = self.build_request(response.urljoin("do027.asp?"),
                self.save_pdf, os.path.join(*path, 'oeffentliche_Niederschrift.pdf'),
                {'DOLFDNR': dolfdnr, 'options': "64"})

            return request
        except:  # not every Sitzung has a oeffentliche Niederschrift
            return None

    def parse_sitzung(self, response):
        """A Sitzung contains a Niederschrift and various Topics that have to be
        scraped. The required requests are build herein. 
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/to010.asp?SILFDNR=11630"""

        # print(response.request.headers)

        # e.g. <td class="kb1">Gremien:</td><td class="text1" colspan="3">Ausländerbeirat, Migrationsrat</td>    
        name = response.xpath('//td[contains(text(), "Gremien") or contains(text(), "Gremium")]/following-sibling::td/text()').get()  

        if not name:
            name = response.xpath('//td[contains(text(), "Gremien") or contains(text(), "Gremium")]/following-sibling::td/a/text()').get()

        if name in self.mapping:
            name = self.mapping[name]

        # e.g. <a href="si010_j.asp?YY=2018&amp;MM=03&amp;DD=05" title="Sitzungskalender 03/2018 anzeigen">05.03.2018</a>
        date = response.xpath('//a[contains(@title, "Sitzungskalender")]/text()').get().split('.')
        path = [self.root, date[-1], name, '-'.join(date[::-1]), '__Dokumente']

        self.create_directories(os.path.join(*path))

        yield self.build_niederschrift_requests(response, path)

        for request in self.build_topic_requests(response, path):
            yield request

    # can probably be shortened with better selectors
    def get_topic_urls(self, response):
        """ Take a response for a Sitzung and extract all URLs to
        Vorlagen in the same order as the Topics. """
        
        trs = response.xpath('//tr[contains(@class, "zl11") or contains(@class, "zl12")]')
        urls = response.xpath('//a[contains(@href, "to020.asp")]/@href').getall() 

        # only use trs that contain a topic and a Vorlage
        # (see https://ratsinfo.muelheim-ruhr.de/buerger/to010.asp?SILFDNR=11631)
        trs = [tr for tr in trs if "to020.asp" in tr.get()]
        for i in reversed([*range(len(trs))] ):
            if "vo020.asp" not in trs[i].get():  # this tr has no link to a Vorlage
                urls.pop(i)

        return urls
    
    def build_topic_requests(self, response, path):
        """ Take a list of urls and topics and create a request for each extracted
        TOLFDNR for parsing the Beschluss over .asp """

        requests = []

        urls = self.get_topic_urls(response)
        # e.g. <a href="vo020.asp?VOLFDNR=20417">V 18/0111-01</a>
        topics = response.xpath('//a[contains(@href, "vo020.asp")]/text()').getall()

        for i in range(len(urls)):          
            # this fixes an error in the HTML layout: the TOP might be in a <span> or not
            try:
                # e.g. '<td class="text4" nowrap><a href="to010.asp?SILFDNR=12002&amp;TOLFDNR=90172#beschluss" title="Auswählen">Ö\xa02</a></td>'
                top = response.xpath('//a[contains(@href, "' + urls[i] + '")]/parent::*/parent::*/td[contains(@class, "text4")]/a/text()').get().strip('Ö\xa0') .lstrip('0')
            except: 
                top = response.xpath('//a[contains(@href, "' + urls[i] + '")]/parent::*/parent::*/td[contains(@class, "text4")]/span/a/text()').get().strip('Ö\xa0') .lstrip('0')     

            current_topic = topics[i].replace('/', '-').replace('\\', '-')

            request = self.build_request(response.urljoin(urls[i]),
                self.parse_beschluss, os.path.join(*path[:-1], top or "kein_TOP", current_topic),
                {'TOLFDNR': urls[i].strip('to020.asp?TOLFDNR=')})

            requests.append(request)

        return requests
                 
    def parse_year(self, response):
        ''' Herein, a specific year or the month of a specific year is parsed. 
        All IDs of Sitzungen are extracted and .asp form request for each ID are executed. 
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/si010_j.asp'''

        # e.g. <a href="to010.asp?SILFDNR=11630">Sitzung der Bezirksvertretung 3</a>
        ids = response.xpath('//a').re(r'"*to010.asp\?SILFDNR=(\S*)"')

        print(ids)

        for current in ids:
            request = self.build_request(response.urljoin('to010.asp'),
                self.parse_sitzung, '', {'SILFDNR': current})
            yield request

    def parse_calender(self, response):
        ''' Muelheim supports an .asp calender that retrieves Sitzungen.
        This function requests all Sitzungen that happened between
        from_day and to_day either for the year passed as CLI argument
        or for all years that have Sizungen. 
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/si010_j.asp'''

        if self.year:  # if year was passed as a parameter, scrape only that year
            self.all_years = [self.year]

        for year in self.all_years:
            from_day, to_day = self.get_dates(str(year), self.month)

            request = self.build_request(response.url,
                self.parse_year, '', {'kaldatvon': from_day, 'kaldatbis': to_day})
            yield request

    def parse(self, response):
        """ Find the URL that links to the calender from the Mülheim
        main page and form a request.
        Site: https://ratsinfo.muelheim-ruhr.de/buerger/allris.net.asp """

        url = response.xpath('//a[contains(@href, "si010_j.asp") or contains(@href, "si010.asp") or contains(@href, "si010_a.asp")]/@href').get()
        # import ipdb
        # ipdb.set_trace()
        # Hagen is accessed like this:
        #   https://www.hagen.de/ngproxy/a6b28fc3a138dc73acd88f99d00e74fdfb845dc2
        yield self.build_request(response.urljoin(url), self.parse_calender, '')  