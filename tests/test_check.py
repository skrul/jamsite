import os
import tempfile
import unittest
from unittest.mock import MagicMock

from jamsite.check import run_check, print_report, find_duplicates
from jamsite.song import Song


def make_song(**overrides):
    """Create a Song with sensible defaults, overridable by keyword args."""
    defaults = dict(
        uuid="gd:abc123",
        artist="Beatles",
        artist_sort="Beatles, The",
        title="Help",
        title_sort="Help",
        year="1965",
        download_link="https://example.com/dl",
        view_link="https://example.com/view",
        modified_time="2024-01-01T00:00:00Z",
        deleted=False,
        skip=False,
    )
    defaults.update(overrides)
    return Song(**defaults)


class TestMissingFields(unittest.TestCase):
    def test_missing_title(self):
        song = make_song(title="")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.missing_fields), 1)
        self.assertIn("missing title", result.missing_fields[0])

    def test_missing_year(self):
        song = make_song(year="")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.missing_fields), 1)
        self.assertIn("missing year", result.missing_fields[0])

    def test_missing_artist_skrul(self):
        song = make_song(artist="", artist_sort="")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.missing_fields), 1)
        self.assertIn("missing artist", result.missing_fields[0])

    def test_missing_artist_gary_not_flagged(self):
        song = make_song(uuid="dbx:xyz789", artist="", artist_sort="")
        songs = {("gary", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "dbx:xyz789.pdf")
            result = run_check(songs, {}, d)
        # Should not flag missing artist for gary songs
        for msg in result.missing_fields:
            self.assertNotIn("missing artist", msg)

    def test_missing_artist_sort(self):
        song = make_song(artist_sort="")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.missing_fields), 1)
        self.assertIn("missing artist_sort", result.missing_fields[0])

    def test_deleted_songs_skipped(self):
        song = make_song(title="", deleted=True)
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.missing_fields), 0)

    def test_skipped_songs_skipped(self):
        song = make_song(title="", skip=True)
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.missing_fields), 0)


class TestYearFormat(unittest.TestCase):
    def test_valid_year(self):
        song = make_song(year="1965")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.year_format), 0)

    def test_non_numeric_year(self):
        song = make_song(year="abc")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.year_format), 1)
        self.assertIn("not valid", result.year_format[0])

    def test_year_too_old(self):
        song = make_song(year="1799")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.year_format), 1)
        self.assertIn("out of range", result.year_format[0])

    def test_year_in_future(self):
        song = make_song(year="2099")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.year_format), 1)
        self.assertIn("out of range", result.year_format[0])

    def test_empty_year_not_flagged(self):
        song = make_song(year="")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        # Empty year is a missing field issue, not a year format issue
        self.assertEqual(len(result.year_format), 0)


class TestDuplicates(unittest.TestCase):
    def test_detects_duplicates(self):
        song1 = make_song(uuid="gd:aaa")
        song2 = make_song(uuid="gd:bbb")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:aaa.pdf")
            _touch(d, "gd:bbb.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.duplicates), 1)
        title, artist, entries = result.duplicates[0]
        self.assertEqual(title, "Help")
        self.assertEqual(artist, "Beatles")
        rows = {row for _, row, _ in entries}
        self.assertEqual(rows, {1, 5})

    def test_case_insensitive(self):
        song1 = make_song(uuid="gd:aaa", title="Help")
        song2 = make_song(uuid="gd:bbb", title="help")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:aaa.pdf")
            _touch(d, "gd:bbb.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.duplicates), 1)

    def test_no_false_duplicates(self):
        song1 = make_song(uuid="gd:aaa", title="Help")
        song2 = make_song(uuid="gd:bbb", title="Yesterday")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:aaa.pdf")
            _touch(d, "gd:bbb.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.duplicates), 0)


class TestFindDuplicates(unittest.TestCase):
    def test_returns_structured_tuples(self):
        song1 = make_song(uuid="gd:aaa", title="Help", artist="Beatles")
        song2 = make_song(uuid="gd:bbb", title="Help", artist="Beatles")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        dupes = find_duplicates(songs)
        self.assertEqual(len(dupes), 1)
        title, artist, entries = dupes[0]
        self.assertEqual(title, "Help")
        self.assertEqual(artist, "Beatles")
        self.assertEqual(len(entries), 2)

    def test_skips_deleted_and_skipped(self):
        song1 = make_song(uuid="gd:aaa", title="Help", deleted=True)
        song2 = make_song(uuid="gd:bbb", title="Help")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        dupes = find_duplicates(songs)
        self.assertEqual(len(dupes), 0)

    def test_distinct_keys_not_duplicates(self):
        song1 = make_song(uuid="gd:aaa", key="G")
        song2 = make_song(uuid="gd:bbb", key="C")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        dupes = find_duplicates(songs)
        self.assertEqual(len(dupes), 0)

    def test_same_keys_still_duplicates(self):
        song1 = make_song(uuid="gd:aaa", key="G")
        song2 = make_song(uuid="gd:bbb", key="G")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        dupes = find_duplicates(songs)
        self.assertEqual(len(dupes), 1)

    def test_one_empty_key_still_duplicates(self):
        song1 = make_song(uuid="gd:aaa", key="G")
        song2 = make_song(uuid="gd:bbb", key="")
        songs = {("skrul", 1): song1, ("skrul", 5): song2}
        dupes = find_duplicates(songs)
        self.assertEqual(len(dupes), 1)

    def test_empty_artist_grouped(self):
        song1 = make_song(uuid="dbx:aaa", title="Jam", artist="", artist_sort="")
        song2 = make_song(uuid="dbx:bbb", title="Jam", artist="", artist_sort="")
        songs = {("gary", 1): song1, ("gary", 5): song2}
        dupes = find_duplicates(songs)
        self.assertEqual(len(dupes), 1)


class TestUnknownArtists(unittest.TestCase):
    def test_artist_in_tab(self):
        song = make_song()
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.unknown_artists), 0)

    def test_artist_not_in_tab(self):
        song = make_song(artist="Unknown Band")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.unknown_artists), 1)
        self.assertIn("Unknown Band", result.unknown_artists[0])

    def test_case_insensitive_match(self):
        song = make_song(artist="BEATLES")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.unknown_artists), 0)

    def test_empty_artist_not_flagged(self):
        song = make_song(uuid="dbx:xyz", artist="", artist_sort="")
        songs = {("gary", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "dbx:xyz.pdf")
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.unknown_artists), 0)


