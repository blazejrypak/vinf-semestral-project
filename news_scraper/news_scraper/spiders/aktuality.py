import json
from typing_extensions import ParamSpec
import scrapy
from scrapy.spiders import CrawlSpider
from scrapy.spiders.crawl import Rule
from scrapy.linkextractors import LinkExtractor
import re
from news_scraper.items import ArticleItem, ArticleHtmlItem
from scrapy.http import Request
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from news_scraper.conf import EMAIL, PASSWORD
from pprint import pprint

chromeOptions = {
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Mobile Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'sk-sk',
    'Cache-Control': 'max-age=31536000',
    'DNT': '1',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
}
class AktualitySpider(CrawlSpider):
    name = 'aktuality'
    allowed_domains = ['aktuality.sk']

    start_urls = ['https://www.aktuality.sk']
    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.options = webdriver.ChromeOptions()
        self.login_page = 'https://konto.aktuality.sk/prihlasenie'
        self.cookies = None
        for key in chromeOptions.keys():
            self.options.add_argument(f'{key}={chromeOptions[key]}')
        self.options.headless = True
        self.driver = None
        self.debug_site_graph_depth = 0
        self.debug = False
        self.headers = {}

    article_link_extractor = LinkExtractor(
        allow=r"www.aktuality.sk/clanok/[a-zA-Z0-9]*/", allow_domains='aktuality.sk', unique=True)
    pagination_link_extractor = LinkExtractor(
        allow=r"www.aktuality.sk/spravy/.*/\d/", allow_domains='aktuality.sk', unique=True)
    section_link_extractor = LinkExtractor(
        allow=r"www.aktuality.sk/spravy/.*/", allow_domains='aktuality.sk', unique=True)
    rules = [
        Rule(section_link_extractor, process_request='process_request_cookies', follow=True),
        Rule(pagination_link_extractor, process_request='process_request_cookies', follow=True),
        Rule(article_link_extractor, callback='parse_article', process_request='process_request_cookies'),
    ]

    def process_exception(self, request, exception, spider):
        request.dont_filter = True
        return request

    def process_request_cookies(self, request, spider):
        if self.cookies:
            request.cookies = self.cookies
        return request

    def login(self):
        self.driver = webdriver.Chrome(chrome_options=self.options)
        self.logger.info('Openning login page')
        self.driver.get(self.login_page)
        time.sleep(5)
        self.driver.find_element(By.ID, ('account-email')).send_keys(EMAIL)
        self.driver.find_element(By.ID, ('password')).send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, ('.submit-btn')).click()
        time.sleep(5)
        self.logger.info('Gonna get session cookies')
        self.cookies = {cookie['name']: cookie['value']
                        for cookie in self.driver.get_cookies()}
        self.driver.quit()
        time.sleep(5)
        self.logger.info('Successfully logged in')
        return self.cookies

    def open_spider(self, spider):
        self.login()

    def start_requests(self):
        if not self.cookies:
            self.login()
        self.logger.info('Starting scraping...')
        for url in self.start_urls:
            yield Request(url=url, cookies=self.cookies, dont_filter=False)

    def parse_article(self, response):
        title = str(response.css('#account-button-title::text').get()).strip()
        if 'rypak.b@...' in title:
            yield ArticleHtmlItem(url=response.url, article_html_body=response.css('body').get())
        else:
            self.logger.info(title)
            self.login()
            yield scrapy.Request(url=response.url, cookies=self.cookies, callback=self.parse_article)