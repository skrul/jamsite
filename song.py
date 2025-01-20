class Song(object):
    SPREADSHEET_COLUMNS = {
        "uuid": "A",
        "artist": "B",
        "artist_sort": "C",
        "title": "D",
        "title_sort": "E",
        "year": "F",
        "download_link": "G",
        "view_link": "H",
        "modified_time": "I",
        "deleted": "J",
        "skip": "K",
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
    ):
        self.uuid = uuid
        self.artist = artist
        self.artist_sort = artist_sort
        self.title = title
        self.title_sort = title_sort
        self.year = year
        self.download_link = download_link
        self.view_link = view_link
        self.modified_time = modified_time
        self.deleted = deleted
        self.skip = skip
    def __repr__(self):
        a = [
            "uuid: " + self.uuid,
            "artist_sort: " + str(self.artist_sort),
            "artist: " + str(self.artist),
            "title: " + str(self.title),
            "title_sort: " + str(self.title_sort),
            "year: " + str(self.year),
            "download_link: " + str(self.download_link),
            "view_link: " + str(self.view_link),
            "modified_time: " + str(self.modified_time),
            "deleted: " + str(self.deleted),
            "skip: " + str(self.skip),
        ]
        return ", ".join(a)