class TestFileExistence(unittest.TestCase):
    def test_missing_pdf(self):
        song = make_song()
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.missing_files), 1)
        self.assertIn("PDF not found", result.missing_files[0])

    def test_existing_pdf(self):
        song = make_song()
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.missing_files), 0)


class TestOrphanedFiles(unittest.TestCase):
    def test_orphaned_pdf(self):
        songs = {}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:orphan.pdf")
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.orphaned_files), 1)
        self.assertIn("gd:orphan.pdf", result.orphaned_files[0])

    def test_no_orphans(self):
        song = make_song()
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d)
        self.assertEqual(len(result.orphaned_files), 0)

    def test_deleted_song_pdf_not_orphaned(self):
        song = make_song(deleted=True)
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.orphaned_files), 0)

    def test_skipped_song_pdf_not_orphaned(self):
        song = make_song(skip=True)
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {}, d)
        self.assertEqual(len(result.orphaned_files), 0)


class TestYearAccuracy(unittest.TestCase):
    def test_flags_year_mismatch(self):
        song = make_song(year="1975")
        songs = {("skrul", 1): song}
        mb = MagicMock()
        mb.get_year.return_value = "1965"
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d, recording_lookup=mb)
        self.assertEqual(len(result.year_accuracy), 1)
        self.assertIn("spreadsheet: 1975", result.year_accuracy[0])
        self.assertIn("MusicBrainz: 1965", result.year_accuracy[0])

    def test_no_flag_when_within_tolerance(self):
        song = make_song(year="1966")
        songs = {("skrul", 1): song}
        mb = MagicMock()
        mb.get_year.return_value = "1965"
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d, recording_lookup=mb)
        self.assertEqual(len(result.year_accuracy), 0)

    def test_no_flag_when_mb_returns_none(self):
        song = make_song(year="1965")
        songs = {("skrul", 1): song}
        mb = MagicMock()
        mb.get_year.return_value = None
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d, recording_lookup=mb)
        self.assertEqual(len(result.year_accuracy), 0)

    def test_not_called_without_lookup(self):
        song = make_song(year="1975")
        songs = {("skrul", 1): song}
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "gd:abc123.pdf")
            result = run_check(songs, {"beatles": MagicMock()}, d, recording_lookup=None)
        self.assertEqual(len(result.year_accuracy), 0)

    def test_skipped_when_missing_artist(self):
        song = make_song(uuid="dbx:xyz", artist="", artist_sort="", year="1975")
        songs = {("gary", 1): song}
        mb = MagicMock()
        with tempfile.TemporaryDirectory() as d:
            _touch(d, "dbx:xyz.pdf")
            result = run_check(songs, {}, d, recording_lookup=mb)
        mb.get_year.assert_not_called()


class TestPrintReport(unittest.TestCase):
    def test_no_issues(self, ):
        from jamsite.check import CheckResult
        result = CheckResult()
        # Should not raise
        print_report(result, 100)

    def test_total_issues(self):
        from jamsite.check import CheckResult
        result = CheckResult()
        result.missing_fields = ["a", "b"]
        result.year_format = ["c"]
        self.assertEqual(result.total_issues, 3)


def _touch(directory, filename):
    """Create an empty file in the given directory."""
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        pass
    return path


if __name__ == "__main__":
    unittest.main()
