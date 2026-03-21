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
});
