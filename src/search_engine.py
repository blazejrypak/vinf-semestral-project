from collections import defaultdict
import os
import pickle
from typing import OrderedDict
from tokenizer import Tokenizer
import time
import re
import math
import pprint
from docs_reader import DocsReader
class SearchEngine:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.docs_reader = DocsReader()
        self.start = None
        self.end = None

    def query_search(self):
        queries = input("Enter query: ")
        self.start = time.time()
        queries = queries.lower()
        queries = re.sub('[^a-z0-9 ]', ' ', queries) # clean queries
        queries, temp = self.tokenizer.tokenize(queries)
        return queries

    def readIO(self, filename):
        with open(filename, 'rb') as f:
            index = pickle.loads(f.read())
        return index


    def writeIO(self, filename, index):
        with open(f'{filename}.txt', 'wb') as file:
            pickle.dump(index, file)

    def compute_idf(self, query, idf):
        if query in idf:
            return math.log(self.docs_reader.stats['readed_docs']/idf[query])
        else:
            return 0

    def compute_tf(self, query, docID, tf, count):
        try:
            a = tf[query][docID]
        except IndexError:
            return 0, 0
        if query in tf:
            if tf[query][docID] == 0:
                return 0, count
            else:
                count = count + 1
                return math.log(1 + tf[query][docID]), count
        else:
            return 0, 0

    def scores(self, queries):
        docID = 1
        count = 0
        scores = defaultdict(int)
        tf = self.readIO("tf.txt")
        idf = self.readIO("idf.txt")
        for doc in range(0, 200):
            score = 0
            for query in queries:
                if len(queries) > 1:
                    idf_score = self.compute_idf(query, idf)
                else:
                    idf_score = 1

                tf_score, flag = self.compute_tf(query, docID, tf, count)

                if flag != 0:
                    count = flag
                score = score + idf_score * tf_score
            scores[docID] = score
            docID = docID + 1

        self.writeIO("scores", scores)   
        return scores, count

    def rank(self, scores):
        ranks = OrderedDict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
        self.writeIO("ranks", ranks)
        docIDs = []
        for k, v in ranks.items():
            if v > 0 and len(docIDs) < 10:
                docIDs.append(k)
                continue
            else:
                break
        return docIDs

    def run(self):
        queries = self.query_search()
        scores, count = self.scores(queries)
        docIDs = self.rank(scores)
        docs = self.docs_reader.get_docs(docIDs)
        for doc in docs:
            print(doc['url'])



searchEngine = SearchEngine()
searchEngine.run()