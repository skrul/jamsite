import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Side menu', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('hamburger opens the side menu with expected sections', async ({ page }) => {
    await page.getByTestId('hamburger').click();

    await expect(page.getByTestId('side-menu')).toHaveClass(/open/);
    await expect(page.getByTestId('side-menu-overlay')).toHaveClass(/visible/);

    // Verify menu contains expected sections
    const menu = page.getByTestId('side-menu');
    await expect(menu.locator('.offline-section')).toBeVisible();
    await expect(menu.getByTestId('playlist-buttons')).toBeVisible();
    await expect(menu.getByTestId('reset-app')).toBeVisible();
  });

  test('clicking overlay closes the side menu', async ({ page }) => {
    await page.getByTestId('hamburger').click();
    await expect(page.getByTestId('side-menu')).toHaveClass(/open/);

    await page.getByTestId('side-menu-overlay').click();

    await expect(page.getByTestId('side-menu')).not.toHaveClass(/open/);
    await expect(page.getByTestId('side-menu-overlay')).not.toHaveClass(/visible/);
  });
});
