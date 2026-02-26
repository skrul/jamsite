import unittest
from unittest.mock import MagicMock

from jamsite.artists import read_artists, append_artist, Artist, ARTISTS_SHEET


class TestReadArtists(unittest.TestCase):
    def _mock_service(self, rows):
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {
            "values": rows
        }
        return service

    def test_reads_artists_from_sheet(self):
        rows = [
            ["name", "mb_id", "mb_artist", "mb_sort"],
            ["Beatles", "abc-123", "The Beatles", "Beatles, The"],
            ["Alanis Morissette", "def-456", "Alanis Morissette", "Morissette, Alanis"],
        ]
        service = self._mock_service(rows)
        artists = read_artists(service, "spreadsheet-id")
        self.assertEqual(len(artists), 2)
        self.assertIn("beatles", artists)
        self.assertIn("alanis morissette", artists)
        self.assertEqual(artists["beatles"].name, "Beatles")
        self.assertEqual(artists["beatles"].mb_id, "abc-123")
        self.assertEqual(artists["beatles"].mb_sort, "Beatles, The")

    def test_keys_are_lowercased(self):
        rows = [
            ["name", "mb_id", "mb_artist", "mb_sort"],
            ["Death Cab For Cutie", "x", "Death Cab for Cutie", "Death Cab for Cutie"],
        ]
        service = self._mock_service(rows)
        artists = read_artists(service, "spreadsheet-id")
        self.assertIn("death cab for cutie", artists)

    def test_skips_header_row(self):
        rows = [
            ["name", "mb_id", "mb_artist", "mb_sort"],
        ]
        service = self._mock_service(rows)
        artists = read_artists(service, "spreadsheet-id")
        self.assertEqual(len(artists), 0)

    def test_handles_short_rows(self):
        rows = [
            ["name", "mb_id", "mb_artist", "mb_sort"],
            ["Some Artist"],
        ]
        service = self._mock_service(rows)
        artists = read_artists(service, "spreadsheet-id")
        self.assertEqual(artists["some artist"].mb_id, "")
        self.assertEqual(artists["some artist"].mb_sort, "")

    def test_skips_empty_name(self):
        rows = [
            ["name", "mb_id", "mb_artist", "mb_sort"],
            ["", "abc", "Artist", "Sort"],
        ]
        service = self._mock_service(rows)
        artists = read_artists(service, "spreadsheet-id")
        self.assertEqual(len(artists), 0)

    def test_empty_sheet(self):
        service = MagicMock()
        service.spreadsheets().values().get().execute.return_value = {}
        artists = read_artists(service, "spreadsheet-id")
        self.assertEqual(len(artists), 0)


class TestAppendArtist(unittest.TestCase):
    def test_appends_row_to_sheet(self):
        service = MagicMock()
        service.spreadsheets().values().append().execute.return_value = {}

        artist = Artist(
            name="New Artist",
            mb_id="new-id",
            mb_artist="New Artist",
            mb_sort="Artist, New",
        )
        append_artist(service, "spreadsheet-id", artist)

        append_call = service.spreadsheets().values().append
        call_kwargs = append_call.call_args[1]
        self.assertEqual(call_kwargs["spreadsheetId"], "spreadsheet-id")
        self.assertEqual(call_kwargs["range"], f"{ARTISTS_SHEET}!A1")
        self.assertEqual(
            call_kwargs["body"]["values"],
            [["New Artist", "new-id", "New Artist", "Artist, New"]],
        )


if __name__ == "__main__":
    unittest.main()
