class Song(object):
    def __init__(self, uuid, artist, artist_sort, title, title_sort, year, link):
        self.uuid = uuid
        self.artist = artist
        self.artist_sort = artist_sort
        self.title = title
        self.title_sort = title_sort
        self.year = year
        self.link = link

    def __repr__(self):
        a = [
            'uuid: ' + self.uuid,
            'artist_sort: ' + self.artist_sort,
            'artist: ' + self.artist,
            'title: ' + self.title,
            'title_sort: ' + self.title_sort,
            'year: ' + self.year,
            'link: ' + self.link
        ]
        return ', '.join(a)
