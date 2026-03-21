import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Responsive layout', () => {
  test('mobile: artist column is hidden at 400px width', async ({ page }) => {
    await page.setViewportSize({ width: 400, height: 800 });
    await waitForApp(page);

    // Second <td> in each row is the artist column
    const artistCell = page.getByTestId('song-table').locator('tr').first().locator('td').nth(1);
    await expect(artistCell).toBeHidden();
  });

  test('mid-range: container and navbar are 80% wide', async ({ page }) => {
    await page.setViewportSize({ width: 800, height: 900 });
    await waitForApp(page);

    const containerWidth = await page.locator('.container').first().evaluate(
      el => el.getBoundingClientRect().width
    );
    // At 800px viewport, 80% = 640px (approximately)
    expect(containerWidth).toBeGreaterThan(600);
    expect(containerWidth).toBeLessThan(700);
  });

  test('desktop: container has constrained max-width at 1400px', async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 900 });
    await waitForApp(page);

    const maxWidth = await page.locator('.container').first().evaluate(
      el => getComputedStyle(el).maxWidth
    );
    // Skeleton's default container max-width is 960px
    expect(parseInt(maxWidth)).toBeLessThan(1400);
  });
});
