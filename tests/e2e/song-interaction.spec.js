import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Song interactions', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('clicking the actions toggle opens the popover with expected options', async ({ page }) => {
    const toggle = page.locator('.song-actions-toggle').first();
    await toggle.click();

    const popover = page.locator('.song-actions-popover.open').first();
    await expect(popover).toBeVisible();
    await expect(popover.locator('.share-with-room')).toBeVisible();
    await expect(popover.locator('.share-qr')).toBeVisible();
  });

  test('clicking outside closes the popover', async ({ page }) => {
    const toggle = page.locator('.song-actions-toggle').first();
    await toggle.click();

    await expect(page.locator('.song-actions-popover.open')).toBeVisible();

    // Click outside the popover
    await page.locator('.main-content').click({ position: { x: 10, y: 10 } });

    await expect(page.locator('.song-actions-popover.open')).toHaveCount(0);
  });

  test('clicking a song row opens the PDF in a new tab', async ({ page }) => {
    const firstRow = page.getByTestId('song-table').locator('tr').first();
    const viewLink = await firstRow.getAttribute('data-view-link');

    // Intercept window.open to capture the URL
    const openedUrl = await page.evaluate(() => {
      return new Promise(resolve => {
        const orig = window.open;
        window.open = (url, target) => { resolve(url); window.open = orig; return null; };
        document.querySelector('#songs tr').click();
      });
    });

    expect(openedUrl).toBe(viewLink);
    expect(openedUrl).toMatch(/\.pdf/);
  });
});
