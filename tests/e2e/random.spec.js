import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Random button', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('clicking random shows a single song', async ({ page }) => {
    await page.getByTestId('random-button').click();

    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBe(1);

    // Search input is populated with the song name
    const searchVal = await page.getByTestId('search-input').inputValue();
    expect(searchVal.length).toBeGreaterThan(0);
  });

  test('clicking random again picks a different song (probabilistically)', async ({ page }) => {
    await page.getByTestId('random-button').click();
    const firstName = await page.getByTestId('search-input').inputValue();

    // Click a few times to increase chance of a different selection
    for (let i = 0; i < 5; i++) {
      await page.getByTestId('random-button').click();
    }
    const lastName = await page.getByTestId('search-input').inputValue();

    // With ~2500 songs, it's extremely unlikely to pick the same one 6 times
    expect(lastName).not.toBe(firstName);
  });
});
