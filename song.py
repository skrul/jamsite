class Song(object):
    def __init__(self, uuid, artist, title, year, link):
        self.uuid = uuid
        self.artist = artist
        self.title = title
        self.year = year
        self.link = link

    def __repr__(self):
        a = [
            'uuid: ' + self.uuid,
            'artist: ' + self.artist,
            'title: ' + self.title,
            'year: ' + self.year,
            'link: ' + self.link
        ]
        return ', '.join(a)
