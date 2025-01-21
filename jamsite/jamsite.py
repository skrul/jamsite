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
from collections import defaultdict
import hashlib
from .search_indexer import SearchIndexer
import json
import dropbox
from . import store

PORT = 8000
JAM_SONGS_FOLDER_ID = "1YBA99d9GmHTa6HktdpjHvSpoMQfoOrBb"
JAM_SONGS_SPREADSHEET_ID = "1yGF1CY-obfm5QWiVhvvBoN5XYtQe902hs1np6b6G9Ag"
GARY_SONGS_FOLDER_PATH = "/Lyrics + Chords"
S3_BUCKET = "skrul.com"

CONTENT_TYPES = {"html": "text/html", "css": "text/css", "js": "application/javascript"}


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
        d = defaultdict(lambda: "")
        for i, v in enumerate(value):
            d[i] = v
        song = Song(
            d[0],
            d[1],
            d[2],
            d[3],
            d[4],
            d[5],
            d[6],
            d[7],
            d[8],
            d[9] == "x",
            d[10] == "x",
        )
        songs_by_row[row] = song
    return songs_by_row


def sync_to_spreadsheet(service, sheet, drive_songs, existing_songs_by_row):
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

    values = [
        [
            s.uuid,
            s.artist,
            None,
            s.title,
            None,
            s.year,
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


def generate(songs):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(pdir("jamsite/templates")),
        autoescape=jinja2.select_autoescape(["html"]),
    )

    jam_dir = pdir("dist/jam")
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

    si = SearchIndexer()
    for song in songs:
        if song.skip:
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
    songs_by_title = [s for s in songs_by_title if not s.skip]

    def render(name):
        decade_list = list(decades.keys())
        decade_list.sort()
        template = env.get_template(name)
        template.stream(
            songs=songs_by_title,
            decades=decade_list,
            static_file_hashes=static_file_hashes,
        ).dump(os.path.join(jam_dir, name))

    render("index.html")
    render("jamulus.html")


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
    songs_by_row = read_songs_spreadsheet(sheets_service, "skrul")
    songs_by_row.update(read_songs_spreadsheet(sheets_service, "gary"))
    songs = list(songs_by_row.values())
    if cache:
        with open(cache_file, "wb") as songs_pickle:
            pickle.dump(songs, songs_pickle)
    return songs


def serve():
    os.chdir(pdir("dist"))
    Handler = http.server.SimpleHTTPRequestHandler
    m = Handler.extensions_map
    m[""] = "text/plain"
    m.update(dict([(k, v + ";charset=UTF-8") for k, v in m.items()]))

    server = socketserver.TCPServer(("", PORT), Handler, bind_and_activate=False)
    server.allow_reuse_address = True
    server.server_bind()
    server.server_activate()
    print("serving at port", PORT)
    print("http://localhost:8000/jam/")
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


def get_drive():
    return google_api.auth("drive", "v3")


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
    parser.add_argument("--songs-dir")
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()
    if args.sync:
        drive_service = get_drive()
        drive_songs = store.get_songs_from_drive(drive_service, JAM_SONGS_FOLDER_ID)

        sheets_service = google_api.auth("sheets", "v4")
        existing_songs_by_row = read_songs_spreadsheet(sheets_service, "skrul")
        sync_to_spreadsheet(sheets_service, "skrul", drive_songs, existing_songs_by_row)
    if args.sync_gary:
        dbx = get_dbx()
        dbx_songs = store.get_songs_from_dropbox(dbx, GARY_SONGS_FOLDER_PATH)

        sheets_service = google_api.auth("sheets", "v4")
        existing_songs_by_row = read_songs_spreadsheet(sheets_service, "gary")
        sync_to_spreadsheet(sheets_service, "gary", dbx_songs, existing_songs_by_row)
    if args.download:
        songs_dir = os.getenv("SONGS_DIR") or args.songs_dir
        if not songs_dir:
            parser.error("--songs-dir or SONGS_DIR environment variable is required when using --download")
        print(f"Downloading songs to {songs_dir}")
        drive_service = get_drive()
        drive_songs = store.get_songs_from_drive(drive_service, JAM_SONGS_FOLDER_ID)
        store.download_songs_from_drive(drive_service, drive_songs, songs_dir)

        dbx = get_dbx()
        dbx_songs = store.get_songs_from_dropbox(dbx, GARY_SONGS_FOLDER_PATH)
        store.download_songs_from_dropbox(dbx, dbx_songs, songs_dir)
    if args.generate:
        songs = get_songs(args.cached)
        generate(songs)
    if args.serve:
        serve()
    if args.publish:
        publish(args.aws_profile)
