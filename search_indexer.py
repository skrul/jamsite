from trie import Trie
import nltk
import unidecode
import re
import string

class SearchIndexer:
    def __init__(self):
        self.t = Trie()
        self.uuids = []

    def add_song(self, song):
        tokens = self._tokenize(song)
        self.uuids.append(song.uuid)
        self.t.add_doc(len(self.uuids) - 1, tokens)

    def index_as_dict(self):
        return self.t.to_dict()

    def _tokenize(self, song):
        s = ' '.join([song.artist, song.title])
        tokens = []
        for t in nltk.tokenize.word_tokenize(s):
            t = unidecode.unidecode(t)
            t = t.lower()
            t = t.strip(string.punctuation)
            if len(t) > 0:
                tokens.append(t)
        tokens.append(song.year)
        return tokens
