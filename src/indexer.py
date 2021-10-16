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

class Indexer:

    def __init__(self):
        self.tokenizer = Tokenizer()
    
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
                tf[token].extend([0] * (docID - len(tf[token])))
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

    def traverseDocs(self, tf, postingslist):
        docsReader = DocsReader()
        for document in docsReader:
            tokens, tf_doc = self.tokenizer.tokenize_doc(document)
            self.add2tf(tf, tf_doc, docsReader.get_docID())
            postingslist = self.add2postingslist(tokens, docsReader.get_current_filename(), postingslist)
        return postingslist, tf

    def create_idf(self, postingslist):
        idf = defaultdict(int)
        for term in postingslist.keys():
            idf[term] = len(postingslist[term])
        return idf

    def writeIO(self, filename, index):
        with open(f'{filename}.txt', 'wb') as file:
            pickle.dump(index, file)


    def run(self):
        """tf:
                {term: [xtimesInDocID-0, xtimesInDocID-1, xtimesInDocID-2, ...xTimesInDocID-X]}

            postingslist:
                {term: [DocID-0-FilePath, DocI-1-FilePath, DocID-2-FilePath]}

            idf:
                {term: xtimesInAllDocs}
        """
        start = time.time()
        postingslist = defaultdict(list)
        tf = defaultdict(list)
        postingslist, tf = self.traverseDocs(tf, postingslist)
        idf = self.create_idf(postingslist)
        end = time.time()
        print("running time: ", str(end - start))
        self.writeIO('tf', tf)
        self.writeIO('postingslist', postingslist)
        self.writeIO('idf', idf)


indexer = Indexer()
indexer.run()
# Dubaj 2020, COVID-19, (SaS), Hlas-SD