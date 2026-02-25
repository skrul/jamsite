import unittest
import jinja2
from jamsite.song import Song


class TestTemplateKeyDisplay(unittest.TestCase):
    def setUp(self):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("jamsite/templates"),
            autoescape=jinja2.select_autoescape(["html"]),
        )

    def _render_song(self, song):
        template_str = (
            '{% for song in songs %}'
            '<span class="song-title-text">{{ song.title }}'
            '{% if song.key %} ({{ song.key }}){% endif %}'
            '</span>'
            '{% endfor %}'
        )
        t = jinja2.Environment(autoescape=True).from_string(template_str)
        return t.render(songs=[song])

    def test_key_shown_when_present(self):
        song = Song(
            "u1", "Artist", "artist", "Title", "title", "2020",
            "dl", "vl", "2020-01-01", False, False, key="C",
        )
        html = self._render_song(song)
        self.assertIn("Title (C)", html)

    def test_key_hidden_when_empty(self):
        song = Song(
            "u1", "Artist", "artist", "Title", "title", "2020",
            "dl", "vl", "2020-01-01", False, False,
        )
        html = self._render_song(song)
        self.assertIn("Title</span>", html)
        self.assertNotIn("()", html)

    def test_key_hidden_when_none(self):
        song = Song(
            "u1", "Artist", "artist", "Title", "title", "2020",
            "dl", "vl", "2020-01-01", False, False, key="",
        )
        html = self._render_song(song)
        self.assertNotIn("()", html)


if __name__ == "__main__":
    unittest.main()
