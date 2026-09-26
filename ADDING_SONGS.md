# Adding new songs

A runbook for bringing new chord charts into the site. Songs arrive from three places, and they all end up as rows in the Google Sheet (the source of truth for title, artist, year and key) pointing at a PDF in Google Drive or Dropbox.

| Source | Where it lives | How it gets in |
|---|---|---|
| Your LaTeX charts | `~/dev/songs` repo | `songs.py` builds PDFs and uploads them to the Drive folder |
| Gary's charts | Gary's Dropbox, `/Lyrics + Chords` | Gary adds them; sync picks them up |
| Everyone else's charts from the monthly jam | Linked from the jam's Google Doc | Download with packeteer, triage, upload to the Drive folder |

Run everything below from the jamsite repo unless noted. All commands start with `uv run jamsite`.

## 1. Upload your LaTeX charts

In `~/dev/songs`:

```
uv run python songs.py status       # what's new or edited since the last upload
uv run python songs.py upload-all   # build and upload them
```

Transposed versions get the key in the Drive filename, e.g. `Solar Power - Lorde (2021) [C].pdf`, and sync copies it into the sheet's key column. The original version has no key in its filename, so it shows up in step 5 as a duplicate: use `k`, press Enter to keep the transposed version's key, and type the original's (it's the `key={...}` in the `.tex` file).

## 2. Sync the sheet

```
uv run jamsite --sync
```

This adds a row for every new file in Drive and Dropbox, marks rows deleted when their file disappears, and fills in playlist entries that match exactly.

**New artists.** For each artist not in the `artists` tab, it looks them up on MusicBrainz and asks you to accept the match:

- `Y`: accept. If the MusicBrainz spelling differs, it asks whether to use it (`m`) or keep yours (`k`).
- `n`: no match (musicals, "Traditional", songwriter teams). Type the sort name yourself, e.g. `Rocky Horror Picture Show, The`. The artist is still saved to the `artists` tab.

Check that the name matches an existing artist. "Go-Go's" vs "The Go-Go's" creates two artists.

**What sync ignores in Dropbox.** Files named `... conflicted copy ...` (Dropbox sync conflicts) and `PHA <Month> <Year>` (whole-jam packets). See `DROPBOX_IGNORE_RE` in `jamsite/store.py`.

## 3. Download the PDFs locally

```
uv run jamsite --download
```

The next steps open PDFs from `/Volumes/songs/data`, so they need to be here. Dropbox Word/RTF files are converted with Gotenberg, which starts in a temporary container automatically (Apple `container`, or Docker if it's running).

## 4. Fill in metadata for Dropbox songs

Dropbox files arrive with only a filename, so they need an artist, title and year:

```
uv run jamsite --fill-metadata
```

For each song it opens the PDF in Preview and a Google search for the year.

- Enter accepts the value in `[brackets]`.
- `-` skips the song (works even when there's a default). It then asks whether to **mark it skip** in the sheet: say yes for junk and duplicates, so they're hidden from the site and you're not asked again.

If MusicBrainz returns a 503 it retries automatically. If the command dies anyway, just re-run it. It only lists songs that are still incomplete.

## 5. Resolve duplicates

```
uv run jamsite --resolve-duplicates
```

Groups songs with the same title and artist and opens them side by side. Answer with:

| Answer | Does |
|---|---|
| `2` | keep #2, mark the rest skip |
| `2,3` | keep #2 and #3, mark the rest skip, then ask for a key for each one kept |
| `k` | keep all, ask for a key for each |
| `c` | merge PDFs into one and upload it |
| `s` | leave this group alone for now |

**The house rule:** no duplicates unless they're in different keys. When a song has key variants, *every* row in the group gets a key, including the original (e.g. Lean On Me is C and A). Keys use flats: Bb, Eb, Ab.

Typical cases:

- Your new LaTeX chart vs. an old PDF of the same song: keep the LaTeX one.
- Gary re-uploaded his own chart: keep the newest.
- Gary's copy of a song you already have, same key: keep yours.
- Your LaTeX default + transposed version: `k`, key both.

## 6. Bring in charts from the monthly jam

In `~/dev/packeteer`, download everything linked from the jam's Google Doc:

```
uv run jam_downloader.py "<jam doc URL>" -o charts-YYYY-MM
```

Files are named `NN - Person - NN - Title.pdf`. Gary's charts will already be in his Dropbox and yours in the songs repo, so skip those. For everyone else's:

1. **Check what's already on the site.** Search jamsite (or the sheet) for each title. Filenames drop apostrophes and punctuation, so search loosely ("Shes A Woman" is "She's a Woman"). If it's already there in the same key, skip it.
2. **Copy the new ones to a review folder**, e.g. `~/dev/packeteer/new-for-jamsite/`, renamed to the Drive filename format:

   ```
   Title - Artist (Year).pdf
   ```

   The year in parentheses is required. Sync skips files without it (look for `Skipping ...` in the sync output). For traditional songs, use the year of a well-known recording. For show tunes, credit the songwriters (`Rodgers & Hammerstein`); the sheet already does this for standards.
3. **Upload the folder to the Drive songs folder** (the same folder `JAM_SONGS_FOLDER_ID` in `jamsite/jamsite.py` points to). Dragging the files into Drive in a browser works.
4. **Go back to step 2** (sync), then 3 (download).

## 7. Check

```
uv run jamsite --check
```

Should report no issues. Common ones:

- **Missing files:** PDFs not downloaded yet. Run `--download`.
- **Unknown artists:** an artist missing from the `artists` tab. Add a row: name, MusicBrainz ID (can be blank), MusicBrainz name, sort name.
- **Duplicates:** go back to step 5.

`--check --check-years` also compares every year against MusicBrainz. It takes an hour or more the first time (results are cached in `~/.jamsite_mb_recording_cache.json`). Treat the flags as suggestions: MusicBrainz often has reissue dates or cover versions.

## 8. Deploy

Push first (`deploy.sh` refuses to run with unpushed commits), then:

```
./deploy.sh --songs
```

`--songs` regenerates from the sheet and downloads the new PDFs on the server. Without it, `deploy.sh` only deploys code changes.

## Things to tell people

- **Gary:** Dropbox conflicted copies pile up when several people edit the shared folder. Jamsite ignores them, but he may want to delete them.
- **Contributors:** `Title - Artist (Year).pdf` filenames save a lot of triage work.
