"""
Spreadsheet data validation for jamsite.

Checks: missing fields, year format, duplicates, unknown artists,
file existence, orphaned files, and optional year accuracy via MusicBrainz.
"""

import datetime
import glob
import json
import os
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass, field

from pypdf import PdfWriter, PdfReader

from jamsite.song import Song, normalize_quotes
from jamsite.store import upload_pdf_to_drive


@dataclass
class CheckResult:
    """Collects issues found during validation."""

    missing_fields: list = field(default_factory=list)
    year_format: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    unknown_artists: list = field(default_factory=list)
    missing_files: list = field(default_factory=list)
    orphaned_files: list = field(default_factory=list)
    year_accuracy: list = field(default_factory=list)

    @property
    def total_issues(self):
        return (
            len(self.missing_fields)
            + len(self.year_format)
            + len(self.duplicates)
            + len(self.unknown_artists)
            + len(self.missing_files)
            + len(self.orphaned_files)
            + len(self.year_accuracy)
        )


def _tab_from_uuid(uuid):
    """Determine tab name from uuid prefix."""
    if uuid.startswith("gd:"):
        return "skrul"
    elif uuid.startswith("dbx:"):
        return "gary"
    return "unknown"


_QUOTE_TABLE = str.maketrans({
    "\u2018": "'",  # left single quotation mark
    "\u2019": "'",  # right single quotation mark
    "\u02bc": "'",  # modifier letter apostrophe
    "\u201c": '"',  # left double quotation mark
    "\u201d": '"',  # right double quotation mark
})


def _normalize_for_matching(s):
    """Normalize a string for duplicate matching: lowercase, strip, straighten quotes."""
    return s.lower().strip().translate(_QUOTE_TABLE)


def find_duplicates(songs_by_row):
    """Find duplicate songs (same title+artist, case-insensitive).

    Args:
        songs_by_row: dict mapping row -> Song

    Returns:
        list of (title, artist, entries) tuples where entries is
        [(tab, row, song), ...] for groups with 2+ entries.
        tab is derived from the song's UUID prefix.
    """
    seen_titles = defaultdict(list)
    for row, song in songs_by_row.items():
        if song.deleted or song.skip:
            continue
        key = (_normalize_for_matching(song.title), _normalize_for_matching(song.artist or ""))
        tab = _tab_from_uuid(song.uuid)
        seen_titles[key].append((tab, row, song))

    duplicates = []
    for (title, artist), entries in seen_titles.items():
        if len(entries) > 1:
            # Skip groups where all entries have distinct non-empty keys
            # (different arrangements, not true duplicates)
            keys = [e[2].key for e in entries]
            if all(keys) and len(set(k.lower().strip() for k in keys)) == len(keys):
                continue
            duplicates.append((entries[0][2].title, entries[0][2].artist or "", entries))
    return duplicates


