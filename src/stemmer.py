

from collections import defaultdict
from typing import DefaultDict
import os
import gzip
import unicodedata

class SlovakStemmer:
    DEPTH = 0
    def __init__(self):
        self.morf_dict = ''
        self.lookup_table = defaultdict(str)
        self.lookup_table_path = 'stemmer_data'
        self.morf_dict_path = './morf_dict.txt.gz'

    def str2ascii(self, string):
        string = unicodedata.normalize('NFD', string)
        string = string.encode('ascii', 'ignore')
        string = string.decode("utf-8")
        return string

    def init_lookup_table(self):
        for root, dirs, files in os.walk(self.lookup_table_path):
            for file in files:
                print(os.path.join(root, file))

    def save_lines(self, path_dirs=None, filename='', lines=set()):
        with open(os.path.join('.', self.lookup_table_path, f"{filename}.txt"), 'w') as file:
            file.writelines(lines)

    def create_stemmer_file_lookup_table(self):
        with gzip.open(self.morf_dict_path, 'rt') as file:
            lines = set()
            current_char = 'a'
            depth = 0
            for line in file:
                line = self.str2ascii(line)
                words = line.lower().split('\t')
                if len(words) < 2: continue
                stemmed_word =  words[0].replace('*', '')
                to_stem = words[1]
                if stemmed_word[depth] != current_char:
                    self.save_lines(filename=current_char, lines=lines)
                    lines.clear()
                    current_char = stemmed_word[depth]
                    lines.add(f"{stemmed_word} {to_stem}\n")
                else:
                    lines.add(f"{stemmed_word} {to_stem}\n")

slovakStemmer = SlovakStemmer()
slovakStemmer.create_stemmer_file_lookup_table()
                





