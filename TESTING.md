# Jamsite Browser Testing

E2E tests using [Playwright Test](https://playwright.dev/). Automated specs live in `tests/e2e/` and run against a local dev server (`http://localhost:8000`).

## Prerequisites

- Node.js installed
- Local server running: `jamsite --serve` (serves at `http://localhost:8000`)
- For broadcast tests: use `jamsite --dev` (starts the broadcast hub)

## Implementation: Test Instrumentation

To make these tests practical with Playwright MCP, add two things to the codebase:

### `data-testid` attributes

Add `data-testid` to key interactive elements in `index.html` so tests can target them reliably via `browser_evaluate` / `browser_run_code` without depending on class names or text content that may change.

Priority elements:
- `data-testid="search-input"` - the search box
- `data-testid="hamburger"` - menu toggle button
- `data-testid="random-button"` - random song button
- `data-testid="side-menu"` - the drawer menu
- `data-testid="offline-toggle"` - offline mode switch
- `data-testid="sync-progress"` - sync progress bar
- `data-testid="filter-badge"` - hamburger badge count
- `data-testid="song-actions-{uuid}"` - per-row action menu trigger
- `data-testid="reset-app"` - reset app button
- Decade/genre chip buttons: `data-testid="decade-{value}"`, `data-testid="genre-{value}"`
- Playlist buttons: `data-testid="playlist-{name}"`

### `window.__app` debug object

Expose a global `window.__app` object that aggregates internal state. This lets Playwright MCP use `browser_evaluate` to directly query app state instead of scraping the DOM or guessing.

```js
window.__app = {
  // Service worker
  sw: {
    registered: false,     // SW registered?
    controller: false,     // SW controlling this page?
    cacheName: null,       // e.g. 'jamsite-static-a1b2c3d4'
  },

  // Caches
  cache: {
    staticCount: 0,        // Number of entries in static cache
    pdfCount: 0,           // Number of entries in pdf-cache
    cacheNames: [],        // All cache names present
  },

  // Broadcast / SSE
  broadcast: {
    connected: false,      // EventSource connected?
    clientId: null,        // Current client ID from server
  },

  // Sync worker
  sync: {
    state: 'STOPPED',     // STOPPED | SYNCING | SYNCED | STOPPING
    progress: { done: 0, total: 0 },
  },

  // Offline preference
  offlineEnabled: false,

  // Search / filter state
  filter: {
    activeDecades: [],
    activeGenres: [],
    activePlaylist: null,
    visibleCount: 0,       // Number of currently visible song rows
    totalCount: 0,         // Total song count
  },
};
```

Each module updates its section as state changes. Tests can then do things like:

```
// Wait for SW to be active
browser_evaluate: "window.__app.sw.controller"

// Check cache was busted after deploy
browser_evaluate: "window.__app.cache.cacheNames"

// Verify SSE is connected before testing broadcast
browser_evaluate: "window.__app.broadcast.connected"

// Check sync progress
browser_evaluate: "window.__app.sync.progress"

// Verify filter state after clicking a decade chip
browser_evaluate: "window.__app.filter.activeDecades"
```

This turns many of the tests below from "poke the DOM and hope" into direct state assertions.

---

## 1. Service Worker & Offline

### 1.1 Service worker registration
- Navigate to the site
- Verify service worker is registered (check `navigator.serviceWorker.controller`)
- Verify static cache exists with expected name pattern `jamsite-static-*`
- Verify all files from `STATIC_FILES` list are present in the cache

### 1.2 Static asset caching (cache-first)
- Load the site once to populate caches
- Go offline (disable network via DevTools or `page.route('**/*', route => route.abort())`)
- Reload the page
- Verify the page loads with all CSS/JS intact (no broken layout, no missing scripts)
- Verify search still works (trie data is cached)

### 1.3 Index.html (network-first with fallback)
- Load the site to cache index.html
- Go offline
- Navigate to `/` - should serve cached version
- Verify the page is fully functional

### 1.4 Index.html - never-cached scenario
- Clear all caches and unregister service worker
- Go offline before SW can install
- Navigate to `/` - should show the minimal offline fallback page ("You are offline")

### 1.5 songs.json (network-first with fallback)
- Load the site to cache songs.json
- Go offline
- Reload - verify song data still loads from cache
- Go back online - verify a fresh fetch is attempted (check network tab)

### 1.6 PDF serving (cache-first via pdf-cache)
- Enable offline mode via the side menu toggle to start the sync worker
- Wait for some PDFs to sync (check progress bar)
- Go offline
- Click a song row to open its PDF
- Verify the PDF loads from `pdf-cache`

### 1.7 PDF cache key format
- After syncing some PDFs, inspect `pdf-cache` entries
- Verify they are keyed by `/pdfs/{uuid}` (not the full URL path)
- Verify both URL formats work: `/songs/{uuid}.pdf` and `/songs/{uuid}/{slug}.pdf`

### 1.8 API requests bypass service worker
- Open `/api/events` (SSE endpoint)
- Verify it is NOT intercepted by the service worker (no cache entry created)
- Verify `/api/health` also bypasses

---

## 2. Cache Busting After Deploy

### 2.1 Static cache version changes on deploy
- Load the site, note the current static cache name (e.g., `jamsite-static-a1b2c3d4`)
- Run `jamsite --generate` (which recomputes the MD5 hash from all static files)
- If any CSS/JS changed, verify the cache name in `dist/service_worker.js` has a new hash
- Reload the page
- Verify the old cache is deleted during SW activation
- Verify the new cache is populated with fresh files

### 2.2 Service worker update triggers page reload
- Load the site (SW installed)
- Deploy a change (modify a CSS/JS file, regenerate)
- Reload - the browser should detect the new SW
- Verify `controllerchange` event fires and the page auto-reloads
- Verify the reload only happens when a previous SW was already active (`hadController` check)

### 2.3 First visit - no reload on initial install
- Clear all browser data (caches, SW registration)
- Navigate to the site fresh
- Verify the page does NOT auto-reload (since `hadController` is false on first install)

### 2.4 songs.json freshness after deploy
- Add/remove a song in the data, regenerate
- Reload the page
- Verify the new song list appears (songs.json is network-first, so it fetches fresh)

### 2.5 PDF hash-based cache invalidation
- With offline sync enabled and some PDFs cached
- Replace a PDF file on disk (same UUID, different content)
- Update the hash in metadata
- Regenerate and reload
- Trigger a sync cycle
- Verify the sync worker re-downloads the PDF (hash mismatch detected)

---

## 3. Send to Room (Broadcast)

### 3.1 SSE connection established
- Open the site
- Verify EventSource connects to `/api/events`
- Verify a `connected` event is received with a `clientId`
- Check console for no SSE errors

### 3.2 Send a song to the room
- Open two browser tabs (Tab A and Tab B)
- Wait for both to establish SSE connections
- In Tab A, click the `...` action menu on a song row
- Click "Share with room"
- Verify Tab A's row gets a brief green flash (`broadcast-sent` class, 1 second)
- Verify Tab B receives a toast notification with the song title and artist

### 3.3 Toast notification behavior
- After receiving a broadcast toast in Tab B:
  - Verify it appears with fade-in animation (`broadcast-toast-visible` class)
  - Verify it shows the correct song title and artist
  - Verify it auto-dismisses after 10 seconds
  - Verify clicking the toast opens the song PDF in a new tab
  - Verify clicking the X button dismisses the toast immediately

### 3.4 SSE reconnection
- Open the site, verify SSE is connected
- Kill/restart the server (or disconnect network briefly)
- Verify EventSource auto-reconnects
- Verify a new `clientId` is assigned
- Verify broadcasts work again after reconnection

### 3.5 Send with no connection
- Open the site
- Disconnect from SSE (kill server or go offline)
- Attempt "Share with room" - should silently no-op (clientId is null)
- Verify no errors in console

---

## 4. General UI

### 4.1 Page load
- Navigate to the site
- Verify loading spinner appears initially
- Verify spinner disappears and `main-content` becomes visible once resources load
- Verify song table is populated with rows

### 4.2 Search
- Type a search term in the search input
- Verify results filter after 150ms debounce
- Verify matching songs are shown, non-matching are hidden
- Verify row striping (`row-odd`) is recalculated for visible rows
- Clear search - verify all songs reappear

### 4.3 Multi-term search (AND semantics)
- Search for "artist songword" (two terms)
- Verify only songs matching BOTH terms appear
- Verify punctuation is stripped from search tokens

### 4.4 Decade filtering
- Open side menu (hamburger button)
- Click a decade chip (e.g., "1970s")
- Verify chip becomes active (blue, `button-primary` class)
- Verify song list filters to only songs from that decade
- Verify filter badge count appears on the hamburger icon
- Click the same chip again to deactivate - verify all songs return

### 4.5 Multiple filter combination
- Activate a decade filter AND type a search term
- Verify results are the intersection (both filters apply)
- Clear one filter - verify the other still applies

### 4.6 Genre filtering
- Open side menu
- If genre chips are present, click one
- Verify songs filter to that genre
- Verify it combines with decade filters and search

### 4.7 Playlist mode
- Open side menu
- Click a playlist button
- Verify search input becomes read-only with text "Playlist: {name}"
- Verify filter chips and random button are disabled
- Verify only songs in the playlist are shown
- Click the playlist button again (or clear) to exit playlist mode
- Verify search input becomes editable again and filters re-enable

### 4.8 Song row interaction - mobile
- Set viewport to mobile width (<550px)
- Verify artist column is hidden
- Verify artist name appears as sub-text within the title cell
- Touch a song row - verify it gets `.selected` class (red background) after 200ms hold
- Verify it navigates to `data-download-link`

### 4.9 Song row interaction - desktop
- Set viewport to desktop width (>550px)
- Verify artist column is visible
- Click a song row - verify it opens `data-view-link` in a new tab

### 4.10 Song actions popover
- Click the `...` button on a song row
- Verify popover appears with "Share with room" and "Share via QR code" options
- Click outside the popover - verify it closes
- Verify the popover doesn't trigger row navigation

### 4.11 QR code sharing
- Click `...` on a song, then "Share via QR code"
- Verify a QR code modal appears
- Verify it encodes the correct song URL

### 4.12 Random button
- Click the random/shuffle button in the navbar
- Verify a random song is selected/highlighted
- Verify it scrolls to the song

### 4.13 Side menu
- Click hamburger to open side menu
- Verify menu slides in from the left (250px wide on desktop, 80%/max 300px on mobile)
- Verify semi-transparent overlay appears behind it
- Click overlay - verify menu closes
- Verify menu contains: offline toggle, decade filters, genre filters, playlists, diagnostics, reset app, external links

### 4.14 Responsive layout
- At >1200px: verify container is capped at 960px
- At 550-1200px: verify container/navbar are 80% wide
- At <550px: verify full-width layout, artist column hidden

### 4.15 Reset app
- Open side menu
- Click "Reset App"
- Verify all caches are cleared
- Verify service worker is unregistered
- Verify page reloads to a clean state

### 4.16 Offline toggle and sync progress
- Open side menu
- Toggle offline mode ON
- Verify sync worker starts (progress bar appears)
- Verify progress updates as PDFs download
- Toggle offline mode OFF
- Verify sync stops and caches are cleared

---

## Running Automated E2E Tests

The test scenarios above marked with automated coverage are implemented as Playwright Test specs in `tests/e2e/`. See below for how to run them.

### One-time setup

```sh
npm install
npx playwright install chromium
```

### Start the server

Generate the site (if you haven't already) and serve it:

```sh
jamsite --generate --cached --serve
```

Or use dev mode (includes broadcast hub + auto-reload of static assets):

```sh
jamsite --generate --cached
jamsite --dev
```

The server runs on `http://localhost:8000`.

### Run tests

```sh
npx playwright test
```

Useful options:

```sh
npx playwright test --ui              # interactive UI mode
npx playwright test search            # run a single spec file
npx playwright test --headed          # watch in a visible browser
npx playwright test --reporter=list   # verbose output
```

### Automated test coverage

| Spec file | Covers |
|-----------|--------|
| `page-load.spec.js` | 4.1 |
| `search.spec.js` | 4.2, 4.3 |
| `filters.spec.js` | 4.4, 4.5 |
| `playlist.spec.js` | 4.7 |
| `song-interaction.spec.js` | 4.9, 4.10 |
| `random.spec.js` | 4.12 |
| `side-menu.spec.js` | 4.13 |
| `responsive.spec.js` | 4.14 |
| `service-worker.spec.js` | 1.1 |
| `cache-busting.spec.js` | 2.1, 2.2, 2.3, 2.5 |
| `broadcast.spec.js` | 3.1 |

### Notes

- The `broadcast.spec.js` test requires `--dev` mode (which starts the broadcast hub). It skips gracefully if the hub isn't available.
- The `service-worker.spec.js` tests require that the service worker has been registered, which happens after the first full page load.
- Tests expect real song data in the generated site — they won't work against an empty `dist/`.
