import jsonlines
import os

class DatasetReader():
    def __init__(self):
        self.data_path = os.path.join(os.path.dirname, '../data')
        self.reader = open('/Users/blazejrypak/Projects/vinf-project/data/03-10-2021-21-13-43-article.json')

