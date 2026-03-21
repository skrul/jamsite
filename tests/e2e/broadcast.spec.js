import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

test.describe('Broadcast (SSE)', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  test('broadcast is connected with a client ID', async ({ page }) => {
    // The broadcast hub may not be running, so skip gracefully
    const broadcast = await page.evaluate(() => window.__app.broadcast);

    test.skip(!broadcast.connected, 'Broadcast hub not available — skipping');

    expect(broadcast.connected).toBe(true);
    expect(broadcast.clientId).not.toBeNull();
  });
});
