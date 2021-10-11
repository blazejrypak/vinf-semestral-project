from collections import Counter, defaultdict
import jsonlines
import unicodedata
import string
import re
import regex
import os
import time
import pprint

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

    def get_slovak_person_first_names(self, file_path):
        f = open(file_path, 'r', encoding='UTF-8')
        words = [line.rstrip() for line in f]
        f.close()
        return words

    def get_stop_words(self, file_path):
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


    def tokenize_persons(self, text, tokens):
        Lu = "{Lu}"
        for name_ in self.slovak_person_first_names:
            name = self.str2ascii(name_)
            # we can find only names without suffix, (we cant find Andrejom Dankom)
            reg_pat = f"((?:{name})(?: [A-Z][a-z]+)+)"
            names_with_first_name = set(regex.findall(reg_pat, text))
            for n in names_with_first_name:
                reg_last_name_pattern = f"( )\\b(?:{n.split(' ')[-1][:-1]}[a-z]+)"
                text = text.replace(n, "")
                text = re.sub(reg_last_name_pattern, "", text)
                tokens.add(n)
            # for n in names_with_first_name:
            #     reg_last_name_pattern = f"( )\\b(?:{n.split(' ')[-1][:-1]}[a-z]+)"
            #     text = text.replace(n, self.get_entity_placeholder(entity='person', placeholder=f"{n.replace(' ', '-')}"))
            #     text = re.sub(self.add_name2pattern(reg_last_name_pattern, 'person'), self.get_entity_placeholder(entity='person', placeholder=f"{n.replace(' ', '-')}"), text)
            #     found_names.add(n)
        return text, tokens


    def tokenize_sub_persons(self, text):
        found_names = set()
        # to replace person like Andrejom Dankom we need to find all words starting with capital letter
        reg_pat = "([A-Z][a-z]+)(?: )"
        all_possible_last_names = set(regex.findall(reg_pat, text))
        for pln in all_possible_last_names:
            for name in self.slovak_person_first_names:
                possible = regex.findall(f"({name}\\S+ {pln}\\S+)", text)
                if possible:
                    text = re.sub(self.add_name2pattern(f"({name}\\S+ {pln}\\S+)", 'person'), self.get_entity_placeholder(entity='person', placeholder=f"{name}-{pln}"), text)
                    text = re.sub(self.add_name2pattern(f"\b{pln[:-1]}(?: |\.)", 'person'), self.get_entity_placeholder(entity='person', placeholder=f"{name}-{pln}"), text)
        return text

    def get_entities_from_article(self, text):
        return set(regex.findall("\[\[([^\]]+)\]\]", text))

    def tokenize_companies(self, text):
        companies_suffixes = "(?:s.r.o|a.s.|j. a. s.|akc. spol.|spol. s. r. o.|s. r. o.|ver. obch. spol.|v. o. s.|kom. spol.|k. s.|š. p.|Inc|Ltd|Jr|Sr|Co)"
        pattern = f"((?:[A-Z][a-z]+)(?: [A-Z][a-z]+)* {companies_suffixes})"
        return re.sub(self.add_name2pattern(pattern, 'company'), self.get_entity_placeholder('company', 'company'), text)


    def tokenize_acronyms(self, text):
        end_sentence = "\.|\!|\?"
        pattern = "(?P<acronym>[A-Z]{2,})" + f"(?: |{end_sentence})"
        text = re.sub(pattern, f"[[=ACRONYM=\g<acronym>]]", text)
        return text


    def tokenize_websites(self, text):
        websites = "[.](?:sk|com|net|org|io|gov|eu|de|cz)"
        pattern = "([A-Za-z]+(?:" + websites + ")+)"
        return re.sub(self.add_name2pattern(pattern, 'website'), self.get_entity_placeholder('website', 'website'), text)


    def clean_date_formats(self, text):
        p1 = "((?:\d\d\.) (?:\d\d\.) (?:\d\d\d\d))"
        p2 = "([0-9]{1,2}\. (jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec).*([0-9]{4}))"
        p2 = "([0-9]{1,2}\. (jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)[a-z]+)"
        text = re.sub(p1, "", text)
        text = re.sub(p2, "", text)
        return text

    def clean_all(self, text):
        p1 = "[0-9]+\. [a-z]+"
        p2 = "(Bc.|Mgr|Mgr. art|Ing|Ing. arch|MUDr|MDDr|MVDr|PhD|ArtD|ThLic|ThDr|RNDr|PharmDr|PhDr|JUDr|PaedDr|ThDr|Dr.h.c|DrSc|doc|prof)[.]"
        text = re.sub(p1, "", text)
        text = re.sub(p2, "", text)
        return text

    def remove_stop_words(self, text):
        for sw in self.stop_words:
            text = re.sub(f"(?i)\\b{sw} ", "", text)
        return text

    def split2sentences(self, text):
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

    def tokenize_doc(self, doc, tf):
        tokens = set()
        article_content = doc['body']
        text = self.prepare_text(article_content)
        text, tokens = self.tokenize_persons(text, tokens)
        print(text)
        # text = self.tokenize_sub_persons(text)
        # text = self.tokenize_companies(text)
        # text = self.tokenize_acronyms(text)
        # text = self.tokenize_websites(text)
        # text = self.clean_date_formats(text)
        # text = self.clean_all(text)
        # text = self.remove_stop_words(text)
        # sentences = self.split2sentences(text)
        # pprint.pprint(sentences)
        # tokens = set()
        # for s in sentences:
        #     s_tokens = (self.get_entities_from_article(s))
        #     tokens.update(s_tokens)
        #     for st in s_tokens:
        #         s = s.replace(st, ' ')
        #     for w in s.replace(',', '').split(' '):
        #         tokens.add(w)
        # pprint.pprint(tokens)

        token_freq = dict(Counter(tokens))
        tf = self.add2tf(token_freq, tf)
        return tokens, tf

    def prepare_for_idf(self, doc_tokens, token_to_article_doc):
        for token in doc_tokens:
            token_to_article_doc[token] = [self.articles_reader.getCurrentFileName()]
        return token_to_article_doc

    def traverseArticlePaths(self, token_to_article_doc, tf):
        self.articles_reader = ArticlesReader('/Users/blazejrypak/Projects/vinf-project/data/03-10-2021-21-13-43-article.json')
        doc_tokens, tf = self.tokenize_doc(self.articles_reader.next(), tf)
        token_to_article_doc = self.prepare_for_idf(doc_tokens, token_to_article_doc)
        return token_to_article_doc, tf

    def create_idf(self, token_to_article_doc):
        idf = defaultdict(int)
        for term in token_to_article_doc.keys():
            idf[term] = len(token_to_article_doc[term])
        return idf

    def run(self):
        token_to_article_doc = defaultdict(list)
        tf = defaultdict(list)
        start = time.time()
        token_to_article_doc, tf = self.traverseArticlePaths(token_to_article_doc, tf)
        idf = self.create_idf(token_to_article_doc)
        pprint.pprint(tf)
        print('\n\n\n')
        pprint.pprint(idf)
        end = time.time()
        print("running time: ", str(end - start))

indexer = Indexer()
indexer.run()
