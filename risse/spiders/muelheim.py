# -*- coding: utf-8 -*-

from risse.spiders.base import *

# move path creation into base class?

# it would be nice to have a general method for building requests in the base class
#   and overwrite it for muelheim -> yer, two functions build_request and build_form_request 
#   would be nice
class MuelheimSpider(RisseSpider):
    name = "muelheim"
    all_years = range(1998, datetime.datetime.now().year + 1)
 
    def parse_vorlage(self, response): 
        """ A Vorlage can have seperate Anlagen as well.
        Herein, the Vorlage and all Anlagen are extracted. """

        # e.g. <input type="hidden" name="DOLFDNR" value="563803">
        # CAN BE FUSED WITH OTHER NUMBER EXTRACTORS
        dolfdnrs = response.xpath('//input[contains(@name, "DOLFDNR")]')
        # e.g. <input type="submit" class="il2_p" value="Vorlage" title="Vorlage (Öffnet PDF-Datei in neuem Fenster)">
        titles = response.xpath('//input[contains(@class, "il2_p")]')

        for i in range(len(dolfdnrs)):
            request = scrapy.FormRequest(response.urljoin("do027.asp?"),
                formdata={'DOLFDNR': dolfdnrs[i].attrib['value'], 'options': "64"},
                callback=self.save_pdf)

            request.meta['path'] = os.path.join(response.meta['path'], 
                titles[i].attrib['title'].split(" (Öffnet")[0] + '.pdf')

            yield request 

        for request in self.build_anlagen_requests(response):
            yield request

    def build_anlagen_requests(self, response):
        """Extract all Anlagen and create a request for each of them """

        requests = []

        # e.g. '<a href="___tmp/tmp/450810361031878127/1031878127/00565584/84-Anlagen/01/B18_0134-01.pdf" target="_blank" title="Dauer ca. 2 sec [DSL] / 29 sec [ISDN] / 33 sec [56K] (Öffnet Dokument in neuem Fenster)" onmouseover="status=\'B 18_0134-01 (235 KB)\'; return true;" onmouseout="status=\'\'; return true;">B 18_0134-01 (235 KB)</a>'
        anlagen = response.xpath('//a[contains(@href, ".pdf")]')
        # remove duplicates
        anlagen = list(set([anlage.attrib['href'] for anlage in anlagen]))

        for anlage in anlagen:
            request = scrapy.Request(response.urljoin(anlage), callback=self.save_pdf)
            request.meta['path'] = os.path.join(response.meta['path'], 
                os.path.basename(anlage))
            requests.append(request)

        return requests 

    def parse_beratungsverlauf(self, response):  
        """Try to parse the HTML Beratungsverlauf and store it in a file.
        If there are non-transferable special characters in that file, save a 
        warning instead. """

        try:
            beratungsverlauf = response.xpath('//span[text()="Beratungsverlauf:"]/parent::node()/parent::node()').get()
        except:
            beratungsverlauf = "Enthält nicht transferierbare Sonderzeichen."

        if beratungsverlauf:  # Not every Topic has a Beratungsverlauf
            beratungsverlauf_path = os.path.join(response.meta['path'], "beratungsverlauf.html")
            self.save_file(beratungsverlauf_path, beratungsverlauf, True)    

    def parse_beschluss(self, response):
        """ For every topic, the related Beschluss with its Beratungsverlauf (HTML),
        Vorlage and Anlagen has to be parsed. """

        self.create_directories(response.meta['path'])

        self.parse_beratungsverlauf(response)

        for request in self.build_anlagen_requests(response):
            yield request

        # e.g. <input type="hidden" name="VOLFDNR" value="20431">
        volfdnr = response.xpath('//input[contains(@name, "VOLFDNR")]').attrib['value']

        # request = build
        request = scrapy.FormRequest(response.urljoin('vo020.asp'),
            formdata={'VOLFDNR': volfdnr},
            callback=self.parse_vorlage)

        request.meta['path'] = response.meta['path']

        yield request

    def build_niederschrift_requests(self, response, path):
        """ Returns a request for the oeffentliche Niederschrift PDF """

        try:
            # e.g. <input type="hidden" name="DOLFDNR" value="564806">
            dolfdnr = response.xpath('//input[contains(@name, "DOLFDNR")]').attrib['value']
            request = scrapy.FormRequest(response.urljoin("do027.asp?"),
                formdata={'DOLFDNR': dolfdnr, 'options': "64"},
                callback=self.save_pdf)

            request.meta['path'] = os.path.join(*path, 'oeffentliche_Niederschrift.pdf')

            return request
        except:  # not every Sitzung has a oeffentliche Niederschrift
            return None

    def parse_sitzung(self, response):
        """A Sitzung contains a Niederschrift and various Topics that have to be
        scraped. The required requests are build herein. """

        # e.g. <a href="au020.asp?T1=Gremium&amp;history=switch&amp;tsDD=10&amp;tsMM=4&amp;tsYYYY=2018&amp;AULFDNR=25&amp;altoption=Gremium">Bezirksvertretung 3</a>
        name = response.xpath('//a[contains(@href, "au020.asp")]/text()').get()
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
            request = scrapy.FormRequest(response.urljoin(urls[i]),
                formdata={'TOLFDNR': urls[i].strip('to020.asp?TOLFDNR=')},
                callback=self.parse_beschluss)

            # this fixes an error in the HTML layout: the TOP might be in a <span> or not
            try:
                # e.g. '<td class="text4" nowrap><a href="to010.asp?SILFDNR=12002&amp;TOLFDNR=90172#beschluss" title="Auswählen">Ö\xa02</a></td>'
                top = response.xpath('//a[contains(@href, "' + urls[i] + '")]/parent::*/parent::*/td[contains(@class, "text4")]/a/text()').get().strip('Ö\xa0') .lstrip('0')
            except: 
                top = response.xpath('//a[contains(@href, "' + urls[i] + '")]/parent::*/parent::*/td[contains(@class, "text4")]/span/a/text()').get().strip('Ö\xa0') .lstrip('0')

            request.meta['path'] = os.path.join(*path[:-1], top or "kein_TOP", topics[i])
            requests.append(request)

        return requests
                 
    def parse_year(self, response):
        ''' Herein, a specific year or the month of a specific year is parsed. 
        All IDs of Sitzungen are extracted and .asp form request for each ID are executed. '''

        # e.g. <a href="to010.asp?SILFDNR=11630">Sitzung der Bezirksvertretung 3</a>
        ids = response.xpath('//a').re(r'"to010.asp\?SILFDNR=(\S*)"')

        for current in ids:
            request = scrapy.FormRequest(response.urljoin("to010.asp?"),
                formdata={'SILFDNR': current},
                callback=self.parse_sitzung)

            yield request

    def parse_calender(self, response):
        ''' Muelheim supports an .asp calender that retrieves Sitzungen.
        This function requests all Sitzungen that happened between
        from_day and to_day either for the year passed as CLI argument
        or for all years that have Sizungen. '''

        if self.year:  # if year was passed as a parameter, scrape only that year
            self.all_years = [self.year]

        for year in self.all_years:
            from_day, to_day = self.get_dates(str(year), self.month)
            yield scrapy.FormRequest(
                response.url,
                formdata={'kaldatvon': from_day, 'kaldatbis': to_day},
                callback=self.parse_year)

    def parse(self, response):
        """ Find the URL that links to the calender from the Mülheim
        main page and form a request. """

        url = response.xpath('//a[contains(@href, "si010_j.asp")]/@href').get()
        request = scrapy.Request(response.urljoin(url), callback=self.parse_calender)

        yield request  