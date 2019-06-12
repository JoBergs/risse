# Risse README

Scraper to scrape PDFs from german Ratsinformationssysteme (Risse).
BLABLABLABL

## TODO

* ~~git/GitHub versioning~~
* ~~docstrings~~
* ~~refactor general structure~~
* ~~markup readme~~
* ~~(some)~~ software tests
* ~~fix schaltjahre~~
* improve logger
* download validation
* starter script (configuration file???)
* IBM cloud API interface
* extend for more scrapers
* ~~url in docstrings for which site it works on~~
* ~~flow diagram how each scraper scrapes~~
* ~~Dortmund Integrationsrat and many other are not being scraped!~~
* Scrape Dortmund Archiv as well???
* add DEBUG variable for only parsing a specific Gremium for testing purposes
* ~~BUG: only year as CLI parameter doesn't work~~

###Starter Script

Prio1days=14  # kommende 14 Tage
prio1=daily
prio1exeptionday=1,7
prio2=weekly
prio2day=1
Prio2days=365  # vergangene Tage (consider leap years)
Prio3 gesamter Zeitraum einmal im Monat

1 Ini for every City (with the parameters above)
1 main Ini (decides which scraper will run amd where the results will be stored)

Vorhergehende Monate sollen Schrittweise abgegrast werden


## Installation (Linux)
Enter in the terminal
```
sudo pip3 install scrapy git pytest
git clone https://github.com/JoBergs/risse.git
```

## Installation (Windows)
This assumes Python is already installed.

For Scrapy see
*https://www.accordbox.com/blog/scrapy-tutorial-4-how-install-scrapy-windows/*

For git see
*https://www.jamessturtevant.com/posts/5-Ways-to-install-git-on-Windows/*

For PyTest (optional) see
*https://docs.pytest.org/en/latest/getting-started.html#installation-issues*

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

Currently, three scrapers are implemented for the RISSE allris(Mülheim), dorat (Dortmund) and somacos (Bochum).

They are run with the command (executed in the risse base directory)
```
scrapy crawl RISSENAME -a stadt=CITY -a url=URL -a root=RESULTPATH -a year=YEAR -a month=MONTH -a overwrite=BOOL
```

### dorat
Scraper:
Main Page -> extend all Gremien -> Gremium -> Sitzungen -> Sitzung (HTML), Anlagen
```
scrapy crawl dorat -a stadt=Dortmund -a url=https://dosys01.digistadtdo.de/dosys/gremniedweb1.nsf/NiederschriftenWeb?OpenView -a root=test -a year=2018 -a month=3 -a overwrite=True
```

### somacos
Scraper:
Main page -> "Gremien" -> GremiumName -> Sitzungen -> if date fits: scrape Einladung, Niederschrift,  Sitzung -> Scrape all Sitzung PDFs (with their topic and TOP)

```
scrapy crawl somacos -a stadt=Bochum -a url=https://session.bochum.de/bi/infobi.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```

### allris

Scraper:
Main page -> "Kalender" -> ASP requests for Sitzungen for fitting months -> Sitzung -> Niederschrift, Topics -> for each topic Beratungsverlauf, Anlagen, Vorlagen ->  all Anlagen for each Vorlage

#### Muelheim
```
scrapy crawl allris -a stadt=Mülheim -a url=https://ratsinfo.muelheim-ruhr.de/buerger/allris.net.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```

#### Herne
```
scrapy crawl allris -a stadt=Herne -a url=https://www.herne.de/Rathaus/Politik/Ratsinformationssystem/ -a root=test -a year=2018 -a month=3 -a overwrite=True
```

#### Oberhausen
```
scrapy crawl allris -a stadt=Oberhausen -a url=https://allris.oberhausen.de/bi/allris.net.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```

#### Selm
```
scrapy crawl allris -a stadt=Selm -a url=https://www.sitzungsdienst-selm.de/bi/allris.net.asp -a root=test -a year=2018 -a month=3 -a overwrite=True
```

#### Hagen
```
scrapy crawl allris -a stadt=Hagen -a url=https://www.hagen.de/irj/portal/AllrisB -a root=test -a year=2018 -a month=3 -a overwrite=True
```



## Software tests

To run the software tests, enter in the Scraper base directory ./risse
```
sudo py.test risse/tests
```
(Pass -s for running ipdb in tests.)