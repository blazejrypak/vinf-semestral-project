#### To run scraper:
You need to install Chrome Browser and chromedriver
`wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`

`sudo dpkg -i google-chrome-stable_current_amd64.deb`

`sudo apt-get install chromium-chromedriver`

`cd news_scraper`

`scrapy crawl aktuality`

#### Inštalácia softvéru a spustenie
Stiahnutie obrazu `bubkor/jupyter-pylucene` z Docker Hub

V termináli v adresári, ktorý obsahuje uložený index a graf spustí nasledujúci príkaz:

 `docker run -it -p 8888:8888 -e JUPYTER_ENABLE_LAB=yes -v "${PWD}":/usr/src bubkor/jupyter-pylucene`
 
Otvor v prehliadači link z terminálu

Spustí jupyter-notebook s programom

Vyhľadávaj
