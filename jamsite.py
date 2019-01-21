import sys
import os
import google_api
from song import Song
import re
import pprint
import argparse
import jinja2
import pathlib
import http.server
import socketserver
import boto3

PORT = 8000
JAM_SONGS_FOLDER_ID = '1YBA99d9GmHTa6HktdpjHvSpoMQfoOrBb'
JAM_SONGS_SPREADSHEET_ID = '1yGF1CY-obfm5QWiVhvvBoN5XYtQe902hs1np6b6G9Ag'
S3_BUCKET = 'skrul.com'

def get_songs_from_drive(service):
    page_token = None
    songs= []
    while True:
        response = service.files().list(
            q=f"'{JAM_SONGS_FOLDER_ID}' in parents and trashed = false",
            fields='nextPageToken, files(id, name, webContentLink)',
            pageToken=page_token).execute()
        for file in response.get('files', []):
            match = re.match(r'(.*) [-‐] (.*) \((.*)\)\.pdf', file.get('name'))
            if match is not None:
                song = Song(
                    'gd:' + file.get('id'),
                    match.group(2),
                    match.group(1),
                    match.group(3),
                    file.get('webContentLink'))
                songs.append(song)
            else:
                print('Skipping ' + file.get('name'))
            page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return songs

def read_songs_spreadsheet(service):
    result = service.spreadsheets().values().get(
        spreadsheetId=JAM_SONGS_SPREADSHEET_ID,
        range='songs').execute()
    values = result.get('values')
    songs_by_row = {}
    for row, value in enumerate(values):
        if row == 0:
            continue
        song = Song(value[0], value[1], value[2], value[3], value[4])
        songs_by_row[row] = song
    return songs_by_row

def sync_to_spreadsheet(service, drive_songs, existing_songs_by_row):
    existing_songs_uuids = set([existing_songs_by_row[k].uuid for k in existing_songs_by_row])
    to_append = []
    for song in drive_songs:
        if song.uuid not in existing_songs_uuids:
            to_append.append(song)

    values = [[s.uuid, s.artist, s.title, s.year, s.link] for s in to_append]
    result = service.spreadsheets().values().append(
        spreadsheetId=JAM_SONGS_SPREADSHEET_ID,
        valueInputOption='RAW',
        range='songs',
        body={ 'values': values }).execute()

def generate(songs):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(pdir('templates')),
        autoescape=jinja2.select_autoescape(['html'])
    )

    jam_dir = pdir('dist/jam')
    if not os.path.exists(jam_dir):
        os.makedirs(jam_dir)

    def render(name, songs):
        template = env.get_template(name)
        template.stream(songs=songs).dump(os.path.join(jam_dir, name))

    songs_by_title = sorted(songs, key=lambda s: s.title)
    render('titles.html', songs_by_title)

def publish(aws_profile):
    session = boto3.Session(profile_name=aws_profile)
    s3 = session.client('s3')
    dist_dir = pdir('dist')
    for root, dirs, files in os.walk(dist_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            remote_path = os.path.relpath(local_path, dist_dir)
            print(f"Uploading {local_path} to {remote_path}")
            s3.upload_file(
                local_path,
                S3_BUCKET,
                remote_path,
                ExtraArgs={ 'ContentType': 'text/html' }
            )

def serve():
    os.chdir(pdir('dist'))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print('serving at port', PORT)
        print('http://localhost:8000/jam/title.html')
        httpd.serve_forever()

def pdir(name):
    return os.path.normpath(os.path.join(os.getcwd(), name))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sync', action='store_true')
    group.add_argument('--generate', action='store_true')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--aws-profile')
    args = parser.parse_args()
    if args.sync:
        drive_service = google_api.auth('drive', 'v3')
        drive_songs = get_songs_from_drive(drive_service)

        sheets_service = google_api.auth('sheets', 'v4')
        existing_songs_by_row = read_songs_spreadsheet(sheets_service)
        sync_to_spreadsheet(sheets_service, drive_songs, existing_songs_by_row)
    if args.generate:
        sheets_service = google_api.auth('sheets', 'v4')
        songs_by_row = read_songs_spreadsheet(sheets_service)
        generate(songs_by_row.values())
    if args.serve:
        serve()
    if args.publish:
        publish(args.aws_profile)