def run_check(songs_by_row, artists_by_name, songs_dir, recording_lookup=None):
    """Run all checks and return a CheckResult.

    Args:
        songs_by_row: dict mapping row -> Song
        artists_by_name: dict mapping lowercased artist name -> Artist
        songs_dir: path to directory containing PDF files
        recording_lookup: optional RecordingLookup instance for year checks
    """
    result = CheckResult()
    current_year = datetime.datetime.now().year

    # Build UUID sets for orphan check
    active_uuids = set()
    inactive_uuids = set()  # deleted or skipped

    for row, song in songs_by_row.items():
        tab = _tab_from_uuid(song.uuid)
        if song.deleted or song.skip:
            inactive_uuids.add(song.uuid)
            continue

        active_uuids.add(song.uuid)

        # 1. Missing fields
        missing = []
        if not song.title or not song.title.strip():
            missing.append("title")
        if not song.year or not song.year.strip():
            missing.append("year")
        if not song.artist or not song.artist.strip():
            missing.append("artist")
        if missing:
            title_str = song.title or "(untitled)"
            artist_str = f' by {song.artist}' if song.artist else ""
            result.missing_fields.append(
                f'  Row {row + 1} ({tab}): "{title_str}"{artist_str}'
                f" — missing {', '.join(missing)}"
            )

        # 2. Year format
        if song.year:
            try:
                year_int = int(song.year)
                if year_int < 1800 or year_int > current_year:
                    result.year_format.append(
                        f'  Row {row + 1} ({tab}): "{song.title}" by {song.artist}'
                        f' — year "{song.year}" is out of range (1800-{current_year})'
                    )
            except ValueError:
                result.year_format.append(
                    f'  Row {row + 1} ({tab}): "{song.title}" by {song.artist}'
                    f' — year "{song.year}" is not valid'
                )

        # 5. File existence
        pdf_path = os.path.join(songs_dir, song.uuid + ".pdf")
        if not os.path.exists(pdf_path):
            title_str = song.title or "(untitled)"
            artist_str = f' "{song.artist}"' if song.artist else ""
            result.missing_files.append(
                f'  {song.uuid} "{title_str}" by{artist_str} — PDF not found'
            )

        # 7. Year accuracy via MusicBrainz (opt-in)
        if recording_lookup and song.title and song.artist and song.year:
            try:
                year_int = int(song.year)
            except ValueError:
                year_int = None
            if year_int is not None:
                mb_year = recording_lookup.get_year(song.title, song.artist)
                if mb_year:
                    try:
                        mb_year_int = int(mb_year)
                        if abs(year_int - mb_year_int) > 1:
                            result.year_accuracy.append(
                                f'  Row {row + 1} ({tab}): "{song.title}" by {song.artist}'
                                f" — spreadsheet: {song.year}, MusicBrainz: {mb_year}"
                            )
                    except ValueError:
                        pass

    # 3. Duplicates
    result.duplicates = find_duplicates(songs_by_row)

    # 4. Unknown artists — collect all unique artists not in artists tab
    artist_usage = defaultdict(int)
    for row, song in songs_by_row.items():
        if song.deleted or song.skip:
            continue
        if song.artist and song.artist.strip() and unicodedata.normalize("NFC", song.artist.strip().lower()) not in artists_by_name:
            artist_usage[song.artist] += 1
    for artist_name, count in sorted(artist_usage.items()):
        result.unknown_artists.append(
            f'  "{artist_name}" — not in artists tab (used by {count} song{"s" if count != 1 else ""})'
        )

    # 6. Orphaned files
    if os.path.isdir(songs_dir):
        for pdf_path in sorted(glob.glob(os.path.join(songs_dir, "*.pdf"))):
            filename = os.path.basename(pdf_path)
            uuid = filename[:-4]  # strip .pdf
            if uuid not in active_uuids and uuid not in inactive_uuids:
                result.orphaned_files.append(
                    f"  {pdf_path} — no matching song in spreadsheet"
                )

    return result


def _format_duplicates(duplicates):
    """Format structured duplicate tuples into display strings."""
    lines = []
    for title, artist, entries in duplicates:
        rows_str = ", ".join(str(row + 1) for _, row, _ in entries)
        artist_str = f" by {artist}" if artist else ""
        lines.append(f'  "{title}"{artist_str} — rows {rows_str}')
    return lines


def print_report(result, total_songs):
    """Print the check report to stdout."""
    duplicate_lines = _format_duplicates(result.duplicates)
    sections = [
        ("Missing Fields", result.missing_fields),
        ("Year Format", result.year_format),
        ("Duplicates", duplicate_lines),
        ("Unknown Artists", result.unknown_artists),
        ("Missing Files", result.missing_files),
        ("Orphaned Files", result.orphaned_files),
        ("Year Accuracy (MusicBrainz)", result.year_accuracy),
    ]

    any_issues = False
    for title, items in sections:
        if items:
            any_issues = True
            print(f"\n=== {title} ===")
            for item in items:
                print(item)

    if not any_issues:
        print("No issues found.")

    print(
        f"\nSummary: {result.total_issues} issue{'s' if result.total_issues != 1 else ''}"
        f" across {total_songs} songs"
    )


def _close_preview_docs(paths):
    """Close specific documents in Preview by filename."""
    for path in paths:
        name = os.path.basename(path)
        subprocess.run(
            ["osascript", "-e",
             f'tell application "Preview" to close (every document whose name is "{name}")'],
            capture_output=True,
        )


def _combine_pdfs(pdf_paths):
    """Merge multiple PDFs into one. Returns path to the merged temp file."""
    writer = PdfWriter()
    for path in pdf_paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    writer.write(tmp)
    tmp.close()
    return tmp.name


