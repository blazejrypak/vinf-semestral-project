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
        self.tf_idf = None
        self.load_indexes()
            
    def load_indexes(self):
        self.tf = self.readIO("tf.txt")
        self.tf_idf = self.readIO("tf_idf.txt")
        self.docID2docFileName = self.readIO('docID2docFileName.txt')

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

    def matching_score(self, queries, tf_idf):
        queries_weights = defaultdict(float)
        temp = defaultdict(int)
        for token in queries:
            if tf_idf.get(token, None):
                docs_weights = tf_idf[token]
                for docID in docs_weights.keys():
                    if self.tf[token][docID] != 0:
                        queries_weights[docID] += docs_weights[docID]
                        temp[docID] += 1

        for docID in queries_weights.copy().keys():
            if temp[docID] != len(queries):
                del queries_weights[docID]              
        return queries_weights

    def rank(self, scores):
        ranks = OrderedDict(
            sorted(scores.items(), key=lambda x: x[1], reverse=True))
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