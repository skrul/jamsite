from collections import defaultdict


class Song:
    SPREADSHEET_COLUMNS = {
        "uuid": "A",
        "artist": "B",
        "artist_sort": "C",
        "title": "D",
        "title_sort": "E",
        "year": "F",
        "key": "G",
        "download_link": "H",
        "view_link": "I",
        "modified_time": "J",
        "deleted": "K",
        "skip": "L",
    }

    def __init__(
        self,
        uuid,
        artist,
        artist_sort,
        title,
        title_sort,
        year,
        download_link,
        view_link,
        modified_time,
        deleted,
        skip,
        key="",
        hash=None,
    ):
        self.uuid = uuid
        self.artist = artist
        self.artist_sort = artist_sort
        self.title = title
        self.title_sort = title_sort
        self.year = year
        self.key = key
        self.download_link = download_link
        self.view_link = view_link
        self.modified_time = modified_time
        self.deleted = deleted
        self.skip = skip
        self.hash = hash

    def __repr__(self):
        a = [
            "uuid: " + self.uuid,
            "artist_sort: " + str(self.artist_sort),
            "artist: " + str(self.artist),
            "title: " + str(self.title),
            "title_sort: " + str(self.title_sort),
            "year: " + str(self.year),
            "key: " + str(self.key),
            "download_link: " + str(self.download_link),
            "view_link: " + str(self.view_link),
            "modified_time: " + str(self.modified_time),
            "deleted: " + str(self.deleted),
            "skip: " + str(self.skip),
            "hash: " + str(self.hash),
        ]
        return ", ".join(a)

    @classmethod
    def from_spreadsheet_row(cls, row):
        d = defaultdict(lambda: "")
        for i, v in enumerate(row):
            d[i] = v
        return cls(
            uuid=d[0],
            artist=d[1],
            artist_sort=d[2],
            title=d[3],
            title_sort=d[4],
            year=d[5],
            download_link=d[7],
            view_link=d[8],
            modified_time=d[9],
            deleted=d[10] == "x",
            skip=d[11] == "x",
            key=d[6],
        )
