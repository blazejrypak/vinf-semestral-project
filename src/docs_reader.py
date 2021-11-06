import pickle
import jsonlines
import os
import json
import atexit
import settings

class DocsReader:
    def __init__(self):
        self.collection_path = '/Users/blazejrypak/Projects/vinf-project/test_collection/' if settings.DEGUG else '/Users/blazejrypak/Projects/vinf-project/collection/'
        self.collection = iter(sorted(os.listdir(self.collection_path)))
        self.current_file_path = ''
        self.docID = -1
        self.stats = {}
        atexit.register(self.save_stats)
        self.load_stats()

    def load_stats(self):
        try:
            with open(f'{settings.INDEX_BASE_PATH}docs_reader_stats.txt', 'rb') as f:
                stats = pickle.load(f)
                if stats:
                    self.stats = stats
                else:
                    self.stats = {}
        except (OSError, IOError) as e:
            self.stats = {}

    def save_stats(self):
        with open(f'{settings.INDEX_BASE_PATH}docs_reader_stats.txt', 'wb') as f:
            pickle.dump(self.stats, f)
        with open(f'{settings.INDEX_BASE_PATH}docs_reader_stats_hr.txt', 'w') as f:
            f.write(json.dumps(self.stats, indent=4, separators=(',', ': ')))

    def __iter__(self):
        return self

    def __next__(self):
        self.docID += 1
        self.current_file_path = next(self.collection)
        self.stats['readed_docs'] = self.docID + 1
        try:
            return jsonlines.open(self.collection_path + self.current_file_path).read(type=dict)
        except Exception as e:
            self.__next__()

    def get_docID(self):
        return self.docID

    def get_current_filename(self):
        return self.current_file_path

    def get_docs(self, docIDs):
        if not any(docIDs):
            return []
        docs = []
        curr_doc_id = 0
        for doc in self:
            if curr_doc_id in docIDs:
                docs.append(doc)
            curr_doc_id += 1
        return docs
