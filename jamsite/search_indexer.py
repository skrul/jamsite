from .trie import Trie
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
        # Extract the year and determine the decade
        year = int(song.year) if song.year and song.year.isdigit() else 0
        
        # Group all years from 1800-1899 under "1800"
        if year < 1950:
            decade = "old af"
        else:
            # For 1900 and later, use the standard decade format (e.g., "1900s", "1910s")
            decade = str(year // 10 * 10) + "s"
        
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
