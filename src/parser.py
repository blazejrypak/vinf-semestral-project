import jsonlines
from scrapy.http import TextResponse
import re
import json
from pprint import  pprint

def parse_article(filepath):
    content = jsonlines.open(filepath).read(type=dict)
    response = TextResponse(url=content['url'], body=content['article_html_body'], encoding='utf-8')
    title = response.css('#article > div.article-headline-wrapper > h1').xpath('//h1/span/text()').get()
    article_body = response.css('.fulltext')
    article_content = ''
    for p in article_body.css('p::text').getall():
        article_content += re.sub('\s+', ' ', str(p)) + ' '
    result = {
        "url": content['url'],
        "title": '',
        "body": article_content
    }
    if title:
        result['title'] = title
    return result
    
    
# with open('test_parse_file.json', mode='w') as sample_file:
#     with open('/Users/blazejrypak/Projects/vinf-project/html_collection/sample.html', 'r') as html:
#         content = html.read()
#         obj = {
#             "url": "https://www.aktuality.sk/clanok/4flrcv3/koronavirus-lengvarsky-bude-trvat-na-tom-co-navrhlo-konzilium-odbornikov-heger-uz-avizuje-raznejsi-pristup/",
#             "article_html_body": content
#         }
#         sample_file.write(json.dumps(obj))


pprint(parse_article('test_parse_file.json'))