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
import pickle

from stemmer import SlovakStemmer



class Tokenizer:
    def __init__(self):
        self.articles_fpaths = self.get_article_files_paths('../data')
        self.slovak_person_first_names = self.get_slovak_person_first_names('./names.txt')
        self.stop_words = self.get_stop_words('./stop_words.txt')
        self.stemmer = SlovakStemmer()

    def get_stop_words(self, file_path):
        f = open(file_path, 'r', encoding='UTF-8')
        words = [self.str2ascii(line).rstrip() for line in f]
        f.close()
        return words   

    def get_slovak_person_first_names(self, file_path):
        f = open(file_path, 'r', encoding='UTF-8')
        words = [line.rstrip() for line in f]
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


    def tokenize_persons(self, text):
        tokens = []
        for name_ in self.slovak_person_first_names:
            name = self.str2ascii(name_)
            reg_pat = f"((?:{name})(?: [A-Z][a-z]+)+)"
            names_with_first_name = regex.findall(reg_pat, text)
            for n in names_with_first_name:
                reg_last_name_pattern = f"(?: )\\b(?:{n.split(' ')[-1][:-1]}[a-z]+)"
                text = text.replace(n, "")
                found = regex.findall(reg_last_name_pattern, text)
                text = re.sub(reg_last_name_pattern, "", text)
                tokens.extend(str(n).lower().split(' '))
                tokens.extend((str(n).lower().split(' '))*len(found))
        return text, tokens


    def tokenize_sub_persons(self, text):
        tokens = []
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
                    tokens.extend([entity]*len(possible))
                    tokens.extend([entity]*len(found))
        return text, tokens

    def get_entities_from_article(self, text):
        return set(regex.findall("\[\[([^\]]+)\]\]", text))

    def tokenize_companies(self, text):
        companies_suffixes = "(?:s.r.o|a.s.|j. a. s.|akc. spol.|spol. s. r. o.|s. r. o.|ver. obch. spol.|v. o. s.|kom. spol.|k. s.|š. p.|Inc|Ltd|Jr|Sr|Co)"
        pattern = f"((?:[A-Z][a-z]+)(?: [A-Z][a-z]+)* {companies_suffixes})"
        found_companies = regex.findall(pattern, text)
        found_companies = [str(x).lower() for x in found_companies]
        return re.sub(self.add_name2pattern(pattern, 'company'), "", text), found_companies


    def tokenize_acronyms(self, text):
        end_sentence = "\.|\!|\?"
        pattern = "(?P<acronym>[A-Z]{2,})" + f"(?: |{end_sentence})"
        found = regex.findall(pattern, text)
        found = [str(x).lower() for x in found]
        return re.sub(pattern, "", text), found


    def tokenize_websites(self, text):
        websites = "[.](?:sk|com|net|org|io|gov|eu|de|cz)"
        pattern = "([A-Za-z]+(?:" + websites + ")+)"
        found = regex.findall(pattern, text)
        found = [str(x).lower() for x in found]
        return re.sub(self.add_name2pattern(pattern, 'website'), "", text), found


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
        text = text.replace(',', ' ')
        return text

    def remove_stop_words(self, text):
        for sw in self.stop_words:
            text = re.sub(f"(?i)\\b{sw}\\b", "", text)
        return text

    def split2sentences(self, text):
        text = text.replace('.', ' ')
        text = re.sub('(\.(?: )?)([A-Z])', "<endline>\g<2>", text)
        return text.split('<endline>')
    
    def clean_tokens(self, tokens):
        tokens_in_doc = []
        for token in tokens:
            if token.strip():
                tokens_in_doc.append(token)
        return tokens_in_doc

    def tokenize_doc(self, document):
        return self.tokenize(document['body'])

    def tokenize_hyphen_words(self, text):
        # COVID-19, hlas-SD ...
        return re.sub('([a-zA-Z0-9]*-[a-zA-Z0-9]*)', "", text), regex.findall('([a-zA-Z0-9]*-[a-zA-Z0-9]*)', text)

    def tokenize(self, text):
        tokens_in_doc = []
        text = self.prepare_text(text)
        text, tokens = self.tokenize_hyphen_words(text)
        text, tokens = self.tokenize_persons(text)
        tokens_in_doc.extend(tokens)
        # text, tokens = self.tokenize_sub_persons(text)
        # tokens_in_doc.extend(tokens)
        text, tokens = self.tokenize_companies(text)
        tokens_in_doc.extend(tokens)
        text, tokens = self.tokenize_acronyms(text)
        tokens_in_doc.extend(tokens)
        text, tokens = self.tokenize_websites(text)
        tokens_in_doc.extend(tokens)
        text = self.clean_date_formats(text)
        text = self.clean_all(text)
        sentences = self.split2sentences(text)
        for s in sentences:
            for w in s.split(' '):
                tokens_in_doc.append(w.lower())

        tokens_in_doc = self.clean_tokens(tokens_in_doc)

        tokens_in_doc = [token for token in tokens_in_doc if token.lower() not in self.stop_words]
        tokens_in_doc = [self.stemmer.stem(token) for token in tokens_in_doc]
        tf_temp = dict(Counter(tokens_in_doc))

        return set(tokens_in_doc), tf_temp