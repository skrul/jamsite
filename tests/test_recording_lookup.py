import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from jamsite.recording_lookup import RecordingLookup


class TestGetYear(unittest.TestCase):
    def _mock_response(self, recordings):
        response = MagicMock()
        response.json.return_value = {"recordings": recordings}
        response.raise_for_status = MagicMock()
        return response

    @patch("jamsite.recording_lookup.requests.get")
    def test_returns_earliest_year(self, mock_get):
        mock_get.return_value = self._mock_response([
            {
                "releases": [
                    {"date": "1970-01-01"},
                    {"date": "1965-06-15"},
                ]
            }
        ])
        rl = RecordingLookup()
        year = rl.get_year("Help", "Beatles")
        self.assertEqual(year, "1965")

    @patch("jamsite.recording_lookup.requests.get")
    def test_returns_none_when_no_results(self, mock_get):
        mock_get.return_value = self._mock_response([])
        rl = RecordingLookup()
        year = rl.get_year("Nonexistent Song", "Nobody")
        self.assertIsNone(year)

    @patch("jamsite.recording_lookup.requests.get")
    def test_returns_none_when_no_dates(self, mock_get):
        mock_get.return_value = self._mock_response([
            {"releases": [{"date": ""}, {}]}
        ])
        rl = RecordingLookup()
        year = rl.get_year("Song", "Artist")
        self.assertIsNone(year)

    @patch("jamsite.recording_lookup.requests.get")
    def test_progressive_search_tries_title_only(self, mock_get):
        """If exact match returns nothing, tries title-only query."""
        no_results = self._mock_response([])
        with_results = self._mock_response([
            {"releases": [{"date": "1999"}]}
        ])
        mock_get.side_effect = [no_results, with_results]
        rl = RecordingLookup()
        year = rl.get_year("Blackbird", "Beatles")
        self.assertEqual(year, "1999")
        self.assertEqual(mock_get.call_count, 2)

    @patch("jamsite.recording_lookup.requests.get")
    def test_progressive_search_tries_simplified(self, mock_get):
        """If title has parenthetical, tries simplified query as third attempt."""
        no_results = self._mock_response([])
        with_results = self._mock_response([
            {"releases": [{"date": "2005"}]}
        ])
        mock_get.side_effect = [no_results, no_results, with_results]
        rl = RecordingLookup()
        year = rl.get_year("Song (Live Version)", "Artist")
        self.assertEqual(year, "2005")
        self.assertEqual(mock_get.call_count, 3)

    @patch("jamsite.recording_lookup.requests.get")
    def test_no_simplified_query_when_title_unchanged(self, mock_get):
        """If simplifying doesn't change the title, skip the third query."""
        no_results = self._mock_response([])
        mock_get.return_value = no_results
        rl = RecordingLookup()
        year = rl.get_year("Simple Title", "Artist")
        self.assertIsNone(year)
        # Only exact + title-only, no simplified
        self.assertEqual(mock_get.call_count, 2)


class TestCache(unittest.TestCase):
    @patch("jamsite.recording_lookup.requests.get")
    def test_results_cached_to_file(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            "recordings": [{"releases": [{"date": "1965"}]}]
        }
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name

        try:
            rl = RecordingLookup(cache_path=cache_path)
            year = rl.get_year("Help", "Beatles")
            self.assertEqual(year, "1965")

            # Verify cache file was written
            with open(cache_path, "r") as f:
                cache = json.load(f)
            self.assertIn("help|beatles", cache)
            self.assertEqual(cache["help|beatles"], "1965")

            # Second call should not hit API
            mock_get.reset_mock()
            rl2 = RecordingLookup(cache_path=cache_path)
            year2 = rl2.get_year("Help", "Beatles")
            mock_get.assert_not_called()
            self.assertEqual(year2, "1965")
        finally:
            os.unlink(cache_path)

    @patch("jamsite.recording_lookup.requests.get")
    def test_none_result_cached(self, mock_get):
        """None results are cached so we don't re-query."""
        response = MagicMock()
        response.json.return_value = {"recordings": []}
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name

        try:
            rl = RecordingLookup(cache_path=cache_path)
            year = rl.get_year("Unknown", "Nobody")
            self.assertIsNone(year)

            mock_get.reset_mock()
            rl2 = RecordingLookup(cache_path=cache_path)
            year2 = rl2.get_year("Unknown", "Nobody")
            mock_get.assert_not_called()
            self.assertIsNone(year2)
        finally:
            os.unlink(cache_path)


class TestRateLimiting(unittest.TestCase):
    @patch("jamsite.recording_lookup.time.sleep")
    @patch("jamsite.recording_lookup.time.time")
    @patch("jamsite.recording_lookup.requests.get")
    def test_rate_limits_between_requests(self, mock_get, mock_time, mock_sleep):
        response = MagicMock()
        response.json.return_value = {
            "recordings": [{"releases": [{"date": "2000"}]}]
        }
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        # Simulate time: first call at t=100, second call at t=100.5
        mock_time.side_effect = [100.0, 100.0, 100.5, 100.5]

        rl = RecordingLookup()
        rl.get_year("Song One", "Artist One")
        rl.get_year("Song Two", "Artist Two")

        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        self.assertAlmostEqual(sleep_time, 0.6, places=1)


class TestSimplify(unittest.TestCase):
    def test_strips_parentheticals(self):
        rl = RecordingLookup()
        self.assertEqual(rl._simplify("Song (Live Version)"), "Song")

    def test_strips_capo_references(self):
        rl = RecordingLookup()
        self.assertEqual(rl._simplify("Song capo 3"), "Song")

    def test_no_change_for_simple_title(self):
        rl = RecordingLookup()
        self.assertEqual(rl._simplify("Simple Title"), "Simple Title")


class TestAPIError(unittest.TestCase):
    @patch("jamsite.recording_lookup.requests.get")
    def test_request_exception_returns_none(self, mock_get):
        mock_get.side_effect = Exception("connection error")
        rl = RecordingLookup()
        year = rl.get_year("Song", "Artist")
        self.assertIsNone(year)


if __name__ == "__main__":
    unittest.main()
