import os
from . import google_api
from jamsite.song import Song
import re
import argparse
import jinja2
import pathlib
import http.server
import socketserver
import boto3
from shutil import copytree
import pickle
import hashlib
from .search_indexer import SearchIndexer
import json
import dropbox
from . import store
import shutil
from .artists import read_artists, append_artist, Artist
from .musicbrainz import MusicBrainzArtistLookup

PORT = 8000
JAM_SONGS_FOLDER_ID = "1YBA99d9GmHTa6HktdpjHvSpoMQfoOrBb"
JAM_SONGS_SPREADSHEET_ID = "1yGF1CY-obfm5QWiVhvvBoN5XYtQe902hs1np6b6G9Ag"
GARY_SONGS_FOLDER_PATH = "/Lyrics + Chords"
S3_BUCKET = "skrul.com"

CONTENT_TYPES = {"html": "text/html", "css": "text/css", "js": "application/javascript"}
MB_CACHE_PATH = os.path.expanduser("~/.jamsite_mb_cache.json")


def _looks_like_collab(original_name, mb_name):
    """Check if the original name looks like a collaboration credit."""
    has_collab_marker = "&" in original_name or " and " in original_name.lower()
    significantly_shorter = len(mb_name) < len(original_name) * 0.75
    return has_collab_marker and significantly_shorter


def _prompt_accept_match(result):
    """Prompt user to accept/reject a MusicBrainz match. Returns 'y', 'n', or 's'."""
    score_warning = " ⚠️ LOW CONFIDENCE" if result.score < 90 else ""
    print(f"  MusicBrainz match (score {result.score}):{score_warning}")
    print(f"    Name: {result.name}")
    print(f"    Sort: {result.sort_name}")
    type_info = result.type or "Unknown"
    country_info = result.country or "??"
    print(f"    Type: {type_info}, Country: {country_info}")
    print(f"    ID: {result.mb_id}")
    if result.disambiguation:
        print(f"    ({result.disambiguation})")
    choice = input("  Accept? [Y/n/s(kip)] ").strip().lower()
    if choice in ("", "y"):
        return "y"
    elif choice == "n":
        return "n"
    else:
        return "s"


def _prompt_display_name(original_name, mb_name):
    """Prompt user to choose display name. Returns the chosen name."""
    if original_name.lower() == mb_name.lower():
        return mb_name
    is_collab = _looks_like_collab(original_name, mb_name)
    if is_collab:
        default = "k"
        print(f'  Use "{mb_name}" as display name, or keep "{original_name}"? [k(eep)/m(b)]')
    else:
        default = "m"
        print(f'  Use "{mb_name}" as display name, or keep "{original_name}"? [m(b)/k(eep)]')
    choice = input("  ").strip().lower()
    if choice == "":
        choice = default
    if choice == "k":
        return original_name
    return mb_name


def resolve_artist_sort(song, artists_by_name, mb, sheets_service):
    """Resolve artist_sort for a new song. Returns the sort name or None.

    May prompt the user interactively and update artists_by_name + the artists sheet.
    """
    if not song.artist:
        return None

    key = song.artist.lower()
    if key in artists_by_name:
        return artists_by_name[key].mb_sort

    print(f'\nNew artist: "{song.artist}"')
    results = mb.search_artist(song.artist)
    if not results:
        print("  No MusicBrainz results found.")
        sort_name = input("  Enter sort name manually (or press Enter to skip): ").strip()
        return sort_name or None

    top = results[0]
    choice = _prompt_accept_match(top)

    if choice == "y":
        display_name = _prompt_display_name(song.artist, top.name)
        artist = Artist(
            name=display_name,
            mb_id=top.mb_id,
            mb_artist=top.name,
            mb_sort=top.sort_name,
        )
        artists_by_name[display_name.lower()] = artist
        # Also index by the song's artist name so subsequent songs match
        if key != display_name.lower():
            artists_by_name[key] = artist
        if sheets_service:
            append_artist(sheets_service, JAM_SONGS_SPREADSHEET_ID, artist)
        return top.sort_name
    elif choice == "n":
        sort_name = input("  Enter sort name manually (or press Enter to skip): ").strip()
        return sort_name or None
    else:
        return None


