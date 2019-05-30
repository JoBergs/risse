# Risse README

Scraper to scrape PDFs from german Ratsinformationssysteme (Risse).

## TODO

* docstrings
* refactor general structure
* richt text readme
* software tests
* fix schaltjahre
* sample html files of scraped structure
* improve logger
* download validation
* starter script
* IBM cloud API interface
* experiment with parameters in risse/risse/settings.py for more parallel requests
* extend for more scrapers
* ' ' to '-' for Linux in paths

## Installation (Linux)
Enter in the terminal
```
sudo pip3 install scrapy git
git clone https://github.com/JoBergs/risse.git
```

## Installation (Windows)
This assumes Python is already installed.

For Scrapy see
*https://www.accordbox.com/blog/scrapy-tutorial-4-how-install-scrapy-windows/*

For git see
*https://www.jamessturtevant.com/posts/5-Ways-to-install-git-on-Windows/*

Then, enter in the Terminal
```
git clone https://github.com/JoBergs/risse.git
```

## Update
```
cd risse
git pull origin master
```


## Usage

Currently, three scrapers are implemented for the cities Dortmund, Bochum
and Mühlheim.

They are run with the command (executed in the risse base directory)
```
scrapy crawl SPIDERNAME -a stadt=CITY -a url=URL -a root=RESULTPATH -a year=YEAR -a month=MONTH -a overwrite=BOOL
```

### Dortmund
```
scrapy crawl dortmund -a stadt=Dortmund -a url=https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView -a root=test -a year=2018 -a month=3 -a overwrite=True
```

### Bochum
```
scrapy crawl bochum -a stadt=Bochum -a url=https://session.bochum.de/bi/infobi.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```

### Mülheim
```
scrapy crawl muelheim -a stadt=Mülheim -a url=https://ratsinfo.muelheim-ruhr.de/buerger/allris.net.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```