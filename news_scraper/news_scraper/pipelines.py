# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from scrapy.exporters import JsonLinesItemExporter
import uuid

class NewsScraperExporterPipeline(object):

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        pass

    def process_item(self, item, spider):
        json_file = open('/Users/blazejrypak/Projects/vinf-project/html_collection/'+ str(uuid.uuid4()) + '.json', 'wb')
        exporter = JsonLinesItemExporter(file=json_file, encoding='utf-8', indent=0)
        exporter.start_exporting()
        exporter.export_item(item)
        exporter.finish_exporting()