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

class ArticlesReader():
    def __init__(self, file_path):
        self.current_file_path = file_path
        self.reader = jsonlines.open(self.current_file_path)
        self.docID = 0

    def getCurrentFileName(self):
        head, tail = os.path.split(self.current_file_path)
        return head.split('.')[0]

    def next(self):
        self.docID += 1
        return self.reader.read(type=dict)

    def getCurrentArticleID(self):
        return self.docID

class Indexer:
    def __init__(self):
        self.articles_fpaths = self.get_article_files_paths('../data')
        self.slovak_person_first_names = self.get_slovak_person_first_names('./names.txt')
        self.stop_words = self.get_stop_words('./stop_words.txt')
        self.articles_reader = None
        self.stemmer = SlovakStemmer()

    def get_slovak_person_first_names(self, file_path):
        f = open(file_path, 'r', encoding='UTF-8')
        words = [line.rstrip() for line in f]
        f.close()
        return words

    def get_stop_words(self, file_path):
        f = open(file_path, 'r', encoding='UTF-8')
        words = [self.str2ascii(line).rstrip() for line in f]
        f.close()
        return words    


    def get_article_files_paths(self, dir_path):
        articleFiles = []
        for root, dirs, files in os.walk(dir_path):
            for fname in files:
                if fname.endswith('.json'):
                    current_file_path = os.path.join(root, fname)
                    articleFiles.append(current_file_path)
        return articleFiles


    def str2ascii(self, string):
        string = unicodedata.normalize('NFD', string)
        string = string.encode('ascii', 'ignore')
        string = string.decode("utf-8")
        return string


    def add_name2pattern(self, pattern, name):
        return f"(?P<{name}>" + pattern + ")"


    def get_entity_placeholder(self, entity, pattern_name=None, placeholder=None):
        if placeholder is None:
            placeholder = f"\g<{pattern_name}>"
        entities = {
            'person': f'[[=PERSON={placeholder}]]',
            'website': f'[[=WEBSITE={placeholder}]]',
            'company': f'[[=COMPANY={placeholder}]]',
            'default': f'[[=DEFAULT={placeholder}]]',
        }
        return entities.get(entity, entities['default'])

    def clean_text(self, text):
        return text.replace('\n', ' ').replace('  ', ' ')

    def prepare_text(self, text):
        text = self.clean_text(text)
        return self.str2ascii(text)    


    def tokenize_persons(self, text, token_freq_per_doc):
        for name_ in self.slovak_person_first_names:
            name = self.str2ascii(name_)
            # we can find only names without suffix, (we cant find Andrejom Dankom)
            reg_pat = f"((?:{name})(?: [A-Z][a-z]+)+)"
            names_with_first_name = set(regex.findall(reg_pat, text))
            for n in names_with_first_name:
                reg_last_name_pattern = f"( )\\b(?:{n.split(' ')[-1][:-1]}[a-z]+)"
                text = text.replace(n, "")
                found = regex.findall(reg_last_name_pattern, text)
                text = re.sub(reg_last_name_pattern, "", text)
                if n not in token_freq_per_doc:
                    token_freq_per_doc[n] = 1 + len(found)
                else:
                    token_freq_per_doc[n] += len(found)
        return text, token_freq_per_doc


    def tokenize_sub_persons(self, text, token_freq_per_doc):
        # to replace person like Andrejom Dankom we need to find all words starting with capital letter
        reg_pat = "([A-Z][a-z]+)(?: )"
        all_possible_last_names = set(regex.findall(reg_pat, text))
        for pln in all_possible_last_names:
            for name in self.slovak_person_first_names:
                possible = regex.findall(f"({name}\\S+ {pln}\\S+)", text)
                if possible:
                    text = re.sub(self.add_name2pattern(f"({name}\\S+ {pln}\\S+)", 'person'), "", text)
                    found = regex.findall(f"\b{pln[:-1]}(?: |\.)", text)
                    text = re.sub(self.add_name2pattern(f"\b{pln[:-1]}(?: |\.)", 'person'), "", text)
                    entity = f"{name} {pln}"
                    if entity not in token_freq_per_doc:
                        token_freq_per_doc[entity] = 1 + len(possible) + len(found)
                    else:
                        token_freq_per_doc[entity] += len(possible) + len(found)
        return text, token_freq_per_doc

    def get_entities_from_article(self, text):
        return set(regex.findall("\[\[([^\]]+)\]\]", text))

    def tokenize_companies(self, text, token_freq_per_doc):
        companies_suffixes = "(?:s.r.o|a.s.|j. a. s.|akc. spol.|spol. s. r. o.|s. r. o.|ver. obch. spol.|v. o. s.|kom. spol.|k. s.|š. p.|Inc|Ltd|Jr|Sr|Co)"
        pattern = f"((?:[A-Z][a-z]+)(?: [A-Z][a-z]+)* {companies_suffixes})"
        found_companies = regex.findall(pattern, text)
        for f in found_companies:
            token_freq_per_doc[f] = text.count(f)
        return re.sub(self.add_name2pattern(pattern, 'company'), "", text), token_freq_per_doc


    def tokenize_acronyms(self, text, token_freq_per_doc):
        end_sentence = "\.|\!|\?"
        pattern = "(?P<acronym>[A-Z]{2,})" + f"(?: |{end_sentence})"
        found = regex.findall(pattern, text)
        for f in found:
            token_freq_per_doc[f] = text.count(f)
        return re.sub(pattern, "", text), token_freq_per_doc


    def tokenize_websites(self, text, token_freq_per_doc):
        websites = "[.](?:sk|com|net|org|io|gov|eu|de|cz)"
        pattern = "([A-Za-z]+(?:" + websites + ")+)"
        found = regex.findall(pattern, text)
        for f in found:
            token_freq_per_doc[f] = text.count(f)
        return re.sub(self.add_name2pattern(pattern, 'website'), "", text), token_freq_per_doc


    def clean_date_formats(self, text):
        p1 = "((?:\d\d\.) (?:\d\d\.) (?:\d\d\d\d))"
        p2 = "([0-9]{1,2}\. (jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec).*([0-9]{4}))"
        p3 = "([0-9]{1,2}\. (jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)[a-z]+)"
        p4 = " \d\d\d\d "
        text = re.sub(p1, "", text)
        text = re.sub(p2, "", text)
        text = re.sub(p3, "", text)
        text = re.sub(p4, "", text)
        return text

    def clean_all(self, text):
        p1 = "[0-9]+\. [a-z]+"
        p2 = "(Bc.|Mgr|Mgr. art|Ing|Ing. arch|MUDr|MDDr|MVDr|PhD|ArtD|ThLic|ThDr|RNDr|PharmDr|PhDr|JUDr|PaedDr|ThDr|Dr.h.c|DrSc|doc|prof)[.]"
        p3 = "\(.*\)"
        text = re.sub(p1, "", text)
        text = re.sub(p2, "", text)
        text = re.sub(p3, "", text)
        return text

    def remove_stop_words(self, text):
        for sw in self.stop_words:
            text = re.sub(f"(?i)\\b{sw}\\b", "", text)
        return text

    def split2sentences(self, text):
        text = text.replace('.', ' ')
        text = re.sub('(\.(?: )?)([A-Z])', "<endline>\g<2>", text)
        return text.split('<endline>')

    def add2tf(self, token_freq, tf):
        new_token = True
        for token in token_freq.keys():
            for term in tf.keys():
                if token == term:
                    new_token = False
                    tf[term].append(token_freq[token])
            if new_token:
                tf[token] = [token_freq[token]]
        for term in tf.keys():
            if len(tf[term]) != self.articles_reader.getCurrentArticleID():
                tf[term].append(0)
        return tf

    def tokenize_doc(self, doc):
        token_freq_per_doc = defaultdict(int)
        article_content = doc['body']
        text = self.prepare_text(article_content)
        print(text, '\n\n\n')
        text, token_freq_per_doc = self.tokenize_persons(text, token_freq_per_doc)
        text, token_freq_per_doc = self.tokenize_sub_persons(text, token_freq_per_doc)
        text, token_freq_per_doc = self.tokenize_companies(text, token_freq_per_doc)
        text, token_freq_per_doc = self.tokenize_acronyms(text, token_freq_per_doc)
        text, token_freq_per_doc = self.tokenize_websites(text, token_freq_per_doc)
        text = self.clean_date_formats(text)
        text = self.clean_all(text)
        print(text, '\n\n\n')
        sentences = self.split2sentences(text)
        for s in sentences:
            for w in s.split(' '):
                if w not in self.stop_words:
                    if w not in token_freq_per_doc:
                        token_freq_per_doc[w] = 1 + text.count(w)
                    else:
                        token_freq_per_doc[w] += text.count(w)
        
        for sw in self.stop_words:
            token_freq_per_doc.pop(sw, None)

        for tok in list(token_freq_per_doc):
            new_tok = self.stemmer.stem(tok)
            if new_tok != tok:
                token_freq_per_doc[new_tok] += token_freq_per_doc.pop(tok)

        pprint.pprint(token_freq_per_doc)

        return token_freq_per_doc

    def traverseArticlePaths(self):
        self.articles_reader = ArticlesReader('/Users/blazejrypak/Projects/vinf-project/data/03-10-2021-21-13-43-article.json')
        token_freq_per_doc = self.tokenize_doc(self.articles_reader.next())
        return token_freq_per_doc

    def add2idf(self, tf, idf):
        for token in tf.keys():
            if token in idf:
                idf[token] += 1
            else:
                idf[token] = 1
        return idf

    def run(self):
        idf = defaultdict(int)
        start = time.time()
        token_freq_per_doc = self.traverseArticlePaths()
        idf = self.add2idf(token_freq_per_doc, idf)
        pprint.pprint(token_freq_per_doc)
        pprint.pprint(idf)
        end = time.time()
        print("running time: ", str(end - start))

indexer = Indexer()
indexer.run()

# Dubaj 2020, COVID-19, (SaS), Hlas-SD