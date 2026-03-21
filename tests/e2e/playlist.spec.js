import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Playlist mode', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('activating a playlist filters songs and locks search', async ({ page }) => {
    // Open side menu
    await page.getByTestId('hamburger').click();
    await expect(page.getByTestId('side-menu')).toHaveClass(/open/);

    // Click the first playlist button
    const playlistBtn = page.locator('[data-playlist]').first();
    const playlistName = await playlistBtn.getAttribute('data-playlist');
    await playlistBtn.click();

    // Search input should be read-only and show playlist name
    const search = page.getByTestId('search-input');
    await expect(search).toHaveAttribute('readonly', '');
    await expect(search).toHaveValue(new RegExp(`Playlist:.*${playlistName}`, 'i'));

    // App state reflects active playlist
    const activePlaylist = await page.evaluate(() => window.__app.filter.activePlaylist);
    expect(activePlaylist).toBe(playlistName);

    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBeGreaterThan(0);

    // Filter chips and random button should be disabled
    const decadeBtn = page.locator('#decade1970s');
    await expect(decadeBtn).toBeDisabled();
    await expect(page.getByTestId('random-button')).toBeDisabled();
  });

  test('clearing playlist restores normal mode', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);

    // Activate playlist
    await page.getByTestId('hamburger').click();
    const playlistBtn = page.locator('[data-playlist]').first();
    await playlistBtn.click();

    // Clear it
    await page.getByTestId('playlist-clear').click();

    const search = page.getByTestId('search-input');
    await expect(search).not.toHaveAttribute('readonly', '');
    await expect(search).toHaveValue('');

    const activePlaylist = await page.evaluate(() => window.__app.filter.activePlaylist);
    expect(activePlaylist).toBeNull();

    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBe(total);
  });
});
