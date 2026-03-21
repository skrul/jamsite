import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Service worker', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('service worker is registered and controlling the page', async ({ page }) => {
    const sw = await page.evaluate(() => window.__app.sw);
    expect(sw.controller).toBe(true);
  });

  test('static cache exists with expected name and contains assets', async ({ page }) => {
    const cache = await page.evaluate(() => window.__app.cache.refreshCache());
    expect(cache.staticCount).toBeGreaterThan(0);

    // Cache name is in the cacheNames list and matches the expected pattern
    expect(cache.cacheNames.length).toBeGreaterThan(0);
    const staticCache = cache.cacheNames.find(n => n.startsWith('jamsite-static-'));
    expect(staticCache).toBeDefined();
  });

  test('page works offline after caching', async ({ page }) => {
    // Verify the app loaded normally first
    const totalBefore = await page.evaluate(() => window.__app.filter.totalCount);
    expect(totalBefore).toBeGreaterThan(0);

    // Go offline by blocking all network requests
    await page.route('**/*', route => route.abort());

    // Reload — service worker should serve everything from cache
    await page.reload();
    await page.waitForFunction(() => typeof window.__app === 'object');

    // Main content visible, loading spinner hidden
    await expect(page.locator('.main-content')).toHaveCSS('display', 'block');
    await expect(page.locator('.loading')).toHaveCSS('display', 'none');

    // Songs loaded from cached songs.json
    const totalOffline = await page.evaluate(() => window.__app.filter.totalCount);
    expect(totalOffline).toBeGreaterThan(0);

    // Search still works offline
    await page.getByTestId('search-input').fill('love');
    await page.waitForTimeout(200);
    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBeLessThan(totalOffline);
    expect(visible).toBeGreaterThan(0);
  });

  test('shows offline fallback when caches are empty', async ({ page }) => {
    // Clear all caches (SW is still controlling the page)
    await page.evaluate(async () => {
      const names = await caches.keys();
      await Promise.all(names.map(name => caches.delete(name)));
    });

    // Go offline at the network level so SW fetch() calls fail
    await page.context().setOffline(true);

    // Reload — SW intercepts but has no cached response for /
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Should show the minimal offline fallback page
    await expect(page.locator('body')).toContainText('You are offline');
  });

  // Skipped TESTING.md scenarios:
  // 1.6 - PDF serving (cache-first via pdf-cache): slow, requires real PDF downloads
  // 1.7 - PDF cache key format: slow, requires real PDF downloads

  test('API requests are not cached by the service worker', async ({ page }) => {
    const apiUrls = await page.evaluate(async () => {
      const allUrls = [];
      const names = await caches.keys();
      for (const name of names) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        for (const req of keys) {
          const url = new URL(req.url);
          if (url.pathname.startsWith('/api/')) {
            allUrls.push(url.pathname);
          }
        }
      }
      return allUrls;
    });
    expect(apiUrls).toEqual([]);
  });
});
