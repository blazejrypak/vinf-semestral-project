from collections import Counter, defaultdict
import os
import pickle
from typing import OrderedDict
from tokenizer import Tokenizer
import time
import re
import math
from docs_reader import DocsReader
import numpy as np
from  pprint import pprint
class SearchEngine:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.docs_reader = DocsReader()
        self.start = None
        self.end = None
        self.tf = self.readIO("tf.txt")
        self.df = self.readIO("df.txt")
        self.count_tokens_per_doc = self.readIO("count_tokens_per_doc.txt")

    def query_search(self):
        queries = input("Enter query: ")
        self.start = time.time()
        queries = queries.lower()
        queries = re.sub('[^a-z0-9 ]', ' ', queries) # clean queries
        queries, temp = self.tokenizer.tokenize(queries)
        return temp

    def readIO(self, filename):
        try:
            with open(filename, 'rb') as f:
                index = pickle.loads(f.read())
            return index
        except FileNotFoundError:
            print(f'No such file to read: {filename}')
            exit(1)

    def writeIO(self, filename, index):
        with open(f'{filename}.txt', 'wb') as file:
            pickle.dump(index, file)

    def compute_idf(self, query):
        if query in self.df:
            return math.log10(self.docs_reader.stats['readed_docs']/self.df[query])
        else:
            return 0

    def compute_tf(self, query, docID):
        if not self.count_tokens_per_doc[docID]:
            return 0
        if query in self.tf:
            return self.tf[query][docID]/self.count_tokens_per_doc[docID]
        return 0

    def compute_tf_idf(self):
        tf_idf = defaultdict(float)
        for docID in range(self.docs_reader.stats['readed_docs']):
            for token in self.tf.keys():
                token_tf_w = self.compute_tf(token, docID)
                token_idf_w = self.compute_idf(token)
                tf_idf[docID, token] = token_tf_w*token_idf_w

        return tf_idf

    def matching_score(self, queries, tf_idf):
        queries_weights = defaultdict(float)
        for key in tf_idf.keys():
            if key[1] in queries:
                queries_weights[key[0]] = tf_idf[key]

        return queries_weights    

    def get_total_number_of_tokens(self):
        total = 0
        for key in self.count_tokens_per_doc.keys():
            total += self.count_tokens_per_doc[key]
        return total

    def vectorization(self, queries, tf_idf):
        scores = {}
        D = np.zeros((self.docs_reader.stats['readed_docs'], len(tf_idf.keys())))
        for key in tf_idf.keys():
            ind = list(self.tf.keys()).index(key[1])
            D[key[0]][ind] = tf_idf[key]
        
        Q = np.zeros((1, len(tf_idf.keys())))
        for key in tf_idf.keys():
            if key[1] in queries:
                ind = list(self.tf.keys()).index(key[1])
                Q[0][ind] = tf_idf[key]
            
        for docID in range(D.shape[0]):
            product = np.dot(Q, D[docID])
            norms = np.linalg.norm(Q)*np.linalg.norm(D[docID])
            if norms > 0:
                scores[docID] = product/norms
            else:
                scores[docID] = 0
        return scores

    def rank(self, scores):
        ranks = OrderedDict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
        # self.writeIO("ranks", ranks)
        docIDs = []
        for k, v in ranks.items():
            if v > 0 and len(docIDs) < 10:
                docIDs.append(k)
                continue
            else:
                break
        return docIDs

    def run(self):
        pprint(self.tf)
        queries_tf = self.query_search()
        tf_idf = self.compute_tf_idf()
        matching_score_scores = self.matching_score(list(queries_tf.keys()), tf_idf)
        # cosine_similarity_scores = self.vectorization(list(queries_tf.keys()), tf_idf)
        # pprint(matching_score_scores)
        # pprint.pprint(cosine_similarity_scores)
        # print('results retrieved based on matching score: \n')
        docIDs = self.rank(matching_score_scores)
        docs = self.docs_reader.get_docs(docIDs)
        for doc in docs:
            print(doc['url'])
        # print('results retrieved based on cosine similarity: \n')
        # docIDs = self.rank(cosine_similarity_scores)
        # docs = self.docs_reader.get_docs(docIDs)
        # for doc in docs:
        #     print(doc['url'])


searchEngine = SearchEngine()
searchEngine.run()