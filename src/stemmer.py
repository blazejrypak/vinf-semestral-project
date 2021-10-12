

from collections import defaultdict
from posixpath import dirname
from typing import DefaultDict, Dict
import os
import gzip
import unicodedata
from pprint import pprint

class SlovakStemmer:
    def __init__(self):
        self.morf_dict = ''
        self.lookup_table = defaultdict(str)
        self.lookup_table_path = 'stemmer_data'
        self.morf_dict_path = './morf_dict.txt.gz'
        self.MAX_DEPTH = 3
        self.init_lookup_table()

    def stem(self, word):
        file_path = self.lookup_table.get(word[:self.MAX_DEPTH], None)
        if not file_path: return word
        with open(file_path, 'r') as f:
            for line in f.readlines():
                words = line.split()
                if words[0] != word and words[1] == word:
                    return words[0]
        return word

    def str2ascii(self, string):
        string = unicodedata.normalize('NFD', string)
        string = string.encode('ascii', 'ignore')
        string = string.decode("utf-8")
        return string

    def init_lookup_table(self):
        for root, dirs, files in os.walk(self.lookup_table_path):
            for file in files:
                self.lookup_table[file.split('.')[0]] = os.path.join(root, file)

    def save_lines(self, dir_name='', filename='', lines=set()):
        try:
            os.makedirs(os.path.join('.', self.lookup_table_path, dir_name))
        except FileExistsError:
            pass
        with open(os.path.join('.', self.lookup_table_path, dir_name, f"{filename}.txt"), 'w') as file:
            file.writelines(lines)

    def save_dict(self, dir_name, depth_dict={}):
        for key in depth_dict.keys():
            self.save_lines(dir_name=dir_name, filename=key, lines=depth_dict[key])

    def create_stemmer_file_lookup_table(self):
        with gzip.open(self.morf_dict_path, 'rt') as file:
            depth_zero_char_dict = defaultdict(set)
            depth_zero_char = 'a'
            for line in file:
                line = self.str2ascii(line)
                words = line.lower().split('\t')
                if len(words) < 2: continue
                stemmed_word =  words[0].replace('*', '')
                to_stem = words[1]
                if stemmed_word[0] != depth_zero_char:
                    self.save_dict(depth_zero_char, depth_zero_char_dict)
                    depth_zero_char_dict.clear()
                    depth_zero_char = stemmed_word[0]
                depth_zero_char_dict[stemmed_word[:self.MAX_DEPTH]].add(f"{stemmed_word} {to_stem}\n")
                    