from collections import Counter, defaultdict
import jsonlines
import unicodedata
import string
import re
import regex
import os
import time
import pprint
import gzip
from stemmer import SlovakStemmer
import pickle

from tokenizer import Tokenizer
from docs_reader import DocsReader
import json
import settings
import networkx as nx
from itertools import combinations

class Indexer:

    def __init__(self):
        self.tokenizer = Tokenizer()
        self.G = self.load_graph()
    
    def print_top_keywords_per_article(self, tf):
        for w in sorted(tf, key=lambda ele: sum(1 for x in tf[ele] if x != 0), reverse=True)[:10]:
            print(w)

    def add2tf(self, tf, tf_doc, docID):
        """Add new doc tokens tf to main TF table"""
        for token in tf_doc.keys():
            if token in tf:
                tf[token].append(tf_doc[token])
            else:
                zero_padding = [0]*docID
                if len(zero_padding):
                    tf[token].extend(zero_padding)
                    tf[token].append(tf_doc[token])
                else:
                    tf[token] = [tf_doc[token]]
        for token in tf.keys():
            if len(tf[token]) - 1 != docID:
                tf[token].extend([0] * (1 + docID - len(tf[token])))
        return tf
    
    def add2postingslist(self, tokens, fName, postingslist):
        if any(postingslist):
            for token in tokens:
                if token in postingslist:
                    postingslist[token].append(fName)
                else:
                    postingslist[token] = [fName]
        else:
            for token in tokens:
                postingslist[token] = [fName]
        return postingslist

    def save_graph(self):
        nx.write_gml(self.G, f'{settings.GRAPH_BASE_PATH}index.gml')
    
    def load_graph(self):
        try:
            return nx.read_gml(f'{settings.GRAPH_BASE_PATH}index.gml')
        except FileNotFoundError or nx.NetworkXError:
            return nx.Graph()

    def traverseDocs(self, tf, postingslist, count_tokens_per_doc):
        docsReader = DocsReader()
        for document in docsReader:
            tokens, tf_doc = self.tokenizer.tokenize_doc(document)
            for edge in combinations(self.tokenizer.person_entities, 2):
                if len(edge) == 2:
                    self.G.add_edge(edge[0], edge[1])
            for edge in combinations(self.tokenizer.company_entities, 2):
                if len(edge) == 2:
                    self.G.add_edge(edge[0], edge[1])
            self.add2tf(tf, tf_doc, docsReader.get_docID())
            postingslist = self.add2postingslist(tokens, docsReader.get_current_filename(), postingslist)
            count_tokens_per_doc[docsReader.get_docID()] = len(tokens)
        return postingslist, tf, count_tokens_per_doc

    def create_df(self, postingslist):
        df = defaultdict(int)
        for term in postingslist.keys():
            df[term] = len(postingslist[term])
        return df

    def writeIO(self, filename, index):
        with open(f'{settings.INDEX_BASE_PATH}{filename}.txt', 'wb') as file:
            pickle.dump(index, file)

    def run(self):
        """tf:
                {term: [xtimesInDocID-0, xtimesInDocID-1, xtimesInDocID-2, ...xTimesInDocID-X]}

            postingslist:
                {term: [DocID-0-FilePath, DocI-1-FilePath, DocID-2-FilePath]}

            df:
                {term: xtimesInAllDocs}
        """
        start = time.time()
        postingslist = defaultdict(list)
        tf = defaultdict(list)
        count_tokens_per_doc = defaultdict(int)
        postingslist, tf, count_tokens_per_doc = self.traverseDocs(tf, postingslist, count_tokens_per_doc)
        df = self.create_df(postingslist)
        end = time.time()
        print("running time: ", str(end - start))
        self.writeIO('tf', tf)
        self.writeIO('postingslist', postingslist)
        self.writeIO('df', df)
        self.writeIO('count_tokens_per_doc', count_tokens_per_doc)
        self.save_graph()


indexer = Indexer()
indexer.run()
# Dubaj 2020, COVID-19, (SaS), Hlas-SD