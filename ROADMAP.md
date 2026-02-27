# Jamsite Roadmap

## Current State

### What it is
A searchable chord sheet archive served as a static PWA. Songs come from two sources (skrul's Google Drive, Gary's Dropbox), metadata lives in a Google Sheet, and the site is generated/published via the `jamsite.py` CLI.

### How it works today
```
Google Drive / Dropbox (PDF sources)
        |
    jamsite --sync
        |
Google Sheets (metadata: title, artist, year, sort fields, etc.)
        |
    jamsite --download
        |
Local PDF storage (/Volumes/songs/data/)
        |
    jamsite --generate
        |
Static site (dist/) -> Docker/Nginx -> jam.skrul.com
```

### Adding a new song today
1. Add PDF to Google Drive (or Dropbox)
2. `jamsite --sync` to push new file into the spreadsheet
3. Manually fix metadata in the spreadsheet (title, artist, year, sort names)
4. If new artist: manually look up MusicBrainz ID, add to artists tab
5. `jamsite --download` to pull the PDF
6. `jamsite --generate && jamsite --publish`

### Monthly jam workflow (separate repo: packeteer)
- `jam_downloader.py` scrapes a Google Doc for linked PDFs from the monthly jam
- Downloads and converts them (Dropbox links, Google Docs, Drive files)
- `archive_builder.py` can bulk-scan multiple jam docs and build a manifest
- After downloading, new charts go through the full "adding a new song" flow above

---

## Pain Points

1. **Too many manual steps to add songs** - sync, fix metadata, look up artists, download, generate, publish. Friction means the archive falls behind.

2. **Metadata quality is hard to guarantee** - title formatting, accurate years, correct artist names are all hand-maintained in a spreadsheet with no validation.

3. **No duplicate detection** - same song can appear multiple times with no way to flag or reconcile. Key isn't tracked, so it's unclear when duplicates are intentional vs redundant.

4. **Two disconnected corpora** - skrul's Drive and Gary's Dropbox are treated as separate streams that only merge at download time. Separate spreadsheet tabs, separate sync commands.

5. **Monthly jam integration is manual** - jam_downloader exists but the output still needs to be manually triaged and added to the archive.

6. **PDF filenames are opaque IDs** - downloaded files are named by their spreadsheet UUID (e.g. `gd:1a2b3c.pdf`). This works for uniqueness but makes URLs meaningless to humans. You can't tell what song a link points to just by reading it.

---

## Proposed Changes

### Phase 1: Reduce friction, improve metadata quality

- **Add an optional `key` field to song metadata** - useful for distinguishing intentional duplicates (same song in different keys) from redundant ones. Optional because backfilling thousands of songs isn't practical. Note: capo variants are already handled by combining into a single multi-page PDF.

- **Automate MusicBrainz artist lookups** - when syncing a new song with an artist not already in the artists tab, automatically query MusicBrainz for the artist ID. Present results for confirmation rather than requiring manual lookup. The packeteer repo already has `musicbrainz_lookup.py` that could be adapted. Keep this scoped to artists (not every song) since the artist list is smaller and more manageable.

- **Song title validation / normalization** - add lightweight checks: consistent capitalization rules, flag common formatting issues (extra spaces, missing punctuation, etc.). MusicBrainz lookups could also help here -- not to pin down a specific song ID (a single song has many recordings, making that impractical), but as a sanity check: "does a song with roughly this title by this artist exist in MusicBrainz?" If nothing comes back, it's a signal the title or artist might be misspelled. Useful as a warning, not a gate.

- **Add metadata validation at sync time** - enforce rules: title/artist not empty, year is a reasonable number, flag exact duplicate title+artist combinations. Surface issues as warnings rather than silently accepting bad data.

- **Single-command "add song" workflow** - combine sync + download + generate into one operation, or at least make it easy to pipeline. Reduce the 6-step process to 1-2 steps.

- **Human-readable PDF filenames** - rename downloaded PDFs to something like `artist-title.pdf` (slugified) instead of raw UUIDs. This makes URLs readable and shareable. The UUID mapping is still maintained in the spreadsheet; the filename just becomes a derived, deterministic value. Needs a migration for existing files.

### Phase 2: Unify the corpora

- **Merge the two spreadsheet tabs into one** - treat all songs as one collection regardless of source. The `uuid` prefix (gd:/dbx:) already distinguishes origin. One tab, one sort order, one view.

- **Unified sync command** - `jamsite --sync` handles both sources in one pass. The sync algorithm can still enumerate each source separately to detect additions/deletions, but writes results to a single sheet. The uuid prefix makes it possible to partition rows by source even in one tab.

### Phase 3: Streamline monthly jam intake

- **Integrate jam_downloader into jamsite** - or at least make it easy to pipe jam_downloader output directly into the jamsite add-song flow. Download from the jam doc, auto-populate metadata, present for review, and add to the archive.

- **Batch review UI** - after downloading new charts from a jam, show a summary of what's new, what looks like a duplicate, what needs metadata fixes. Approve in bulk rather than editing cells one by one.

### Metadata storage: keep Google Sheets (for now)

Google Sheets has real advantages: free editing UI, no data loss concerns, easy to share and inspect. The main downsides (API auth complexity, no built-in validation) can be mitigated by adding validation in the jamsite CLI layer rather than moving to a different store. If this becomes painful later, a local SQLite or JSON store is still an option, but it's not worth the migration cost right now.

### Other ideas (not prioritized)

- **Better search on the site** - fuzzy matching, search by artist, filter by key
- **Show key on the song list** - if the metadata is there, surface it
- **Duplicate flagging in the UI** - mark songs that have multiple versions, let users pick which one to view
- **Track song "source" (who brought it)** - useful for the jam community
