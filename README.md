# jamsite
A searchable song packet directory!

## Dev Environment Setup

This project is using [poetry](https://python-poetry.org/docs/), see its docs for how to install.

First `git clone` the repo and `cd` into it.

```
cd ~/your/projects/folder/
git clone git@github.com:skrul/jamsite.git
cd jamsite
```

Install the dependencies:
```
poetry install
```

Run the script:
```
poetry run python jamsite.py
```

### Google API credentials
You need the Google API to read [the spreadsheet](https://docs.google.com/spreadsheets/d/1yGF1CY-obfm5QWiVhvvBoN5XYtQe902hs1np6b6G9Ag/edit#gid=0) to populate the data for the site.

You'll need a new Google API project with Sheets and Drive enabled. A quick way to do that is to click on the `Enable the Google Sheets API` button on the [Google Sheets Python Quickstart Guide](https://developers.google.com/sheets/api/quickstart/python)
which will create a new project with a default name of Quickstart with Sheets enabled.

From your new project, search the API library for `Google Drive API` and enable that as well.

Now go to the Credentials tab for your project and click `+ Create Credentials` and select OAuth client ID. For application type, select `Web Application` then add `http://localhost:8080/` as an authorized redirect URI. Once you've created the OAuth client, download the `credentials.json` file and put it in your `jamsite` directory.

### Running the site locally

Before you sync, comment out this code in `jamsite.py` which you don't need.
```
if args.sync:
    drive_service = google_api.auth('drive', 'v3')
    drive_songs = get_songs_from_drive(drive_service)

    #sheets_service = google_api.auth('sheets', 'v4')
    #existing_songs_by_row = read_songs_spreadsheet(sheets_service)
    #sync_to_spreadsheet(sheets_service, drive_songs, existing_songs_by_row)
```

Auth with Google
```
poetry run python jamsite.py --sync
```
(You may see an error that says `This app isn't verified`. Just click on the `Advanced` link towards the bottom of that page, which should expand with some additional text. Click on the `Go to Quickstart (unsafe)` link.)

Build the site
```
poetry run python jamsite.py --generate
```
(You may need to download punkt. Just follow the directions in the error message.)

Serve the site
```
poetry run python jamsite.py --serve
```

Check it all out! http://localhost:8000/jam/

Note that if you make changes, you'll need to run generate again and reload the page to see them!
