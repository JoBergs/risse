# -*- coding: utf-8 -*-

import calendar, datetime, logging, os

import scrapy

from scrapy.utils.log import configure_logging


class RisseSpider(scrapy.Spider):   
    ''' Abstract base class for scraping Ratsinformationssysteme. '''

    def __init__(self, root="documents", stadt=None, url=None, year=None,
                     month=None, overwrite="False", *a, **kw):
        ''' Initialization:
        root:: directory path were the results are stored,
        stadt:: city that is to be crawled,
        url:: url of the target Ratsinformationssystem,
        year, month:: year and month to be scraped,
        overwrite:: flag determines if existing results are overwritten'''

        super(RisseSpider, self).__init__(*a, **kw)

        self.root, self.year, self.month, self.stadt = root, year, month, stadt
        self.overwrite, self.start_urls = bool(overwrite), [url]

        configure_logging({"LOG_FILE": self.stadt + '.log'})

        # read in Gremium mappings to abbreviations
        map_path = os.path.join('risse', 'spiders', self.stadt + '.txt')
        self.mapping = self.parse_mapping(map_path)

    def save_file(self, path, content, is_html):
        '''path:: target path where content should be saved,
        content:: either binary PDF or HTML text,
        is_html is True if a HTML should be saved and False for PDF'''

        descriptor = 'w' if is_html else 'wb'
        message = 'HTML' if is_html else 'PDF'
        
        # if overwrite or the path doesn't exist and there is content, write the file
        if content is not None and (self.overwrite or not os.path.isfile(path)): 
            with open(path, descriptor) as f:
                f.write(content)
                logging.info('Saving %s %s', message, path)

    def save_pdf(self, response):
        self.save_file(response.meta['path'], response.body, False)

    def create_directories(self, path):
        if not os.path.isdir(path):
            os.makedirs(path) 

    def parse_mapping(self, path):
        '''path is the path to the mapping of Gremium name to an abbreviation
        for the given city
        returns a dictionary {GREMIUM : ABBREVIATION} '''

        mapping = {}

        with open(path, 'r') as f:
            for line in f.readlines():
                key, short = line.split('=')
                mapping[key] = short

        return mapping

    # TEST THIS
    def last_day_of_month(self, year, month):
        ''' Return the last day of the month, which is either "31.", "30.", "28." in february
        of "29." in a leap year february '''
        last_day = "31."

        if int(month) % 2 == 0:
            last_day = "30."

        if int(month) == 2:
            last_day = "28."
            if calendar.isleap(int(year)):
                last_day = "29."

        return last_day

    # BROKEN! DOES NOT WORK FOR MONTH = None
    # TEST THIS
    def get_dates(self, year, month):
        ''' Find the date range for the given year and month for parsing
        Sitzungen in  between. If only year is given, return 1.1.YEAR, 31.12.YEAR.
        If additionally a month is given, return 1.MONTH.YEAR, LAST_DAY.MONTH.YEAR.'''

        last_day = self.last_day_of_month(year, month)

        if month:
            tmp = month
            if len(month) == 1:
                month = '0' + month
            return "01." + month + "." + year, last_day + month + "." + year
        return "01.01." + year, last_day + year