def read_songs_spreadsheet(service, sheet):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=JAM_SONGS_SPREADSHEET_ID, range=sheet)
        .execute()
    )
    values = result.get("values")
    songs_by_row = {}
    for row, value in enumerate(values):
        if row == 0:
            continue
        songs_by_row[row] = Song.from_spreadsheet_row(value)
    return songs_by_row


def sync_to_spreadsheet(
    service, sheet, drive_songs, existing_songs_by_row,
    artists_by_name=None, mb=None,
):
    existing_songs_uuids = {
        existing_songs_by_row[r].uuid: (r, existing_songs_by_row[r])
        for r in existing_songs_by_row
    }
    to_append = []
    to_update = []
    drive_songs_uuids = set()
    for song in drive_songs:
        drive_songs_uuids.add(song.uuid)
        if song.uuid not in existing_songs_uuids:
            to_append.append(song)
        else:
            row, existing_song = existing_songs_uuids[song.uuid]
            if existing_song.view_link == "":
                to_update.append(
                    {
                        "range": sheet
                        + "!"
                        + Song.SPREADSHEET_COLUMNS["view_link"]
                        + str(row + 1),
                        "values": [[song.view_link]],
                    }
                )
    for row in existing_songs_by_row:
        existing_song = existing_songs_by_row[row]
        is_deleted = existing_song.uuid not in drive_songs_uuids
        if existing_song.deleted != is_deleted:
            to_update.append(
                {
                    "range": sheet
                    + "!"
                    + Song.SPREADSHEET_COLUMNS["deleted"]
                    + str(row + 1),
                    "values": [["x" if is_deleted else ""]],
                }
            )

    # Resolve artist_sort for new songs
    artist_sort_map = {}
    if artists_by_name is not None and mb is not None:
        for s in to_append:
            if s.artist and s.artist.lower() not in artist_sort_map:
                sort_name = resolve_artist_sort(
                    s, artists_by_name, mb, service
                )
                artist_sort_map[s.artist.lower()] = sort_name

    values = [
        [
            s.uuid,
            s.artist,
            artist_sort_map.get(s.artist.lower()) if artists_by_name is not None else None,
            s.title,
            None,
            s.year,
            "",              # key - empty for new songs
            s.download_link,
            s.view_link,
            s.modified_time,
            "",
        ]
        for s in to_append
    ]
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=JAM_SONGS_SPREADSHEET_ID,
            valueInputOption="RAW",
            range=f"{sheet}!A1",
            body={"values": values},
        )
        .execute()
    )

    result = (
        service.spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=JAM_SONGS_SPREADSHEET_ID,
            body={"valueInputOption": "RAW", "data": to_update},
        )
        .execute()
    )


