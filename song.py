class Song(object):
    SPREADSHEET_COLUMNS = {
        'uuid': 'A',
        'artist': 'B',
        'artist_sort': 'C',
        'title': 'D',
        'title_sort': 'E',
        'year': 'F',
        'download_link': 'G',
        'view_link': 'H',
        'modified_time': 'I',
        'deleted': 'J'
    }

    def __init__(self, uuid, artist, artist_sort, title, title_sort, year,
                 download_link, view_link, modified_time, deleted):
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

    def __repr__(self):
        a = [
            'uuid: ' + self.uuid,
            'artist_sort: ' + self.artist_sort,
            'artist: ' + self.artist,
            'title: ' + self.title,
            'title_sort: ' + self.title_sort,
            'year: ' + self.year,
            'download_link: ' + self.download_link,
            'view_link: ' + self.view_link,
            'modified_time: ' + self.modified_time,
            'deleted: ' + self.deleted,
        ]
        return ', '.join(a)
