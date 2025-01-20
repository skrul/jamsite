from trie import Trie
from nltk.tokenize import WhitespaceTokenizer
import unidecode
import re
import string


class SearchIndexer:
    def __init__(self):
        self.t = Trie()
        self.uuids = []
        self.decades = {}

    def add_song(self, song):
        tokens = self._tokenize(song)
        decade = song.year[:-1] + "0s"
        self.uuids.append(song.uuid)
        self.t.add_doc(len(self.uuids) - 1, tokens)
        if decade not in self.decades.keys():
            self.decades[decade] = []
        self.decades[decade].append(len(self.uuids) - 1)

    def index_as_dict(self):
        return self.t.to_dict()

    def decades(self):
        return self.decades

    def _tokenize(self, song):
        s = " ".join([song.artist, song.title])
        tokens = []
        for t in WhitespaceTokenizer().tokenize(s):
            t = unidecode.unidecode(t)
            t = t.lower()
            if len(t) > 0:
                tokens.append(t)
        tokens.append(song.year)
        return tokens
