import unittest
from unittest.mock import MagicMock, patch
from jamsite.jamsite import (
    read_songs_spreadsheet,
    sync_to_spreadsheet,
    resolve_artist_sort,
    _looks_like_collab,
    JAM_SONGS_SPREADSHEET_ID,
)
from jamsite.artists import Artist
from jamsite.musicbrainz import ArtistResult


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


    def test_append_with_artist_sort_from_artists_tab(self):
        service = MagicMock()
        service.spreadsheets().values().append().execute.return_value = {}
        service.spreadsheets().values().batchUpdate().execute.return_value = {}

        from jamsite.song import Song
        new_song = Song(
            "u-new", "Beatles", None, "Help", None, "1965",
            "http://dl", "http://vl", "2020-01-01", False, False,
        )
        artists_by_name = {
            "beatles": Artist(
                name="Beatles", mb_id="abc", mb_artist="The Beatles", mb_sort="Beatles, The"
            ),
        }
        mb = MagicMock()
        sync_to_spreadsheet(
            service, "skrul", [new_song], {},
            artists_by_name=artists_by_name, mb=mb,
        )

        append_call = service.spreadsheets().values().append
        body = append_call.call_args[1]["body"]
        row = body["values"][0]
        self.assertEqual(row[2], "Beatles, The")  # artist_sort populated
        mb.search_artist.assert_not_called()

    def test_append_without_artists_params_uses_none(self):
        service = MagicMock()
        service.spreadsheets().values().append().execute.return_value = {}
        service.spreadsheets().values().batchUpdate().execute.return_value = {}

        from jamsite.song import Song
        new_song = Song(
            "u-new", "Artist", None, "Title", None, "2020",
            "http://dl", "http://vl", "2020-01-01", False, False,
        )
        # No artists_by_name or mb params — backward compatible
        sync_to_spreadsheet(service, "skrul", [new_song], {})

        append_call = service.spreadsheets().values().append
        body = append_call.call_args[1]["body"]
        row = body["values"][0]
        self.assertIsNone(row[2])  # artist_sort is None

    def test_empty_artist_skips_lookup(self):
        service = MagicMock()
        service.spreadsheets().values().append().execute.return_value = {}
        service.spreadsheets().values().batchUpdate().execute.return_value = {}

        from jamsite.song import Song
        new_song = Song(
            "u-new", "", None, "Some Title", None, None,
            None, "http://vl", "2020-01-01", False, False,
        )
        artists_by_name = {}
        mb = MagicMock()
        sync_to_spreadsheet(
            service, "skrul", [new_song], {},
            artists_by_name=artists_by_name, mb=mb,
        )
        mb.search_artist.assert_not_called()


class TestLooksLikeCollab(unittest.TestCase):
    def test_ampersand_collab(self):
        self.assertTrue(_looks_like_collab("Kenny Rogers & Dolly Parton", "Kenny Rogers"))

    def test_and_collab(self):
        self.assertTrue(_looks_like_collab("Simon and Garfunkel", "Simon"))

    def test_not_collab_same_length(self):
        self.assertFalse(_looks_like_collab("Death Cab For Cutie", "Death Cab for Cutie"))

    def test_no_collab_marker(self):
        self.assertFalse(_looks_like_collab("Alanis Morissette", "Alanis"))


class TestResolveArtistSort(unittest.TestCase):
    def test_known_artist_returns_sort(self):
        from jamsite.song import Song
        song = Song("u1", "Beatles", None, "Help", None, "1965",
                     "dl", "vl", "mt", False, False)
        artists = {
            "beatles": Artist("Beatles", "abc", "The Beatles", "Beatles, The"),
        }
        mb = MagicMock()
        result = resolve_artist_sort(song, artists, mb, None)
        self.assertEqual(result, "Beatles, The")
        mb.search_artist.assert_not_called()

    def test_empty_artist_returns_none(self):
        from jamsite.song import Song
        song = Song("u1", "", None, "Title", None, None,
                     None, "vl", "mt", False, False)
        mb = MagicMock()
        result = resolve_artist_sort(song, {}, mb, None)
        self.assertIsNone(result)
        mb.search_artist.assert_not_called()

    @patch("builtins.input", side_effect=["", ""])
    @patch("builtins.print")
    def test_unknown_artist_accept_mb(self, mock_print, mock_input):
        from jamsite.song import Song
        song = Song("u1", "Alanis Morissette", None, "Ironic", None, "1995",
                     "dl", "vl", "mt", False, False)
        mb = MagicMock()
        mb.search_artist.return_value = [
            ArtistResult("abc-123", "Alanis Morissette", "Morissette, Alanis",
                         100, "", "Person", "CA"),
        ]
        artists = {}
        sheets_service = MagicMock()
        sheets_service.spreadsheets().values().append().execute.return_value = {}
        result = resolve_artist_sort(song, artists, mb, sheets_service)
        self.assertEqual(result, "Morissette, Alanis")
        # Artist was added to in-memory dict
        self.assertIn("alanis morissette", artists)

    @patch("builtins.input", side_effect=["s"])
    @patch("builtins.print")
    def test_unknown_artist_skip(self, mock_print, mock_input):
        from jamsite.song import Song
        song = Song("u1", "Unknown", None, "Title", None, "2020",
                     "dl", "vl", "mt", False, False)
        mb = MagicMock()
        mb.search_artist.return_value = [
            ArtistResult("abc", "Unknown", "Unknown", 80, "", "", ""),
        ]
        result = resolve_artist_sort(song, {}, mb, None)
        self.assertIsNone(result)

    @patch("builtins.input", side_effect=["n", "Custom, Sort"])
    @patch("builtins.print")
    def test_unknown_artist_reject_manual(self, mock_print, mock_input):
        from jamsite.song import Song
        song = Song("u1", "Weird Artist", None, "Title", None, "2020",
                     "dl", "vl", "mt", False, False)
        mb = MagicMock()
        mb.search_artist.return_value = [
            ArtistResult("abc", "Wrong Match", "Match, Wrong", 60, "", "", ""),
        ]
        result = resolve_artist_sort(song, {}, mb, None)
        self.assertEqual(result, "Custom, Sort")

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_no_mb_results_skip(self, mock_print, mock_input):
        from jamsite.song import Song
        song = Song("u1", "Nobody", None, "Title", None, "2020",
                     "dl", "vl", "mt", False, False)
        mb = MagicMock()
        mb.search_artist.return_value = []
        result = resolve_artist_sort(song, {}, mb, None)
        self.assertIsNone(result)

    @patch("builtins.input", side_effect=["", "k"])
    @patch("builtins.print")
    def test_collab_keeps_original_name(self, mock_print, mock_input):
        from jamsite.song import Song
        song = Song("u1", "Kenny Rogers & Dolly Parton", None, "Islands", None, "1983",
                     "dl", "vl", "mt", False, False)
        mb = MagicMock()
        mb.search_artist.return_value = [
            ArtistResult("abc", "Kenny Rogers", "Rogers, Kenny",
                         100, "", "Person", "US"),
        ]
        artists = {}
        result = resolve_artist_sort(song, artists, mb, None)
        self.assertEqual(result, "Rogers, Kenny")
        # Display name should be the original (collab) name
        self.assertIn("kenny rogers & dolly parton", artists)
        self.assertEqual(artists["kenny rogers & dolly parton"].name, "Kenny Rogers & Dolly Parton")


if __name__ == "__main__":
    unittest.main()
