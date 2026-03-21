import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Search', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('typing a search term filters songs', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);

    await page.getByTestId('search-input').fill('love');
    await page.waitForTimeout(200); // debounce

    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBeLessThan(total);
    expect(visible).toBeGreaterThan(0);
  });

  test('a visible row contains the search term', async ({ page }) => {
    await page.getByTestId('search-input').fill('love');
    await page.waitForTimeout(200);

    const firstVisibleRow = page.getByTestId('song-table').locator('tr:not([style*="display: none"])').first();
    await expect(firstVisibleRow).toContainText(/love/i);
  });

  test('row striping is recalculated after filtering', async ({ page }) => {
    await page.getByTestId('search-input').fill('love');
    await page.waitForTimeout(200);

    const visibleRows = page.getByTestId('song-table').locator('tr:not([style*="display: none"])');
    const count = await visibleRows.count();
    expect(count).toBeGreaterThan(1);

    // Odd-indexed visible rows (0-based) should have row-odd class
    const firstHasOdd = await visibleRows.nth(0).evaluate(el => el.classList.contains('row-odd'));
    const secondHasOdd = await visibleRows.nth(1).evaluate(el => el.classList.contains('row-odd'));
    expect(firstHasOdd).not.toBe(secondHasOdd);
  });

  test('clearing search restores all songs', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);

    await page.getByTestId('search-input').fill('love');
    await page.waitForTimeout(200);

    await page.getByTestId('search-input').fill('');
    await page.waitForTimeout(200);

    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBe(total);
  });

  test('multi-term search applies AND logic', async ({ page }) => {
    await page.getByTestId('search-input').fill('beatles love');
    await page.waitForTimeout(200);

    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBeGreaterThan(0);

    const rows = page.getByTestId('song-table').locator('tr:not([style*="display: none"])');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
      const text = (await rows.nth(i).textContent()).toLowerCase();
      expect(text).toContain('beatles');
      expect(text).toContain('love');
    }
  });

  test('punctuation is stripped from search tokens', async ({ page }) => {
    // "don't" should match as "dont" — same results as without apostrophe
    await page.getByTestId('search-input').fill("don't");
    await page.waitForTimeout(200);
    const withPunct = await page.evaluate(() => window.__app.filter.visibleCount);

    await page.getByTestId('search-input').fill('dont');
    await page.waitForTimeout(200);
    const withoutPunct = await page.evaluate(() => window.__app.filter.visibleCount);

    expect(withPunct).toBe(withoutPunct);
    expect(withPunct).toBeGreaterThan(0);
  });
});
