import jsonlines
import os

class DocsReader:
    def __init__(self, file_path='/Users/blazejrypak/Projects/vinf-project/data/03-10-2021-21-13-43-article.json'):
        self.current_file_path = file_path
        self.reader = jsonlines.open(self.current_file_path)
        self.docID = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            self.docID += 1
            if(self.docID == 200): raise StopIteration
            return self.reader.read(type=dict)
        except EOFError:
            raise StopIteration

    def get_docID(self):
        return self.docID

    def get_current_filename(self):
        head, tail = os.path.split(self.current_file_path)
        return head.split('.')[0]

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