import unicodedata
from dataclasses import dataclass


ARTISTS_SHEET = "artists"


@dataclass
class Artist:
    name: str
    mb_id: str
    mb_artist: str
    mb_sort: str


def read_artists(service, spreadsheet_id):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=ARTISTS_SHEET)
        .execute()
    )
    values = result.get("values", [])
    artists_by_name = {}
    for row_num, row in enumerate(values):
        if row_num == 0:
            continue
        # Columns: A=name, B=mb_id, C=mb_artist, D=mb_sort
        name = row[0] if len(row) > 0 else ""
        mb_id = row[1] if len(row) > 1 else ""
        mb_artist = row[2] if len(row) > 2 else ""
        mb_sort = row[3] if len(row) > 3 else ""
        if name:
            artists_by_name[unicodedata.normalize("NFC", name.lower())] = Artist(
                name=name,
                mb_id=mb_id,
                mb_artist=mb_artist,
                mb_sort=mb_sort,
            )
    return artists_by_name


def append_artist(service, spreadsheet_id, artist):
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        valueInputOption="RAW",
        range=f"{ARTISTS_SHEET}!A1",
        body={
            "values": [[artist.name, artist.mb_id, artist.mb_artist, artist.mb_sort]]
        },
    ).execute()
