import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const SW_PATH = path.resolve('dist/service_worker.js');
const SONGS_JSON_PATH = path.resolve('dist/songs.json');

// Restore dist files from source so a previous failed run can't poison later runs.
function restoreDistFiles() {
  execSync('python -c "from jamsite.jamsite import copy_static_assets; copy_static_assets()"', {
    cwd: path.resolve('.'),
  });
}

test.describe('Cache busting after deploy', () => {
  test.beforeAll(() => restoreDistFiles());
  test.afterAll(() => restoreDistFiles());
  test('first visit does not trigger auto-reload', async ({ page }) => {
    // Fresh context: no SW, no caches. On first visit the SW installs and
    // calls clients.claim(), firing controllerchange. But hadController is
    // false so no reload should occur.
    await waitForApp(page);

    await page.evaluate(() => { window.__reloadMarker = true; });

    // Wait long enough for a potential spurious reload
    await page.waitForTimeout(2000);

    const marker = await page.evaluate(() => window.__reloadMarker);
    expect(marker).toBe(true);
  });

  test('deploying new SW version cleans old cache and triggers reload', async ({ page }) => {
    // First visit — let the SW install and populate the cache
    await waitForApp(page);

    const originalCache = await page.evaluate(async () => {
      const info = await window.__app.cache.refreshCache();
      return {
        cacheNames: info.cacheNames,
        staticName: info.cacheNames.find(n => n.startsWith('jamsite-static-')),
      };
    });
    expect(originalCache.staticName).toBeDefined();

    // Reload so the page starts with an active controller.
    // The hadController flag is captured at page load — it's only true
    // when the page already has a SW controller when it loads.
    await page.reload();
    await page.waitForFunction(() => typeof window.__app === 'object');

    // Read the SW file and swap in a new cache name to simulate a deploy
    const originalSW = fs.readFileSync(SW_PATH, 'utf-8');
    const testCacheName = 'jamsite-static-test-deploy';

    try {
      const modifiedSW = originalSW.replace(
        /const STATIC_CACHE = '[^']+'/,
        `const STATIC_CACHE = '${testCacheName}'`,
      );
      fs.writeFileSync(SW_PATH, modifiedSW);

      // Clear browser HTTP cache so r.update() fetches the modified script
      // from the server instead of using a heuristically-fresh cached copy.
      const cdp = await page.context().newCDPSession(page);
      await cdp.send('Network.clearBrowserCache');

      // Trigger SW update check — the new SW will install (skipWaiting),
      // activate (clean old caches, clients.claim), controllerchange fires,
      // and hadController is true so the page auto-reloads.
      // Set up the load listener BEFORE triggering the update to avoid races.
      const reloadPromise = page.waitForEvent('load', { timeout: 10_000 });
      await page.evaluate(() =>
        navigator.serviceWorker.getRegistration().then(r => r.update()),
      );
      await reloadPromise;

      // Wait for the app to initialize after reload
      await page.waitForFunction(
        () => typeof window.__app === 'object',
        { timeout: 10_000 },
      );

      // Verify old cache was cleaned and new cache is active
      const newCache = await page.evaluate(async () => {
        const info = await window.__app.cache.refreshCache();
        return {
          cacheNames: info.cacheNames,
          staticCount: info.staticCount,
        };
      });

      expect(newCache.cacheNames).not.toContain(originalCache.staticName);
      expect(newCache.cacheNames).toContain(testCacheName);
      expect(newCache.staticCount).toBeGreaterThan(0);
    } finally {
      // Restore original SW so other tests aren't affected
      fs.writeFileSync(SW_PATH, originalSW);
    }
  });

  test('sync worker re-downloads PDF when hash changes', async ({ page }) => {
    await waitForApp(page);

    // Pick the first song from the real songs.json for a fast single-song sync
    const originalSongsJson = fs.readFileSync(SONGS_JSON_PATH, 'utf-8');
    const allSongs = JSON.parse(originalSongsJson);
    const testSong = allSongs[0];

    try {
      // Replace songs.json with just our test song so sync is fast
      fs.writeFileSync(SONGS_JSON_PATH, JSON.stringify([testSong]));

      // Start the sync worker and wait for it to finish
      await page.evaluate(() => {
        window.__app.sync.state = 'SYNCING';
        // Access the sync worker via the global reference set in index.html
        window.__app.syncWorker.postMessage({ type: 'START' });
      });
      await page.waitForFunction(
        () => window.__app.sync.state === 'SYNCED',
        { timeout: 15_000 },
      );

      // Verify the PDF is cached with the original hash
      const cachedHash = await page.evaluate(async (uuid) => {
        const cache = await caches.open('pdf-cache');
        const resp = await cache.match(`/pdfs/${uuid}`);
        return resp?.headers.get('X-File-Hash');
      }, testSong.uuid);
      expect(cachedHash).toBe(testSong.hash);

      // Change the hash in songs.json to simulate a new version of the PDF
      const fakeHash = 'aaaa' + testSong.hash.slice(4);
      fs.writeFileSync(
        SONGS_JSON_PATH,
        JSON.stringify([{ ...testSong, hash: fakeHash }]),
      );

      // Clear the browser HTTP cache so the sync worker's fetch of
      // songs.json hits the server and picks up the modified file.
      const cdp = await page.context().newCDPSession(page);
      await cdp.send('Network.clearBrowserCache');

      // Trigger a re-sync — the worker detects the hash mismatch and
      // re-downloads the PDF, stamping it with the new hash.
      // Reset the observable state before sending SYNC to avoid a race
      // where waitForFunction resolves immediately on the stale value.
      await page.evaluate(() => {
        window.__app.sync.state = 'SYNCING';
        window.__app.syncWorker.postMessage({ type: 'SYNC' });
      });
      await page.waitForFunction(
        () => window.__app.sync.state === 'SYNCED',
        { timeout: 15_000 },
      );

      // Verify the cached PDF now has the updated hash
      const updatedHash = await page.evaluate(async (uuid) => {
        const cache = await caches.open('pdf-cache');
        const resp = await cache.match(`/pdfs/${uuid}`);
        return resp?.headers.get('X-File-Hash');
      }, testSong.uuid);
      expect(updatedHash).toBe(fakeHash);
    } finally {
      fs.writeFileSync(SONGS_JSON_PATH, originalSongsJson);
    }
  });

  test('CDN dependency survives deploy (offline after cache bust)', async ({ page }) => {
    // Verify that all scripts needed by loadResources() are in
    // STATIC_FILES so the app works offline after a deploy cache bust.

    // First visit — SW installs and populates the static cache
    await waitForApp(page);

    // Simulate a deploy: create a new cache with only STATIC_FILES
    // (mimicking what caches.addAll does in the SW install handler),
    // then delete the old cache (mimicking the SW activate handler).
    await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      const swResp = await fetch(reg.active.scriptURL);
      const swText = await swResp.text();

      const cacheMatch = swText.match(/const STATIC_CACHE = '([^']+)'/);
      const filesMatch = swText.match(/const STATIC_FILES = \[([\s\S]*?)\]/);
      const oldCacheName = cacheMatch[1];
      const files = filesMatch[1].match(/'[^']+'/g).map(s => s.slice(1, -1));

      const newCacheName = 'jamsite-static-test-cdn';
      const newCache = await caches.open(newCacheName);
      const oldCache = await caches.open(oldCacheName);

      // Copy only STATIC_FILES — just like the new SW's install handler
      for (const file of files) {
        const resp = await oldCache.match(file);
        if (resp) await newCache.put(file, resp);
      }

      await caches.delete(oldCacheName);
    });

    // After a deploy, the user visits the page once (online). The SW's
    // network-first handlers cache index.html and songs.json in the new
    // static cache. This is the normal post-deploy flow.
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => typeof window.__app === 'object');

    // Now go offline — the app should work using only what's in the
    // new cache (STATIC_FILES + index.html + songs.json).
    await page.context().setOffline(true);
    await page.reload({ waitUntil: 'load' });

    const appLoaded = await page.evaluate(() => {
      return new Promise(resolve => {
        const check = () => {
          if (typeof window.__app === 'object') return resolve(true);
        };
        check();
        const interval = setInterval(check, 100);
        setTimeout(() => { clearInterval(interval); resolve(false); }, 5000);
      });
    });

    expect(appLoaded).toBe(true);
  });
});