def generate(songs, songs_dir):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(pdir("jamsite/templates")),
        autoescape=jinja2.select_autoescape(["html"]),
    )

    jam_dir = pdir("dist")
    if not os.path.exists(jam_dir):
        os.makedirs(jam_dir)

    static_files = []
    static_file_hashes = {}
    dist_css = os.path.join(jam_dir, "css")
    copytree(pdir("jamsite/css"), dist_css, dirs_exist_ok=True)
    static_files.extend(get_files(dist_css))

    dist_js = os.path.join(jam_dir, "js")
    copytree(pdir("jamsite/js"), dist_js, dirs_exist_ok=True)
    static_files.extend(get_files(dist_js))

    # Copy the service worker to the dist directory since it needs to be served from the root.
    shutil.copy(pdir("jamsite/js/service_worker.js"), jam_dir)

    si = SearchIndexer()
    for song in songs:
        if song.skip or song.deleted:
            continue
        si.add_song(song)
    index_str = json.dumps(si.index_as_dict(), separators=(",", ":"))
    id_map_str = json.dumps(si.uuids, separators=(",", ":"))
    decades_map_str = json.dumps(si.decades, separators=(",", ":"))
    decades = si.decades
    search_data_path = os.path.join(jam_dir, "js", "search_data.js")
    with open(search_data_path, "w") as f:
        f.write(
            f"var INDEX_DATA = {index_str}; var INDEX_ID_MAP = {id_map_str}; var DECADES_MAP = {decades_map_str};"
        )
    static_files.append(search_data_path)

    for f in static_files:
        rel_path = os.path.relpath(f, jam_dir)
        static_file_hashes[rel_path] = get_hash(f)

    songs_by_title = sorted(songs, key=lambda s: s.title)
    songs_by_title = [s for s in songs_by_title if not s.skip and not s.deleted]

    def render(name):
        decade_list = list(decades.keys())
        decade_list.sort()
        # move the decane named "old af" to the front.
        if "old af" in decade_list:
            decade_list.remove("old af")
            decade_list.insert(0, "old af")
        template = env.get_template(name)
        template.stream(
            songs=songs_by_title,
            decades=decade_list,
            static_file_hashes=static_file_hashes,
        ).dump(os.path.join(jam_dir, name))

    render("index.html")
    render("reset.html")

    # Build songs.json that is an array of objects with uuid and hash.
    songs_json = []
    for song in songs_by_title:
        try:
       	    metadata_path = os.path.join(songs_dir, song.uuid + ".json")
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                songs_json.append({"uuid": song.uuid, "hash": metadata["hash"]})
        except Exception as e:
            print(f"⚠️ Unexpected error with song {song.uuid}: {e}")
    with open(os.path.join(jam_dir, "songs.json"), "w") as f:
        json.dump(songs_json, f)


