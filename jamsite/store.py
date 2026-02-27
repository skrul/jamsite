import re
import pathlib
import datetime
import tempfile
import urllib.parse
import dropbox
from .song import Song
import os
import json
from googleapiclient.http import MediaIoBaseDownload
import requests
from gotenberg_client import GotenbergClient
from pathlib import Path


def get_songs_from_drive(service, folder_id):
    page_token = None
    songs = []
    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, webContentLink, webViewLink, modifiedTime, sha1Checksum)",
                pageToken=page_token,
            )
            .execute()
        )
        for file in response.get("files", []):
            match = re.match(r"(.*) [-‐] (.*) \((.*)\)(?:\s+\[[^\]]+\])?\.pdf", file.get("name"))
            if match is not None:
                song = Song(
                    "gd:" + file.get("id"),
                    match.group(2),
                    None,
                    match.group(1),
                    None,
                    match.group(3),
                    file.get("webContentLink"),
                    file.get("webViewLink"),
                    file.get("modifiedTime"),
                    False,
                    False,
                    hash=file.get("sha1Checksum"),
                )
                songs.append(song)
            else:
                print("Skipping " + file.get("name"))
            page_token = response.get("nextPageToken", None)
        if page_token is None:
            break
    return songs


def get_songs_from_dropbox(dbx, path):
    songs = []
    response = dbx.files_list_folder(path)
    while True:
        for entry in response.entries:
            # Skip folders
            if isinstance(entry, dropbox.files.FolderMetadata):
                continue
            modified = entry.server_modified.replace(tzinfo=datetime.UTC)
            song = Song(
                "dbx:" + entry.id,
                "",
                None,
                pathlib.Path(entry.name).stem,
                None,
                None,
                None,
                f"https://www.dropbox.com/home/{urllib.parse.quote('Lyrics + Chords')}?preview={urllib.parse.quote(entry.name)}",
                modified.isoformat(),
                False,
                False,
                hash=entry.content_hash,
            )
            songs.append(song)

        if not response.has_more:
            break
        response = dbx.files_list_folder_continue(response.cursor)
    return songs


def download_songs_from_drive(service, songs, dest):
    count_songs = 0
    count_exists = 0
    count_downloaded = 0

    for song in songs:
        count_songs += 1
        song_base_path = os.path.join(dest, song.uuid)
        metadata_path = song_base_path + ".json"
        song_path = song_base_path + ".pdf"
        should_download = True

        if os.path.exists(song_path) and os.path.exists(metadata_path):
            with open(metadata_path) as f:
                metadata = json.load(f)
                if metadata.get("hash") == song.hash:
                    should_download = False
                else:
                    print(f"Hash mismatch for {song.title} {song.uuid}")
                    print(f"Metadata: {metadata.get('hash')}")
                    print(f"Song: {song.hash}")

        if should_download:
            count_downloaded += 1
            file_id = song.uuid.split(":")[1]
            print(f"Downloading {file_id}")
            request = service.files().get_media(fileId=file_id)
            with open(song_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

            # Write metadata file with hash
            with open(metadata_path, "w") as f:
                json.dump({"hash": song.hash}, f)
        else:
            print(f"Exists {song.title} {song.uuid}")
            count_exists += 1

    print("GDrive download:")
    print(f"  Total songs: {count_songs}")
    print(f"  Downloaded {count_downloaded} songs")
    print(f"  Exists {count_exists} songs")


def download_songs_from_dropbox(dbx, songs, dest):
    count_songs = 0
    count_converted = 0
    count_exists = 0
    count_unsupported = 0
    count_downloaded = 0

    for song in songs:
        count_songs += 1

        song_base_path = os.path.join(dest, song.uuid)
        metadata_path = song_base_path + ".json"
        song_path = song_base_path + ".pdf"
        should_download = True

        # Check if metadata file exists and hash matches
        if os.path.exists(song_path) and os.path.exists(metadata_path):
            with open(metadata_path) as f:
                metadata = json.load(f)
                if metadata.get("hash") == song.hash:
                    should_download = False
                else:
                    print(f"Hash mismatch for {song.title} {song.uuid}")
                    print(f"Metadata: {metadata.get('hash')}")
                    print(f"Song: {song.hash}")

        if should_download:
            file_id = song.uuid.split(":", 1)[1]
            print(f"Downloading {song.title} {file_id}")

            # This is a dumb hack but what you gonna do
            # Extract file name from view_link
            extension = song.view_link.split(".")[-1]
            if extension == "pdf":
                count_downloaded += 1
                dbx.files_download_to_file(song_path, file_id)
            elif extension in ["doc", "docx", "rtf", "txt"]:
                count_downloaded += 1
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    dbx.files_download_to_file(
                        temp_file.name + "." + extension, file_id
                    )
                    convert_to_pdf(temp_file.name + "." + extension, song_path)
                count_converted += 1
            else:
                print(f"Unsupported file type: {song}")
                count_unsupported += 1
                continue

            # Write metadata file with hash
            with open(metadata_path, "w") as f:
                json.dump({"hash": song.hash}, f)
        else:
            print(f"Exists {song.title} {song.uuid}")
            count_exists += 1

    print("Dropbox download:")
    print(f"  Total songs: {count_songs}")
    print(f"  Downloaded {count_downloaded} songs")
    print(f"  Exists {count_exists} songs")
    print(f"  Converted {count_converted} songs")
    print(f"  Unsupported {count_unsupported} songs")


def convert_to_pdf(input_path, output_path):
    print(f"Converting {input_path} to {output_path}")
    gotenberg_url = os.getenv("GOTENBERG_URL", "http://gotenberg:3000")
    with GotenbergClient(gotenberg_url) as client:
        with client.libre_office.to_pdf() as route:
            response = route.convert(Path(input_path)).run()
            response.to_file(Path(output_path))
