import json
from typing_extensions import ParamSpec
import scrapy
from scrapy.spiders import CrawlSpider
from scrapy.spiders.crawl import Rule
from scrapy.linkextractors import LinkExtractor
import re
from news_scraper.items import ArticleItem
from scrapy.http import Request
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from news_scraper.conf import EMAIL, PASSWORD

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


class ArticleSpider(scrapy.Spider):
    name = 'article'
    allowed_domains = ['aktuality.sk']
    start_urls = [
        'https://www.aktuality.sk/clanok/w38ccd1/narast-napatia-i-nestability-co-vsetko-sa-na-juhu-kaukazu-zmenilo-od-vojny-o-karabach/']

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.options = webdriver.ChromeOptions()
        self.login_page = 'https://konto.aktuality.sk/prihlasenie'
        self.cookies = None
        for key in chromeOptions.keys():
            self.options.add_argument(f'{key}={chromeOptions[key]}')
        self.options.headless = True
        self.driver = webdriver.Chrome(chrome_options=self.options)

    def start_requests(self):
        self.driver.get(self.login_page)
        time.sleep(5)
        self.driver.find_element(By.ID, ('account-email')).send_keys(EMAIL)
        self.driver.find_element(By.ID, ('password')).send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, ('.submit-btn')).click()
        time.sleep(5)
        self.cookies = {cookie['name']: cookie['value']
                        for cookie in self.driver.get_cookies()}
        time.sleep(5)
        yield Request(url='https://www.aktuality.sk/clanok/w38ccd1/narast-napatia-i-nestability-co-vsetko-sa-na-juhu-kaukazu-zmenilo-od-vojny-o-karabach/', cookies=self.cookies, headers=chromeOptions)
        self.driver.quit()

    def make_requests_from_url(self, url):
        request = super(ArticleSpider, self).make_requests_from_url(url)
        if self.cookies:
            request.cookies = self.cookies
        request.headers = chromeOptions
        return request

    def parse_article(self, response):
        title = response.xpath('//*[@id="article"]/h1/span/text()').get()
        # datetime_str = str(response.css('.date::text').get()).strip('\n ')
        # date_str = re.search(r'\d{2}.\d{2}.\d{4}', datetime_str)
        # time_str = re.search(r'\d{2}:\d{2}', datetime_str)
        article_body = response.css('.fulltext')
        content = ''
        for p in article_body.css('p::text').getall():
            content += re.sub('\s+', ' ', str(p))
        # output_datetime = ''
        # if date_str:
        #     output_datetime += date_str.group()
        #     if time_str:
        #         output_datetime += ':'
        #         output_datetime += time_str.group()
        article = ArticleItem(url=response.url, title=title, body=content)
        return article


class AktualitySpider(CrawlSpider):
    name = 'aktuality'
    allowed_domains = ['aktuality.sk']
    start_urls = ['https://www.aktuality.sk', 'https://www.aktuality.sk/spravy/slovensko/', 'https://www.aktuality.sk/regiony/',
                  'https://www.aktuality.sk/spravy/zahranicne/', 'https://www.aktuality.sk/spravy/komentare/', 'https://www.aktuality.sk/cestovanie/', 'https://www.aktuality.sk/zdravie/', 'https://www.aktuality.sk/kultura/', 'https://www.aktuality.sk/premiove-citanie/']

    # start_urls = ['https://www.aktuality.sk']
    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.options = webdriver.ChromeOptions()
        self.login_page = 'https://konto.aktuality.sk/prihlasenie'
        self.cookies = None
        for key in chromeOptions.keys():
            self.options.add_argument(f'{key}={chromeOptions[key]}')
        self.options.headless = True
        self.driver = webdriver.Chrome(chrome_options=self.options)
        self.debug_site_graph_depth = 0
        self.debug = False

    article_link_extractor = LinkExtractor(
        allow=r"www.aktuality.sk/clanok/[a-zA-Z0-9]*/", allow_domains='aktuality.sk', unique=True)
    pagination_link_extractor = LinkExtractor(
        allow=r"www.aktuality.sk/spravy/.*/\d/", allow_domains='aktuality.sk', unique=True)
    # section_link_extractor = LinkExtractor(
    #     allow=r"www.aktuality.sk/spravy/.*/", allow_domains='aktuality.sk', unique=True)
    rules = [
        # Rule(section_link_extractor, process_request='process_request_cookies'),
        Rule(pagination_link_extractor, process_request='process_request_cookies'),
        Rule(article_link_extractor, callback='parse_article',
             process_request='process_request_cookies'),
    ]

    def process_exception(self, request, exception, spider):
        request.dont_filter = True
        return request

    def process_request_cookies(self, request, spider):
        if self.cookies:
            request.cookies = self.cookies
        # request.headers = headers # not working why?
        return request

    def start_requests(self):
        self.driver.get(self.login_page)
        time.sleep(5)
        self.driver.find_element(By.ID, ('account-email')).send_keys(EMAIL)
        self.driver.find_element(By.ID, ('password')).send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, ('.submit-btn')).click()
        time.sleep(5)
        self.cookies = {cookie['name']: cookie['value']
                        for cookie in self.driver.get_cookies()}
        self.driver.quit()
        time.sleep(5)
        for url in self.start_urls:
            yield Request(url=url, cookies=self.cookies)

    def _parse(self, response, **kwargs):
        if self.debug and self.debug_site_graph_depth < 5:
            links = []
            for rule_index, rule in enumerate(self._rules):
                links.extend(rule.link_extractor.extract_links(response))

            linkedUrls = []
            for l in links:
                linkedUrls.append(l.url)
            with open('./site.json', 'a') as file:
                root_node = {
                    'url': response.url,
                    'urlLinks': linkedUrls
                }
                file.write(json.dumps(root_node) + '\n')
            self.debug_site_graph_depth += 1
        return super()._parse(response, **kwargs)

    def parse_article(self, response):
        title = response.xpath('//*[@id="article"]/h1/span/text()').get()
        article_body = response.css('.fulltext')
        content = ''
        for p in article_body.css('p::text').getall():
            content += re.sub('\s+', ' ', str(p)) + ' '
        article = ArticleItem(url=response.url, title=title, body=content)
        return article
