import json
import os
import time
from dataclasses import dataclass

import requests

MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/artist"
USER_AGENT = "Jamsite/0.1 (https://github.com/skrul/jamsite)"
RATE_LIMIT_SECONDS = 1.1
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5

CUSTOM_ARTISTS = {
    "gary schoofs": {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Gary Schoofs",
        "sort-name": "Schoofs, Gary",
        "score": 100,
        "disambiguation": "",
        "type": "Person",
        "country": "",
    },
}


def get_with_retry(url, params):
    """GET a MusicBrainz endpoint, backing off on rate limiting and server errors."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=10
            )
        except (requests.ConnectionError, requests.Timeout):
            if attempt == MAX_RETRIES:
                raise
            delay = 2 ** (attempt + 1)
        else:
            if response.status_code not in RETRY_STATUSES or attempt == MAX_RETRIES:
                response.raise_for_status()
                return response
            retry_after = response.headers.get("Retry-After", "")
            delay = int(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1)
        print(f"  MusicBrainz unavailable, retrying in {delay}s...")
        time.sleep(delay)


@dataclass
class ArtistResult:
    mb_id: str
    name: str
    sort_name: str
    score: int
    disambiguation: str
    type: str
    country: str


class MusicBrainzArtistLookup:
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
                json.dump(self._cache, f, indent=2)

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()

    def search_artist(self, name):
        key = name.lower()

        # Check custom artists first
        if key in CUSTOM_ARTISTS:
            a = CUSTOM_ARTISTS[key]
            return [
                ArtistResult(
                    mb_id=a["id"],
                    name=a["name"],
                    sort_name=a["sort-name"],
                    score=a["score"],
                    disambiguation=a["disambiguation"],
                    type=a["type"],
                    country=a["country"],
                )
            ]

        # Check cache
        if key in self._cache:
            return [ArtistResult(**r) for r in self._cache[key]]

        # Query MusicBrainz API
        self._rate_limit()
        response = get_with_retry(
            MUSICBRAINZ_API_URL, {"query": name, "fmt": "json", "limit": 5}
        )
        data = response.json()

        results = []
        for artist in data.get("artists", []):
            results.append(
                ArtistResult(
                    mb_id=artist.get("id", ""),
                    name=artist.get("name", ""),
                    sort_name=artist.get("sort-name", ""),
                    score=artist.get("score", 0),
                    disambiguation=artist.get("disambiguation", ""),
                    type=artist.get("type", ""),
                    country=artist.get("country", ""),
                )
            )

        # Cache the results
        self._cache[key] = [
            {
                "mb_id": r.mb_id,
                "name": r.name,
                "sort_name": r.sort_name,
                "score": r.score,
                "disambiguation": r.disambiguation,
                "type": r.type,
                "country": r.country,
            }
            for r in results
        ]
        self._save_cache()

        return results
