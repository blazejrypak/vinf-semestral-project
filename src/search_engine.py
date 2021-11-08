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
from pprint import pp, pprint
import settings
import networkx as nx
import matplotlib.pyplot as plt
import regex


class SearchEngine:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.docs_reader = DocsReader()
        self.start = None
        self.end = None
        self.tf = None
        self.df = None
        self.count_tokens_per_doc = None
        self.load_indexes()
        self.tf_idf = self.compute_tf_idf()
        self.docID2docFileName = self.readIO('docID2docFileName.txt')
            
    def load_indexes(self):
        self.tf = self.readIO("tf.txt")
        self.df = self.readIO("df.txt")
        self.count_tokens_per_doc = self.readIO("count_tokens_per_doc.txt")

    def load_graph(self):
        try:
            return nx.read_gml(f'{settings.GRAPH_BASE_PATH}index.gml')
        except nx.NetworkXError:
            return None

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
        tf_idf = defaultdict(dict)
        for docID in range(self.docs_reader.stats['readed_docs']):
            for token in self.tf.keys():
                token_tf_w = self.compute_tf(token, docID)
                token_idf_w = self.compute_idf(token)
                if tf_idf.get(token, None):
                    tf_idf[token][docID] = token_tf_w*token_idf_w
                else:
                    tf_idf[token] = {docID: token_tf_w*token_idf_w}
        return tf_idf

    def matching_score(self, queries, tf_idf):
        queries_weights = defaultdict(float)
        for token in queries:
            if tf_idf.get(token, None):
                docs_weights = tf_idf[token]
                for docID in docs_weights.keys():
                    if queries_weights.get(docID, None):
                        if queries_weights[docID] == -1:
                            continue
                        else:
                            queries_weights[docID] += docs_weights[docID]
                    else:
                        if self.tf[token][docID] != 0:
                            queries_weights[docID] += docs_weights[docID]
                        else:
                            queries_weights[docID] = -1
        
        for w in queries_weights.copy().keys():
            if queries_weights[w] == -1:
                del queries_weights[w]                  
        return queries_weights

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

    def terminal_show_commands(self):
        print('If you want to exit program, them enter: exit')
        print("If you want find connections between entities write them in this format: connections: <Robert Fico>; <Peter Pellegrini>; ...")
        print('Enter query: ')

    def get_connections_if_any(self, query):
        any_connections = re.search('connections:.*;', query)
        connections_entities_to_find = []
        if any_connections:
            self.G = self.load_graph()
            any_connections = any_connections.group(
                0).replace('connections:', '')
            entities = regex.findall('([a-zA-Z ]*)', any_connections)
            connections_entities_to_find = [
                entity.strip() for entity in entities if entity != '']
        return connections_entities_to_find

    def get_clean_query_tf(self, query):
        query = query.replace('connections:', '')
        query = re.sub(';', '', query)
        query, queries_tf = self.tokenizer.tokenize(query)
        return queries_tf

    def get_docs(self, docsIDs):
        docs_filenames = []
        for docID in docsIDs:
            doc_filename = self.docID2docFileName.get(docID, None)
            if doc_filename:
                docs_filenames.append(doc_filename)
        return self.docs_reader.get_docs_by_file_name(docs_filenames)

    def run(self):
        while True:
            self.terminal_show_commands()
            command = input()
            if command == "exit":
                break
            else:
                start = time.time()
                connections_entities = self.get_connections_if_any(command)
                query_tf = self.get_clean_query_tf(command)
                matching_score_scores = self.matching_score(
                    list(query_tf.keys()), self.tf_idf)
                docIDs = self.rank(matching_score_scores)
                docs = self.get_docs(docIDs)
                if not any(docs):
                    print('We did not found anything relevant')
                else:
                    print('\nFound results: \n')
                    for doc in docs:
                        if doc.get('title', None):
                            print('\t', doc['title'])
                        print('\t', doc['url'])
                        print()

                neighbors = set()
                for entity in connections_entities:
                    try:
                        neighbors.update(x[0] for x in sorted(
                            self.G[entity].items(), key=lambda edge: edge[1]['weight']))
                    except KeyError:
                        pass
                if neighbors:
                    print('\n', connections_entities, ': ', ', '.join(
                        list(neighbors - set(connections_entities))[:10]))
                end = time.time()
                print("running time: ", str(end - start))


searchEngine = SearchEngine()
searchEngine.run()