def publish(aws_profile):
    session = boto3.Session(profile_name=aws_profile)
    s3 = session.client("s3")
    dist_dir = pdir("dist")
    for root, dirs, files in os.walk(dist_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            remote_path = os.path.relpath(local_path, dist_dir)
            content_type = CONTENT_TYPES[pathlib.Path(remote_path).suffix[1:]]
            print(f"Uploading {local_path} to {remote_path}")
            s3.upload_file(
                local_path,
                S3_BUCKET,
                remote_path,
                ExtraArgs={
                    "ContentType": content_type + "; charset=utf-8",
                    "StorageClass": "REDUCED_REDUNDANCY",
                    "CacheControl": "no-cache",
                },
            )


def get_songs(cache):
    cache_file = pdir("songs.pickle")
    if cache:
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as songs_pickle:
                return pickle.load(songs_pickle)
    sheets_service = google_api.auth("sheets", "v4")
    skrul_songs_by_row = read_songs_spreadsheet(sheets_service, "skrul")
    print(f"skrul song count: {len(skrul_songs_by_row)}")
    gary_songs_by_row = read_songs_spreadsheet(sheets_service, "gary")
    print(f"gary song count: {len(gary_songs_by_row)}")
    songs = list(skrul_songs_by_row.values()) + list(gary_songs_by_row.values())
    if cache:
        with open(cache_file, "wb") as songs_pickle:
            pickle.dump(songs, songs_pickle)
    return songs


class JamSiteHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, songs_dir=None, **kwargs):
        self.songs_dir = songs_dir
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.startswith('/songs/'):
            relative_path = self.path[7:]  # Remove '/songs/'
            file_path = os.path.join(self.songs_dir, relative_path)
            
            try:
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    # Set content type for PDF files
                    if file_path.lower().endswith('.pdf'):
                        self.send_header('Content-Type', 'application/pdf')
                    else:
                        self.send_header('Content-Type', 'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, str(e))
        else:
            # Handle all other requests using the default static file handler
            super().do_GET()


def serve(songs_dir):
    os.chdir(pdir("dist"))
    
    # Create handler with songs directory
    handler = lambda *args, **kwargs: JamSiteHandler(*args, songs_dir=songs_dir, **kwargs)
    
    # Set up content type mappings
    m = handler.extensions_map = http.server.SimpleHTTPRequestHandler.extensions_map.copy()
    m[""] = "text/plain"
    m.update(dict([(k, v + ";charset=UTF-8") for k, v in m.items()]))

    server = socketserver.TCPServer(("", PORT), handler, bind_and_activate=False)
    server.allow_reuse_address = True
    server.server_bind()
    server.server_activate()
    print("serving at port", PORT)
    print("http://localhost:8000/")
    print(f"Serving songs from: {songs_dir}")
    server.serve_forever()


def pdir(name):
    return os.path.normpath(os.path.join(os.getcwd(), name))


def get_files(path):
    files = []
    for root, dirs, filenames in os.walk(path):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    return files


def get_hash(f_path):
    h = hashlib.new("md5")
    with open(f_path, "rb") as file:
        data = file.read()
    h.update(data)
    digest = h.hexdigest()
    return digest


def get_dbx():
    # Refresh this token https://www.dropbox.com/developers/apps/info/prsqycfo9z22u99
    token_file = os.getenv("DROPBOX_TOKEN_FILE", "dropbox_token.txt")
    token = pathlib.Path(token_file).read_text().strip()
    dbx = dropbox.Dropbox(token)
    return dbx


def get_drive(force_reauth=False):
    return google_api.auth("drive", "v3", force_reauth=force_reauth)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sync", action="store_true")
    group.add_argument("--sync-gary", action="store_true")
    group.add_argument("--generate", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--aws-profile")
    parser.add_argument("--force-google-reauth", action="store_true")
    parser.add_argument("--songs-dir")
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()

    songs_dir = os.getenv("SONGS_DIR", "/Volumes/songs/data")

    if args.sync:
        drive_service = get_drive(force_reauth=args.force_google_reauth)
        drive_songs = store.get_songs_from_drive(drive_service, JAM_SONGS_FOLDER_ID)

        sheets_service = google_api.auth("sheets", "v4", force_reauth=args.force_google_reauth)
        existing_songs_by_row = read_songs_spreadsheet(sheets_service, "skrul")
        artists_by_name = read_artists(sheets_service, JAM_SONGS_SPREADSHEET_ID)
        mb = MusicBrainzArtistLookup(cache_path=MB_CACHE_PATH)
        sync_to_spreadsheet(
            sheets_service, "skrul", drive_songs, existing_songs_by_row,
            artists_by_name=artists_by_name, mb=mb,
        )
    if args.sync_gary:
        dbx = get_dbx()
        dbx_songs = store.get_songs_from_dropbox(dbx, GARY_SONGS_FOLDER_PATH)

        sheets_service = google_api.auth("sheets", "v4")
        existing_songs_by_row = read_songs_spreadsheet(sheets_service, "gary")
        artists_by_name = read_artists(sheets_service, JAM_SONGS_SPREADSHEET_ID)
        mb = MusicBrainzArtistLookup(cache_path=MB_CACHE_PATH)
        sync_to_spreadsheet(
            sheets_service, "gary", dbx_songs, existing_songs_by_row,
            artists_by_name=artists_by_name, mb=mb,
        )
    if args.download:
        print(f"Downloading songs to {songs_dir}")
        drive_service = get_drive(force_reauth=args.force_google_reauth)
        drive_songs = store.get_songs_from_drive(drive_service, JAM_SONGS_FOLDER_ID)
        store.download_songs_from_drive(drive_service, drive_songs, songs_dir)

        dbx = get_dbx()
        dbx_songs = store.get_songs_from_dropbox(dbx, GARY_SONGS_FOLDER_PATH)
        store.download_songs_from_dropbox(dbx, dbx_songs, songs_dir)
    if args.generate:
        songs = get_songs(args.cached)
        generate(songs, songs_dir)
    if args.serve:
        serve(songs_dir)
    if args.publish:
        publish(args.aws_profile)
