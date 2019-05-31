# Risse README

Scraper to scrape PDFs from german Ratsinformationssysteme (Risse).

## TODO

* ~~git/GitHub versioning~~
* docstrings
* refactor general structure
* ~~markup readme~~
* software tests
* fix schaltjahre
* improve logger
* download validation
* starter script (configuration file???)
* IBM cloud API interface
* extend for more scrapers
* url in docstrings for which site it works on
* flow diagram how each scraper scrapes
* Dortmund Integrationsrat is not being parsed!
* add DEBUG variable for only parsing a specific Gremium for testing purposes

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
Scraper:
Main Page -> extend all Gremien -> Gremium -> Sitzungen -> Sitzung (HTML), Anlagen
```
scrapy crawl dortmund -a stadt=Dortmund -a url=https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView -a root=test -a year=2018 -a month=3 -a overwrite=True
```

### Bochum
Scraper:
Main page -> "Gremien" -> GremiumName -> Sitzungen -> if date fits: scrape Einladung, Niederschrift,  Sitzung -> Scrape all Sitzung PDFs (with their topic and TOP)

```
scrapy crawl bochum -a stadt=Bochum -a url=https://session.bochum.de/bi/infobi.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```

### Mülheim
Scraper:
Main page -> "Kalender" -> ASP requests for Sitzungen for fitting months -> Sitzung -> Niederschrift, Topics -> for each topic Beratungsverlauf, Anlagen, Vorlagen ->  all Anlagen for each Vorlage

```
scrapy crawl muelheim -a stadt=Mülheim -a url=https://ratsinfo.muelheim-ruhr.de/buerger/allris.net.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```