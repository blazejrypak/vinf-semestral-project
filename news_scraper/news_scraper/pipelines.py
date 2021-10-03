# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exporters import JsonLinesItemExporter
import datetime

class NewsScraperExporterPipeline(object):
    """Bulk items exporter"""

    def open_spider(self, spider):
        self.current_exporter = JsonLinesItemExporter(file=self.get_file(), encoding='utf-8', indent=0)
        self.current_exporter_scraped_items = 0
        self.limit_bulk_items = 1200 # cca 1 hour of scraping
        self.current_exporter.start_exporting()

    def get_file(self):
        now = datetime.datetime.now()
        return open('/Users/blazejrypak/Projects/vinf-project/data/'+now.strftime("%d-%m-%Y-%H-%M-%S") + '-article.json', 'wb')

    def close_spider(self, spider):
        self.current_exporter.finish_exporting()

    def _exporter_for_item(self):
        if self.current_exporter_scraped_items >= self.limit_bulk_items:
            self.current_exporter = JsonLinesItemExporter(file=self.get_file(), encoding='utf-8', indent=0)
            self.current_exporter_scraped_items = 0
        return self.current_exporter

    def process_item(self, item, spider):
        self.current_exporter = self._exporter_for_item()
        self.current_exporter.export_item(item)
        self.current_exporter_scraped_items += 1
        return item
