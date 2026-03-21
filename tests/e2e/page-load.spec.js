import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Page load', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('loading spinner is hidden and main content is visible', async ({ page }) => {
    const loading = page.locator('.loading');
    await expect(loading).toHaveCSS('display', 'none');

    const main = page.locator('.main-content');
    await expect(main).toHaveCSS('display', 'block');
  });

  test('song table has rows', async ({ page }) => {
    const rows = page.getByTestId('song-table').locator('tr');
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test('totalCount is greater than zero', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);
    expect(total).toBeGreaterThan(0);
  });
});
