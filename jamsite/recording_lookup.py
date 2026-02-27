"""
MusicBrainz recording search for year validation.

Adapted from packeteer's musicbrainz_lookup.py. Uses the recording search
endpoint to find the earliest release year for a given title + artist.
"""

import json
import os
import re
import time

import requests

MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/recording"
USER_AGENT = "Jamsite/0.1 (https://github.com/skrul/jamsite)"
RATE_LIMIT_SECONDS = 1.1


class RecordingLookup:
    def __init__(self, cache_path=None):
        self._last_request_time = 0.0
        self._cache_path = cache_path
        self._cache = {}
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, ValueError):
                self._cache = {}

    def _save_cache(self):
        if self._cache_path:
            with open(self._cache_path, "w") as f:
                json.dump(self._cache, f, indent=2, sort_keys=True)

    def _cache_key(self, title, artist):
        return f"{title.lower().strip()}|{artist.lower().strip()}"

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _search(self, query):
        """Execute a MusicBrainz recording search, return earliest release year or None."""
        self._rate_limit()
        try:
            response = requests.get(
                MUSICBRAINZ_API_URL,
                params={"query": query, "fmt": "json", "limit": 5},
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return None

        recordings = data.get("recordings", [])
        earliest_year = None
        for rec in recordings:
            for release in rec.get("releases", []):
                date = release.get("date", "")
                if date and len(date) >= 4:
                    year = date[:4]
                    if year.isdigit():
                        if earliest_year is None or year < earliest_year:
                            earliest_year = year
        return earliest_year

    def _simplify(self, text):
        """Strip parentheticals, capo references, and extra whitespace."""
        text = re.sub(r"\(.*?\)", "", text)
        text = re.sub(r"\bcapo\s+\w+\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_year(self, title, artist):
        """Look up earliest release year for a song. Returns cached result if available."""
        key = self._cache_key(title, artist)
        if key in self._cache:
            return self._cache[key] if self._cache[key] else None

        # Progressive search: exact title+artist, title-only, simplified
        queries = [
            f'recording:"{title}" AND artist:"{artist}"',
            f'recording:"{title}"',
        ]
        simplified = self._simplify(title)
        if simplified.lower() != title.lower():
            queries.append(f'recording:"{simplified}" AND artist:"{artist}"')

        year = None
        for query in queries:
            year = self._search(query)
            if year:
                break

        self._cache[key] = year
        self._save_cache()
        return year
