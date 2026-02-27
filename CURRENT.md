This repository is for jamsite, my chord chart archive and serving website. It has evolved over the years and it is getting a little messy now and I'd like to fix it up a bit.

# Chord sheet management #

For historical reasons, there are two sources of chord sheets:
- skrul's chord sheets in a google drive folder
- gary's chod sheets in a dropbox

Right now these are being treated separately and only really combined when the files are downloaded and served by the website. The metadata for the chord sheets are stored in a google sheet, each corpus getting a separate tab.

The google sheet is the source of truth for song title, artist name, and year published. It also includes a sortable title and sortable artist name for sorting and search purposes. These metadata are linked back to the pdf file chord sheet using an id, either "gd:<google drive file identifier>" or "dbx:<drop box file identifier>.

Metadata is maintained by hand in the spreadsheet.

There are several tools in the jamsite.py pythong script to do things like download the files from google drive / dropbox to the webserver, as well as sync the contents of the google drive folder / dropbox folder to the spreadsheet. So to add a new chord chart, the process is usually:

1. Add the PDF to the google drive folder (or dropbox)
2. Use jamsite.py to sync the drive to the spreadsheet. The new chord chart is added in a new row of the spreadsheet, and metadata is prepopulated if possible (parsed from the file name)
3. The metadata is fixed in the spreadsheet, if needed. There is a special tab that contains all the unique artists and thier corresponding musicbrainz IDs. If the new song chart is by a new aritsts, I manually go and find the artist in musicbrainz and get the id. I also use this to check the formatting of the artist's name.
4. Use jamsite.py to download the new chord chart to the webserver
5. Use jamsite.py to generate and publish a new version of the site

# The Problems #

There are a few problems with this system:

- I would like to be confident that all the metadata is correct, that the song titles are formatted correctly, that the year is accurate etc.
- Sometimes chord sheets have different versions; different people write up their own sheets and sometimes you get duplicates. My preference is to not allow duplicates unless there is a good reason -- the only reason I can think of is different keys. Currently key is not part of the metadata but it may have to be. Note that sometimes there are duplicates where the different versions are actually different capo positions. This is ok but I usually combine them all into a single multi page PDF when this happens.
- Adding new files is a bit of a chore. Every month we have a jam and people bring new songs, and they link to their PDFs in a googel doc. If you look at /Users/skrul/dev/packeteer/jam_downloader.py there is some code to download the files that are linked in the monthly PDFs. After I do that I folow the process for adding new charts I outlined above.

I just want this to be easy to maintain because when it is not easy I don't maintain it! But I also want to make sure everything his high quality and accurate.
