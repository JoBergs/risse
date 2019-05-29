# Risse README

Scraper to scrape PDFs from german Ratsinformationssysteme (Risse).

## TODO

* docstrings
* richt text readme
* software tests
* fix schaltjahre
* sample html files of scraped structure
* improve logger
* download validation
* starter script
* IBM cloud API interface


## Usage

Currently, three scrapers are implemented for the cities Dortmund, Bochum
and Mühlheim.

They are run with the command
```
scrapy crawl SPIDERNAME -a stadt=CITY -a url=URL -a root=RESULTPATH -a year=YEAR -a month=MONTH -a overwrite=BOOL
```