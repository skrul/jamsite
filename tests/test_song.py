import unittest
from jamsite.song import Song


class TestSongInit(unittest.TestCase):
    def test_with_key(self):
        song = Song(
            "uuid1", "Artist", "artist", "Title", "title", "2020",
            "dl", "vl", "2020-01-01", False, False, key="C",
        )
        self.assertEqual(song.key, "C")
        self.assertEqual(song.download_link, "dl")

    def test_without_key(self):
        song = Song(
            "uuid1", "Artist", "artist", "Title", "title", "2020",
            "dl", "vl", "2020-01-01", False, False,
        )
        self.assertEqual(song.key, "")
        self.assertEqual(song.download_link, "dl")

    def test_repr_includes_key(self):
        song = Song(
            "uuid1", "Artist", "artist", "Title", "title", "2020",
            "dl", "vl", "2020-01-01", False, False, key="Am",
        )
        self.assertIn("key: Am", repr(song))


class TestFromSpreadsheetRow(unittest.TestCase):
    def _make_row(self, key="C"):
        return [
            "uuid1",          # A - uuid
            "Artist",         # B - artist
            "artist",         # C - artist_sort
            "Title",          # D - title
            "title",          # E - title_sort
            "2020",           # F - year
            key,              # G - key
            "http://dl",      # H - download_link
            "http://vl",      # I - view_link
            "2020-01-01",     # J - modified_time
            "",               # K - deleted
            "",               # L - skip
        ]

    def test_full_row_with_key(self):
        song = Song.from_spreadsheet_row(self._make_row("C"))
        self.assertEqual(song.uuid, "uuid1")
        self.assertEqual(song.artist, "Artist")
        self.assertEqual(song.title, "Title")
        self.assertEqual(song.year, "2020")
        self.assertEqual(song.key, "C")
        self.assertEqual(song.download_link, "http://dl")
        self.assertEqual(song.view_link, "http://vl")
        self.assertFalse(song.deleted)
        self.assertFalse(song.skip)

    def test_empty_key(self):
        song = Song.from_spreadsheet_row(self._make_row(""))
        self.assertEqual(song.key, "")

    def test_short_row_missing_key(self):
        # Rows shorter than expected — defaultdict fills missing indices with ""
        row = ["uuid1", "Artist", "artist", "Title", "title", "2020"]
        song = Song.from_spreadsheet_row(row)
        self.assertEqual(song.key, "")
        self.assertEqual(song.download_link, "")

    def test_deleted_and_skip_flags(self):
        row = self._make_row()
        row[10] = "x"  # deleted
        row[11] = "x"  # skip
        song = Song.from_spreadsheet_row(row)
        self.assertTrue(song.deleted)
        self.assertTrue(song.skip)


class TestSpreadsheetColumns(unittest.TestCase):
    def test_key_column_is_g(self):
        self.assertEqual(Song.SPREADSHEET_COLUMNS["key"], "G")

    def test_shifted_columns(self):
        self.assertEqual(Song.SPREADSHEET_COLUMNS["download_link"], "H")
        self.assertEqual(Song.SPREADSHEET_COLUMNS["view_link"], "I")
        self.assertEqual(Song.SPREADSHEET_COLUMNS["modified_time"], "J")
        self.assertEqual(Song.SPREADSHEET_COLUMNS["deleted"], "K")
        self.assertEqual(Song.SPREADSHEET_COLUMNS["skip"], "L")


if __name__ == "__main__":
    unittest.main()
