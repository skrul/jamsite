import unittest
from jamsite.search_indexer import SearchIndexer
from jamsite.song import Song


class TestSearchIndexerKeyExcluded(unittest.TestCase):
    def test_key_not_in_search_tokens(self):
        si = SearchIndexer()
        song = Song(
            "u1", "Beatles", "beatles", "Help", "help", "1965",
            "http://dl", "http://vl", "2020-01-01", False, False,
            key="Am",
        )
        tokens = si._tokenize(song)
        self.assertNotIn("am", tokens)
        self.assertNotIn("Am", tokens)
        self.assertIn("beatles", tokens)
        self.assertIn("help", tokens)


if __name__ == "__main__":
    unittest.main()
