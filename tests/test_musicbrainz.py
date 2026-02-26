import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from jamsite.musicbrainz import MusicBrainzArtistLookup, CUSTOM_ARTISTS


class TestCustomArtists(unittest.TestCase):
    def test_gary_schoofs_returns_without_api_call(self):
        mb = MusicBrainzArtistLookup()
        results = mb.search_artist("Gary Schoofs")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Gary Schoofs")
        self.assertEqual(results[0].sort_name, "Schoofs, Gary")
        self.assertEqual(results[0].mb_id, "00000000-0000-0000-0000-000000000001")
        self.assertEqual(results[0].score, 100)

    def test_custom_artist_case_insensitive(self):
        mb = MusicBrainzArtistLookup()
        results = mb.search_artist("GARY SCHOOFS")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Gary Schoofs")


class TestAPISearch(unittest.TestCase):
    def _mock_response(self, artists):
        response = MagicMock()
        response.json.return_value = {"artists": artists}
        response.raise_for_status = MagicMock()
        return response

    @patch("jamsite.musicbrainz.requests.get")
    def test_search_returns_results(self, mock_get):
        mock_get.return_value = self._mock_response([
            {
                "id": "abc-123",
                "name": "Alanis Morissette",
                "sort-name": "Morissette, Alanis",
                "score": 100,
                "disambiguation": "",
                "type": "Person",
                "country": "CA",
            }
        ])
        mb = MusicBrainzArtistLookup()
        results = mb.search_artist("Alanis Morissette")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].mb_id, "abc-123")
        self.assertEqual(results[0].name, "Alanis Morissette")
        self.assertEqual(results[0].sort_name, "Morissette, Alanis")
        self.assertEqual(results[0].score, 100)
        self.assertEqual(results[0].country, "CA")

    @patch("jamsite.musicbrainz.requests.get")
    def test_search_no_results(self, mock_get):
        mock_get.return_value = self._mock_response([])
        mb = MusicBrainzArtistLookup()
        results = mb.search_artist("xyznonexistent")
        self.assertEqual(results, [])

    @patch("jamsite.musicbrainz.requests.get")
    def test_missing_fields_default(self, mock_get):
        mock_get.return_value = self._mock_response([
            {"id": "abc", "name": "Test", "sort-name": "Test", "score": 80}
        ])
        mb = MusicBrainzArtistLookup()
        results = mb.search_artist("Test")
        self.assertEqual(results[0].disambiguation, "")
        self.assertEqual(results[0].type, "")
        self.assertEqual(results[0].country, "")


class TestCache(unittest.TestCase):
    @patch("jamsite.musicbrainz.requests.get")
    def test_results_cached_to_file(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            "artists": [
                {
                    "id": "abc-123",
                    "name": "Test Artist",
                    "sort-name": "Artist, Test",
                    "score": 100,
                    "disambiguation": "",
                    "type": "Person",
                    "country": "US",
                }
            ]
        }
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name

        try:
            mb = MusicBrainzArtistLookup(cache_path=cache_path)
            mb.search_artist("Test Artist")

            # Verify cache file was written
            with open(cache_path, "r") as f:
                cache = json.load(f)
            self.assertIn("test artist", cache)

            # Second call should not hit API
            mock_get.reset_mock()
            mb2 = MusicBrainzArtistLookup(cache_path=cache_path)
            results = mb2.search_artist("Test Artist")
            mock_get.assert_not_called()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].name, "Test Artist")
        finally:
            os.unlink(cache_path)

    @patch("jamsite.musicbrainz.requests.get")
    def test_cache_key_is_lowercased(self, mock_get):
        response = MagicMock()
        response.json.return_value = {"artists": []}
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name

        try:
            mb = MusicBrainzArtistLookup(cache_path=cache_path)
            mb.search_artist("THE BEATLES")

            # Second call with different case should use cache
            mock_get.reset_mock()
            mb.search_artist("the beatles")
            mock_get.assert_not_called()
        finally:
            os.unlink(cache_path)


class TestRateLimiting(unittest.TestCase):
    @patch("jamsite.musicbrainz.time.sleep")
    @patch("jamsite.musicbrainz.time.time")
    @patch("jamsite.musicbrainz.requests.get")
    def test_rate_limits_between_requests(self, mock_get, mock_time, mock_sleep):
        response = MagicMock()
        response.json.return_value = {"artists": []}
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        # Simulate time: first call at t=100, second call at t=100.5
        mock_time.side_effect = [100.0, 100.0, 100.5, 100.5]

        mb = MusicBrainzArtistLookup()
        mb.search_artist("artist one")
        mb.search_artist("artist two")

        # Should have slept for ~0.6s (1.1 - 0.5)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        self.assertAlmostEqual(sleep_time, 0.6, places=1)


if __name__ == "__main__":
    unittest.main()
