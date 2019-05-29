# -*- coding: utf-8 -*-

import os

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

        map_path = os.path.join('risse', 'spiders', self.stadt + '.txt')
        self.mapping = self.parse_mapping(map_path)

    def save_pdf(self, response):
        full_path = response.meta['path']

        # test for overwrite
        if self.overwrite == True or not os.path.isfile(full_path):
            with open(full_path, 'wb') as f:
                f.write(response.body)

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
