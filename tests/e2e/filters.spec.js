import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Decade filters', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('clicking a decade button activates the filter', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);
    const btn = page.locator('#decade1970s');

    await btn.click();

    await expect(btn).toHaveClass(/button-primary/);
    const filters = await page.evaluate(() => window.__app.filter.activeFilters);
    expect(filters).toContain('1970s');

    await page.waitForFunction(t => window.__app.filter.visibleCount < t, total);
    const visible = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(visible).toBeGreaterThan(0);
  });

  test('clicking an active decade button deactivates it', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);
    const btn = page.locator('#decade1970s');

    await btn.click();
    await page.waitForFunction(t => window.__app.filter.visibleCount < t, total);

    await btn.click();
    await page.waitForFunction(t => window.__app.filter.visibleCount === t, total);

    await expect(btn).not.toHaveClass(/button-primary/);
  });

  test('decade filter combined with search narrows results', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);

    await page.locator('#decade1970s').click();
    await page.waitForFunction(t => window.__app.filter.visibleCount < t, total);
    const decadeOnly = await page.evaluate(() => window.__app.filter.visibleCount);

    await page.getByTestId('search-input').fill('love');
    await page.waitForFunction(d => window.__app.filter.visibleCount < d, decadeOnly);

    const combined = await page.evaluate(() => window.__app.filter.visibleCount);
    expect(combined).toBeGreaterThan(0);
  });

  test('clearing one filter keeps the other active', async ({ page }) => {
    const total = await page.evaluate(() => window.__app.filter.totalCount);

    // Activate decade filter
    await page.locator('#decade1970s').click();
    await page.waitForFunction(t => window.__app.filter.visibleCount < t, total);
    const decadeOnly = await page.evaluate(() => window.__app.filter.visibleCount);

    // Add search
    await page.getByTestId('search-input').fill('love');
    await page.waitForFunction(d => window.__app.filter.visibleCount < d, decadeOnly);

    // Clear search — decade filter should still apply
    await page.getByTestId('search-input').fill('');
    await page.waitForFunction(
      ([d, t]) => {
        const v = window.__app.filter.visibleCount;
        return v === d && v < t;
      },
      [decadeOnly, total]
    );
  });
});