def resolve_duplicates(duplicate_groups, songs_dir, sheets_service, spreadsheet_id,
                       drive_service=None, folder_id=None):
    """Interactively resolve duplicate songs.

    For each duplicate group, opens the PDFs for comparison and prompts
    the user to pick which to keep. Others are marked as skipped in the
    spreadsheet.

    Args:
        duplicate_groups: list of (title, artist, entries) from find_duplicates()
        songs_dir: path to directory containing PDF files
        sheets_service: authenticated Google Sheets API service
        spreadsheet_id: the spreadsheet ID to update
        drive_service: authenticated Google Drive API service (needed for combine)
        folder_id: Drive folder ID to upload combined PDFs into
    """
    total = len(duplicate_groups)
    total_skipped = 0
    total_keys_set = 0
    total_combined = 0

    for i, (title, artist, entries) in enumerate(duplicate_groups):
        artist_str = f' by {artist}' if artist else ""
        print(f'\n=== Duplicate {i + 1}/{total}: "{title}"{artist_str} ===')

        for j, (tab, row, song) in enumerate(entries):
            key_str = f", key: {song.key}" if song.key else ""
            print(
                f"  {j + 1}. Row {row + 1} ({tab})"
                f" — year: {song.year}{key_str}, uuid: {song.uuid}"
            )

        # Open PDFs in Preview with descriptive symlink names
        symlink_dir = tempfile.mkdtemp(prefix="jamsite_dupes_")
        symlink_paths = []
        for j, (tab, row, song) in enumerate(entries):
            pdf_path = os.path.join(songs_dir, song.uuid + ".pdf")
            if os.path.exists(pdf_path):
                link_name = f"{j + 1}_{tab}_row{row + 1}.pdf"
                link_path = os.path.join(symlink_dir, link_name)
                shutil.copy2(pdf_path, link_path)
                symlink_paths.append(link_path)
        if symlink_paths:
            print("\n  Opening PDFs in Preview...")
            subprocess.run(["open", "-a", "Preview"] + symlink_paths)
        else:
            print("\n  (no PDFs found to open)")

        # Prompt user
        valid_nums = "/".join(str(j + 1) for j in range(len(entries)))
        combine_opt = "/c(ombine)" if drive_service and folder_id else ""
        choice = input(f"  Keep which? [{valid_nums}/k(eys){combine_opt}/s(kip)/q(uit)] ").strip().lower()

        updates = []

        if choice == "q":
            print("  Quitting early.")
            if symlink_paths:
                _close_preview_docs(symlink_paths)
                shutil.rmtree(symlink_dir, ignore_errors=True)
            break
        elif choice == "s":
            print("  → Skipped")
        elif choice == "k":
            # Assign keys to distinguish arrangements (PDFs stay open)
            for j, (tab, row, song) in enumerate(entries):
                existing = f" [{song.key}]" if song.key else ""
                key_val = input(f"  Key for {j + 1} (row {row + 1}, {tab}){existing}: ").strip()
                if key_val:
                    updates.append({
                        "range": f"songs!{Song.SPREADSHEET_COLUMNS['key']}{row + 1}",
                        "values": [[key_val]],
                    })
                    total_keys_set += 1
                    print(f"  → Setting key to {key_val}")
        elif choice == "c":
            if not drive_service or not folder_id:
                print("  → Combine not available (no Drive service)")
            else:
                # Ask which songs to combine
                combo_input = input(
                    f"  Which songs to combine? (e.g. 1,2 or 1,2,3): "
                ).strip()
                try:
                    combo_indices = [int(x.strip()) for x in combo_input.split(",")]
                    if any(x < 1 or x > len(entries) for x in combo_indices):
                        raise ValueError("out of range")
                    if len(combo_indices) < 2:
                        raise ValueError("need at least 2")
                except ValueError as e:
                    print(f"  → Invalid selection ({e}), skipping")
                    if symlink_paths:
                        _close_preview_docs(symlink_paths)
                        shutil.rmtree(symlink_dir, ignore_errors=True)
                    continue

                # Ask which song's metadata to use
                meta_input = input(
                    f"  Use metadata from which song? [{'/'.join(str(x) for x in combo_indices)}]: "
                ).strip()
                try:
                    meta_pick = int(meta_input)
                    if meta_pick < 1 or meta_pick > len(entries):
                        raise ValueError("out of range")
                except ValueError:
                    print("  → Invalid metadata choice, skipping")
                    if symlink_paths:
                        _close_preview_docs(symlink_paths)
                        shutil.rmtree(symlink_dir, ignore_errors=True)
                    continue

                meta_song = entries[meta_pick - 1][2]

                # Merge the selected PDFs in order
                pdf_paths = []
                for idx in combo_indices:
                    p = os.path.join(songs_dir, entries[idx - 1][2].uuid + ".pdf")
                    if not os.path.exists(p):
                        print(f"  → PDF not found for {entries[idx - 1][2].uuid}, aborting combine")
                        break
                    pdf_paths.append(p)
                else:
                    # All PDFs found — proceed with merge
                    merged_path = _combine_pdfs(pdf_paths)

                    # Generate Drive filename
                    year_str = f" ({meta_song.year})" if meta_song.year else ""
                    drive_filename = f"{meta_song.title} - {meta_song.artist}{year_str}.pdf"
                    print(f"  → Uploading as: {drive_filename}")

                    # Upload to Drive
                    result = upload_pdf_to_drive(
                        drive_service, merged_path, drive_filename, folder_id
                    )
                    new_file_id = result["id"]
                    new_uuid = f"gd:{new_file_id}"
                    print(f"  → Uploaded: {new_uuid}")

                    # Save merged PDF locally
                    local_pdf_path = os.path.join(songs_dir, new_uuid + ".pdf")
                    shutil.copy2(merged_path, local_pdf_path)
                    os.unlink(merged_path)

                    # Write local metadata
                    local_meta_path = os.path.join(songs_dir, new_uuid + ".json")
                    with open(local_meta_path, "w") as f:
                        json.dump({"hash": result.get("sha1Checksum", "")}, f)

                    # Append new row to spreadsheet
                    new_row = [[
                        new_uuid,
                        meta_song.artist,
                        "",  # artist_sort
                        meta_song.title,
                        "",  # title_sort
                        meta_song.year,
                        "",  # key
                        result.get("webContentLink", ""),
                        result.get("webViewLink", ""),
                        result.get("modifiedTime", ""),
                        "",  # deleted
                    ]]
                    sheets_service.spreadsheets().values().append(
                        spreadsheetId=spreadsheet_id,
                        valueInputOption="RAW",
                        range="songs!A1",
                        body={"values": new_row},
                    ).execute()
                    print(f"  → Added new spreadsheet row")

                    # Mark ALL source songs as skipped
                    for j, (tab, row, song) in enumerate(entries):
                        updates.append({
                            "range": f"songs!{Song.SPREADSHEET_COLUMNS['skip']}{row + 1}",
                            "values": [["x"]],
                        })
                        total_skipped += 1
                        print(f"  → Marking {song.uuid} as skipped")

                    total_combined += 1
        else:
            try:
                pick = int(choice)
                if pick < 1 or pick > len(entries):
                    print("  → Invalid choice, skipping")
                    pick = None
            except ValueError:
                print("  → Invalid choice, skipping")
                pick = None

            # Mark all others as skipped
            if pick is not None:
                for j, (tab, row, song) in enumerate(entries):
                    if j + 1 != pick:
                        updates.append({
                            "range": f"songs!{Song.SPREADSHEET_COLUMNS['skip']}{row + 1}",
                            "values": [["x"]],
                        })
                        total_skipped += 1
                        print(f"  → Marking {song.uuid} as skipped")

        # Close the opened PDFs in Preview
        if symlink_paths:
            _close_preview_docs(symlink_paths)
            shutil.rmtree(symlink_dir, ignore_errors=True)

        if updates:
            sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"valueInputOption": "RAW", "data": updates},
            ).execute()

    parts = []
    if total_skipped:
        parts.append(f"marked {total_skipped} as skipped")
    if total_keys_set:
        parts.append(f"set {total_keys_set} key{'s' if total_keys_set != 1 else ''}")
    if total_combined:
        parts.append(f"combined {total_combined} group{'s' if total_combined != 1 else ''}")
    summary = ", ".join(parts) if parts else "no changes"
    print(f"\nDone: {summary}.")
    return total_skipped


