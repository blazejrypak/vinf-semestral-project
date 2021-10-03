from typing_extensions import ParamSpec
import scrapy
from scrapy.spiders import CrawlSpider
from scrapy.spiders.crawl import Rule
from scrapy.linkextractors import LinkExtractor
import re
from news_scraper.items import ArticleItem
from scrapy.http import Request, FormRequest, request
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import time
from news_scraper.conf import EMAIL, PASSWORD

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'navigate',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
}

class ArticleSpider(scrapy.Spider):
    name = 'article'
    allowed_domains = ['aktuality.sk']
    start_urls = ['https://www.aktuality.sk/clanok/w38ccd1/narast-napatia-i-nestability-co-vsetko-sa-na-juhu-kaukazu-zmenilo-od-vojny-o-karabach/']

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.options = webdriver.ChromeOptions()
        self.login_page = 'https://konto.aktuality.sk/prihlasenie'
        self.cookies = None
        for key in headers.keys():
            self.options.add_argument(f'{key}={headers[key]}')
        self.driver = webdriver.Chrome(chrome_options=self.options)

    def start_requests(self):
        self.driver.get(self.login_page)
        time.sleep(5)
        self.driver.find_element(By.ID, ('account-email')).send_keys(EMAIL)
        self.driver.find_element(By.ID, ('password')).send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, ('.submit-btn')).click()
        time.sleep(5)
        self.cookies = {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()}
        time.sleep(5)
        yield Request(url='https://www.aktuality.sk/clanok/w38ccd1/narast-napatia-i-nestability-co-vsetko-sa-na-juhu-kaukazu-zmenilo-od-vojny-o-karabach/', cookies=self.cookies)
        self.driver.quit()

    def make_requests_from_url(self, url):
        request = super(ArticleSpider, self).make_requests_from_url(url)
        if self.cookies:
            request.cookies = self.cookies
        return request

    def parse(self, response):
        datetime_str = str(response.css('.date::text').get()).strip('\n ')
        date_str = re.search(r'\d{2}.\d{2}.\d{4}', datetime_str)
        time_str = re.search(r'\d{2}:\d{2}', datetime_str)
        article_body = response.css('.fulltext')
        content = ''
        for p in article_body.css('p::text').getall():
            content += re.sub('\s+',' ',str(p))
        yield {
            'body': re.sub('Aktivujte[\s\S]*nami.', '', content),
            'url': response.url,
            'datetime': str(f'{date_str.group()}:{time_str.group()}')
        }
    


class AktualitySpider(CrawlSpider):
    name = 'aktuality'
    allowed_domains = ['aktuality.sk']
    start_urls = ['https://www.aktuality.sk/spravy/slovensko/']

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.options = webdriver.ChromeOptions()
        self.login_page = 'https://konto.aktuality.sk/prihlasenie'
        self.cookies = None
        for key in headers.keys():
            self.options.add_argument(f'{key}={headers[key]}')
        self.driver = webdriver.Chrome(chrome_options=self.options)

    article_link_extractor = LinkExtractor(allow=r"https:\/\/www.aktuality.sk/clanok/[a-zA-Z0-9]*/", allow_domains='aktuality.sk', unique=True)
    pagination_link_extractor = LinkExtractor(allow=r"https://www.aktuality.sk/spravy/.*/\d/", allow_domains='aktuality.sk', unique=True)
    section_link_extractor = LinkExtractor(allow=r"https://www.aktuality.sk/spravy/.*/", allow_domains='aktuality.sk', unique=True)
    rules = [
        Rule(article_link_extractor, callback='parse_article', process_request='process_request_cookies'),
        Rule(pagination_link_extractor, process_request='process_request_cookies'),
        Rule(section_link_extractor, process_request='process_request_cookies')
    ]

    def process_request_cookies(self, request, spider):
        if self.cookies:
            request.cookies = self.cookies
        return request

    def start_requests(self):
        self.driver.get(self.login_page)
        time.sleep(5)
        self.driver.find_element(By.ID, ('account-email')).send_keys(EMAIL)
        self.driver.find_element(By.ID, ('password')).send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, ('.submit-btn')).click()
        time.sleep(5)
        self.cookies = {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()}
        time.sleep(5)
        yield Request(url='https://www.aktuality.sk', cookies=self.cookies)
        self.driver.quit()

    def make_requests_from_url(self, url):
        request = super().make_requests_from_url(url)
        request.cookies = self.cookies
        return request

    def parse_article(self, response):
        title = response.xpath('//*[@id="article"]/h1/span/text()').get()
        datetime_str = str(response.css('.date::text').get()).strip('\n ')
        date_str = re.search(r'\d{2}.\d{2}.\d{4}', datetime_str)
        time_str = re.search(r'\d{2}:\d{2}', datetime_str)
        article_body = response.css('.fulltext')
        content = ''
        for p in article_body.css('p::text').getall():
            content += re.sub('\s+',' ',str(p))
        output_datetime = ''
        if date_str:
            output_datetime += date_str.group()
            if time_str:
                output_datetime += ':'
                output_datetime += time_str.group()
        article = ArticleItem(url=response.url, title=title, body = content, datetime = output_datetime)
        return article