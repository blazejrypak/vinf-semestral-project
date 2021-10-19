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
from pprint import pprint
import settings
import networkx as nx
import matplotlib.pyplot as plt


class SearchEngine:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.docs_reader = DocsReader()
        self.start = None
        self.end = None
        self.tf = self.readIO("tf.txt")
        self.df = self.readIO("df.txt")
        self.count_tokens_per_doc = self.readIO("count_tokens_per_doc.txt")
        self.G = self.load_graph()

    def load_graph(self):
        try:
            return nx.read_gml(f'{settings.GRAPH_BASE_PATH}index.gml')
        except nx.NetworkXError:
            return None

    def query_search(self):
        if self.G is not None:
            print("If you want find connections between entities write them in this format: connections: <Robert Fico>; <Peter Pellegrini>; ...")
        queries = input("Enter query: ")
        if self.G is not None:
            any_connections = re.findall('connections:.*;', queries)
            connections_entities_to_find = []
            for connections in any_connections:
                entities = connections.findall('<([a-zA-Z ]*)>', connections)
                connections_entities_to_find.append(entities)
        self.start = time.time()
        queries = queries.lower()
        queries = re.sub('[^a-z0-9 ]', ' ', queries)  # clean queries
        queries, temp = self.tokenizer.tokenize(queries)
        return temp, connections_entities_to_find

    def readIO(self, filename):
        try:
            with open(settings.INDEX_BASE_PATH + filename, 'rb') as f:
                index = pickle.loads(f.read())
            return index
        except FileNotFoundError:
            print(f'No such file to read: {filename}')
            exit(1)

    def writeIO(self, filename, index):
        with open(f'{settings.INDEX_BASE_PATH}{filename}.txt', 'wb') as file:
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
        D = np.zeros(
            (self.docs_reader.stats['readed_docs'], len(tf_idf.keys())))
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
        ranks = OrderedDict(
            sorted(scores.items(), key=lambda x: x[1], reverse=True))
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
        queries_tf, connections_entities_to_find = self.query_search()
        tf_idf = self.compute_tf_idf()
        matching_score_scores = self.matching_score(
            list(queries_tf.keys()), tf_idf)
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
        for connections_entities in connections_entities_to_find:
            neighbors = []
            for entity in connections_entities:
                neighbors.extend(self.G.adj[entity])
            print(connections_entities, ': ')
            print(set(neighbors))
        # pos = nx.spring_layout(self.G)
        # nx.draw_networkx(self.G, pos=pos)
        # options = {
        #     "font_size": 36,
        #     "node_size": 3000,
        #     "node_color": "white",
        #     "edgecolors": "black",
        #     "linewidths": 5,
        #     "width": 5,
        # }
        # ax = plt.gca(options=options)
        # ax.margins(0.3)
        # ax.margins(0.20)
        # plt.axis("off")
        # plt.rcParams["figure.autolayout"] = True
        # plt.show()


searchEngine = SearchEngine()
searchEngine.run()