def find_incomplete_songs(sheets_service, spreadsheet_id, sheet):
    """Find songs that have a uuid but are missing artist, title, or year.

    Reads raw sheet values directly (can't use read_songs_spreadsheet which
    filters out incomplete rows).

    Returns:
        list of (row_index, values_dict) where row_index is 0-based and
        values_dict has keys: uuid, artist, title, year.
    """
    result = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet)
        .execute()
    )
    rows = result.get("values", [])
    incomplete = []
    for row_idx, row in enumerate(rows):
        if row_idx == 0:
            continue
        d = defaultdict(lambda: "")
        for i, v in enumerate(row):
            d[i] = v
        uuid = d[0].strip()
        artist = d[1].strip()
        title = d[3].strip()
        year = d[5].strip()
        deleted = d[10].strip().lower() == "x"
        skip = d[11].strip().lower() == "x"
        if not uuid or deleted or skip:
            continue
        if not artist or not title or not year:
            incomplete.append((row_idx, {
                "uuid": uuid,
                "artist": artist,
                "title": title,
                "year": year,
            }))
    return incomplete


def fill_metadata(incomplete_songs, songs_dir, sheets_service, spreadsheet_id, sheet,
                   resolve_artist_sort_fn=None):
    """Interactively fill in missing metadata for incomplete songs.

    For each song, opens the PDF, prompts for artist/title/year, searches
    Google for the year, and updates the spreadsheet.

    Args:
        resolve_artist_sort_fn: optional callback(artist, title) -> sort_name
            that resolves artist_sort via MusicBrainz and updates the artists sheet.
    """
    total = len(incomplete_songs)
    updated = 0

    for i, (row_idx, vals) in enumerate(incomplete_songs):
        uuid = vals["uuid"]
        print(f"\n=== Song {i + 1} of {total}: {uuid} ===")
        if vals["artist"]:
            print(f"  Artist: {vals['artist']}")
        if vals["title"]:
            print(f"  Title: {vals['title']}")
        if vals["year"]:
            print(f"  Year: {vals['year']}")

        # Open PDF in Preview via a temp copy (so we can cleanly close it)
        pdf_path = os.path.join(songs_dir, uuid + ".pdf")
        tmp_dir = None
        tmp_path = None
        if os.path.exists(pdf_path):
            tmp_dir = tempfile.mkdtemp(prefix="jamsite_fill_")
            safe_name = uuid.replace(":", "_") + ".pdf"
            tmp_path = os.path.join(tmp_dir, safe_name)
            shutil.copy2(pdf_path, tmp_path)
            subprocess.run(["open", "-a", "Preview", tmp_path])
        else:
            print(f"  (PDF not found: {pdf_path})")

        # Prompt for artist
        if vals["artist"]:
            artist = input(f"  Artist [{vals['artist']}]: ").strip()
            if not artist:
                artist = vals["artist"]
        else:
            artist = input("  Artist (empty to skip song): ").strip()
            if not artist:
                print("  -> Skipped")
                if tmp_path:
                    _close_preview_docs([tmp_path])
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                continue

        # Prompt for title
        if vals["title"]:
            title = input(f"  Title [{vals['title']}]: ").strip()
            if not title:
                title = vals["title"]
        else:
            title = input("  Title (empty to skip song): ").strip()
            if not title:
                print("  -> Skipped")
                if tmp_path:
                    _close_preview_docs([tmp_path])
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                continue

        # Open Google search for year
        query = urllib.parse.quote(f"{artist} {title} year")
        search_url = f"https://www.google.com/search?q={query}"
        subprocess.run(["open", search_url])

        # Prompt for year
        if vals["year"]:
            year = input(f"  Year [{vals['year']}]: ").strip()
            if not year:
                year = vals["year"]
        else:
            year = input("  Year (empty to skip): ").strip()

        # Normalize quotes to curly style
        artist = normalize_quotes(artist)
        title = normalize_quotes(title)

        # Resolve artist_sort via MusicBrainz
        artist_sort = None
        if resolve_artist_sort_fn and artist:
            artist_sort = resolve_artist_sort_fn(artist, title)

        # Update spreadsheet
        updates = []
        if artist != vals["artist"]:
            updates.append({
                "range": f"{sheet}!{Song.SPREADSHEET_COLUMNS['artist']}{row_idx + 1}",
                "values": [[artist]],
            })
        if artist_sort:
            updates.append({
                "range": f"{sheet}!{Song.SPREADSHEET_COLUMNS['artist_sort']}{row_idx + 1}",
                "values": [[artist_sort]],
            })
        if title != vals["title"]:
            updates.append({
                "range": f"{sheet}!{Song.SPREADSHEET_COLUMNS['title']}{row_idx + 1}",
                "values": [[title]],
            })
        if year and year != vals["year"]:
            updates.append({
                "range": f"{sheet}!{Song.SPREADSHEET_COLUMNS['year']}{row_idx + 1}",
                "values": [[year]],
            })

        if updates:
            sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"valueInputOption": "USER_ENTERED", "data": updates},
            ).execute()
            updated += 1
            print(f"  -> Updated: {artist} - {title} ({year})")
        else:
            print("  -> No changes")

        # Close the PDF
        if tmp_path:
            _close_preview_docs([tmp_path])
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # Check for quit
        next_action = input("  [Enter to continue, q to quit] ").strip().lower()
        if next_action == "q":
            print("  Quitting early.")
            break

    print(f"\nDone: updated {updated} of {total} songs.")
