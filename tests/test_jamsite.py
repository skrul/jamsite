import unittest
from unittest.mock import MagicMock
from jamsite.jamsite import read_songs_spreadsheet, sync_to_spreadsheet, JAM_SONGS_SPREADSHEET_ID


class TestReadSongsSpreadsheet(unittest.TestCase):
    def _mock_service(self, rows):
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {
            "values": rows
        }
        return service

    def test_parses_row_with_key(self):
        rows = [
            ["uuid", "artist", "artist_sort", "title", "title_sort", "year",
             "key", "download_link", "view_link", "modified_time", "deleted", "skip"],
            ["u1", "Beatles", "beatles", "Help", "help", "1965",
             "A", "http://dl", "http://vl", "2020-01-01", "", ""],
        ]
        service = self._mock_service(rows)
        songs_by_row = read_songs_spreadsheet(service, "skrul")
        song = songs_by_row[1]
        self.assertEqual(song.uuid, "u1")
        self.assertEqual(song.artist, "Beatles")
        self.assertEqual(song.title, "Help")
        self.assertEqual(song.key, "A")
        self.assertEqual(song.download_link, "http://dl")
        self.assertFalse(song.deleted)

    def test_parses_row_without_key(self):
        rows = [
            ["header"],
            ["u1", "Beatles", "beatles", "Help", "help", "1965",
             "", "http://dl", "http://vl", "2020-01-01", "", ""],
        ]
        service = self._mock_service(rows)
        songs_by_row = read_songs_spreadsheet(service, "skrul")
        song = songs_by_row[1]
        self.assertEqual(song.key, "")

    def test_deleted_song(self):
        rows = [
            ["header"],
            ["u1", "Beatles", "beatles", "Help", "help", "1965",
             "", "http://dl", "http://vl", "2020-01-01", "x", ""],
        ]
        service = self._mock_service(rows)
        songs_by_row = read_songs_spreadsheet(service, "skrul")
        self.assertTrue(songs_by_row[1].deleted)


class TestSyncToSpreadsheet(unittest.TestCase):
    def test_append_values_include_key_slot(self):
        service = MagicMock()
        # Make append and batchUpdate return something
        service.spreadsheets().values().append().execute.return_value = {}
        service.spreadsheets().values().batchUpdate().execute.return_value = {}

        # A new song not in existing
        from jamsite.song import Song
        new_song = Song(
            "u-new", "Artist", None, "Title", None, "2020",
            "http://dl", "http://vl", "2020-01-01", False, False,
        )
        sync_to_spreadsheet(service, "skrul", [new_song], {})

        # Grab the body passed to append
        append_call = service.spreadsheets().values().append
        call_kwargs = append_call.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        row = body["values"][0]

        # Row layout: uuid, artist, None, title, None, year, key(""), dl, vl, mtime, deleted("")
        self.assertEqual(row[0], "u-new")    # uuid
        self.assertEqual(row[6], "")          # key slot (empty for new songs)
        self.assertEqual(row[7], "http://dl") # download_link
        self.assertEqual(row[8], "http://vl") # view_link
        self.assertEqual(len(row), 11)


if __name__ == "__main__":
    unittest.main()
