# -*- coding: utf-8 -*-

import datetime, logging, os

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
        descriptor = 'w' if is_html else 'wb'
        message = 'HTML' if is_html else 'PDF'
        
        # if overwrite or the path doesn't exist and there is content, write the file
        if self.overwrite or not os.path.isfile(path) and content: 
            with open(path, descriptor) as f:
                f.write(content)
                logging.info('Saving %s %s', message, path)

    def save_pdf(self, response):
        # full_path = response.meta['path']
        self.save_file(response.meta['path'], response.body, False)

        # # test for overwrite
        # if self.overwrite or not os.path.isfile(full_path):
        #     with open(full_path, 'wb') as f:
        #         f.write(response.body)
        # # logging should happen here

    def create_directories(self, path):
        if not os.path.isdir(path):
            os.makedirs(path) 

    def parse_mapping(self, path):
        mapping = {}

        with open(path, 'r') as f:
            for line in f.readlines():
                key, short = line.split('=')
                mapping[key] = short

        return mapping
