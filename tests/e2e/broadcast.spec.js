import { test, expect } from '@playwright/test';
import { waitForApp } from './helpers.js';

/**
 * Wait for the broadcast hub to be connected on a page.
 * Returns the broadcast state or null if not available.
 */
async function waitForBroadcast(page) {
  try {
    await page.waitForFunction(
      () => window.__app && window.__app.broadcast && window.__app.broadcast.connected,
      { timeout: 5000 }
    );
    return await page.evaluate(() => window.__app.broadcast);
  } catch {
    return null;
  }
}

test.describe('Broadcast (SSE)', () => {
  test.beforeEach(async ({ page }) => {
    await waitForApp(page);
  });

  // 3.1 SSE connection established
  test('3.1 SSE connects and receives a client ID', async ({ page }) => {
    const broadcast = await waitForBroadcast(page);
    test.skip(!broadcast, 'Broadcast hub not available');

    expect(broadcast.connected).toBe(true);
    expect(broadcast.clientId).not.toBeNull();
  });

  // 3.5 Send with no connection is a silent no-op
  test('3.5 share with room does not POST when disconnected', async ({ browser }) => {
    // Check the hub is available first
    const probePage = await browser.newPage();
    await waitForApp(probePage);
    const probe = await waitForBroadcast(probePage);
    await probePage.close();
    test.skip(!probe, 'Broadcast hub not available');

    // Create a page that can never establish SSE
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
      // Block SSE before navigating so the connection is never established
      await page.route('**/api/events', route => route.abort());

      // Track all requests to /api/send
      const sendRequests = [];
      page.on('request', req => {
        if (req.url().includes('/api/send')) sendRequests.push(req);
      });

      await waitForApp(page);

      // Verify broadcast is not connected
      const broadcast = await page.evaluate(() => window.__app.broadcast);
      expect(broadcast.connected).toBe(false);

      // Try "Share with room" on the first song
      const firstRow = page.locator('#songs tbody tr').first();
      await firstRow.locator('.song-actions-toggle').click();
      await firstRow.locator('.share-with-room').click();
      await page.waitForTimeout(500);

      // Verify no POST to /api/send was made
      expect(sendRequests).toHaveLength(0);

      // Verify no uncaught errors
      const errors = [];
      page.on('pageerror', err => errors.push(err.message));
      await page.waitForTimeout(200);
      expect(errors).toHaveLength(0);
    } finally {
      await context.close();
    }
  });
});

// Multi-tab tests require the `browser` fixture for separate contexts
test.describe('Broadcast multi-tab', () => {

  // 3.2 Send a song to the room
  test('3.2 sending a song shows toast on the other tab', async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    try {
      await waitForApp(pageA);
      await waitForApp(pageB);

      const broadcastA = await waitForBroadcast(pageA);
      const broadcastB = await waitForBroadcast(pageB);
      test.skip(!broadcastA || !broadcastB, 'Broadcast hub not available');

      // They should have different client IDs
      expect(broadcastA.clientId).not.toBe(broadcastB.clientId);

      // In Tab A: open the action menu on the first song and share
      const firstRow = pageA.locator('#songs tbody tr').first();
      await firstRow.locator('.song-actions-toggle').click();
      await firstRow.locator('.share-with-room').click();

      // Verify Tab A's row gets a brief green flash
      await expect(firstRow).toHaveClass(/broadcast-sent/);
      // ...which goes away after ~1 second
      await expect(firstRow).not.toHaveClass(/broadcast-sent/, { timeout: 3000 });

      // Verify Tab B receives a toast notification
      const toast = pageB.locator('.broadcast-toast').first();
      await expect(toast).toBeVisible({ timeout: 5000 });

      // Verify toast shows the correct song title and artist
      const expectedTitle = await firstRow.locator('.song-title-text').textContent();
      const expectedArtist = await firstRow.locator('td:nth-child(2)').textContent();
      await expect(toast.locator('.broadcast-toast-title')).toHaveText(expectedTitle.trim());
      await expect(toast.locator('.broadcast-toast-artist')).toHaveText(expectedArtist.trim());
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });

  // 3.3 Toast notification behavior — dismiss button
  test('3.3 clicking dismiss button removes the toast', async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    try {
      await waitForApp(pageA);
      await waitForApp(pageB);
      const a = await waitForBroadcast(pageA);
      const b = await waitForBroadcast(pageB);
      test.skip(!a || !b, 'Broadcast hub not available');

      // Send from Tab A
      const firstRow = pageA.locator('#songs tbody tr').first();
      await firstRow.locator('.song-actions-toggle').click();
      await firstRow.locator('.share-with-room').click();

      // Wait for toast on Tab B
      const toast = pageB.locator('.broadcast-toast').first();
      await expect(toast).toBeVisible({ timeout: 5000 });

      // Click the X dismiss button
      await toast.locator('.broadcast-toast-dismiss').click();

      // Toast should disappear (300ms animation)
      await expect(toast).not.toBeVisible({ timeout: 2000 });
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });

  // 3.3 Toast notification behavior — clicking toast opens PDF
  test('3.3 clicking the toast opens the song in the PDF viewer', async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    try {
      await waitForApp(pageA);
      await waitForApp(pageB);
      const a = await waitForBroadcast(pageA);
      const b = await waitForBroadcast(pageB);
      test.skip(!a || !b, 'Broadcast hub not available');

      // Send from Tab A
      const firstRow = pageA.locator('#songs tbody tr').first();
      await firstRow.locator('.song-actions-toggle').click();
      await firstRow.locator('.share-with-room').click();

      // Wait for toast on Tab B
      const toast = pageB.locator('.broadcast-toast').first();
      await expect(toast).toBeVisible({ timeout: 5000 });

      // Click the toast body (not dismiss)
      await toast.locator('.broadcast-toast-content').click();

      // Verify the PDF viewer opens
      await expect(pageB.locator('.pdf-viewer-overlay')).toBeVisible({ timeout: 5000 });

      // Verify the URL changed to a song PDF path
      await expect(pageB).toHaveURL(/\/songs\/.*\.pdf$/);
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });

  // 3.4 SSE reconnection
  test('3.4 EventSource connects after initial failure', async ({ browser }) => {
    // Verify the hub is actually running first
    const probePage = await browser.newPage();
    await waitForApp(probePage);
    const probe = await waitForBroadcast(probePage);
    await probePage.close();
    test.skip(!probe, 'Broadcast hub not available');

    // Create Tab B with SSE initially blocked (simulates outage)
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    try {
      await waitForApp(pageA);
      const a = await waitForBroadcast(pageA);

      // Block SSE on Tab B before load
      await pageB.route('**/api/events', route => route.abort());
      await waitForApp(pageB);

      // Verify Tab B is not connected
      const bState = await pageB.evaluate(() => window.__app.broadcast);
      expect(bState.connected).toBe(false);

      // Unblock SSE — EventSource auto-reconnects on error
      await pageB.unroute('**/api/events');

      // Wait for Tab B to connect (EventSource retries automatically)
      const reconnected = await waitForBroadcast(pageB);
      expect(reconnected).not.toBeNull();
      expect(reconnected.connected).toBe(true);
      expect(reconnected.clientId).not.toBeNull();

      // Verify broadcasts work after reconnection: send from A, receive on B
      const firstRow = pageA.locator('#songs tbody tr').first();
      await firstRow.locator('.song-actions-toggle').click();
      await firstRow.locator('.share-with-room').click();

      const toast = pageB.locator('.broadcast-toast').first();
      await expect(toast).toBeVisible({ timeout: 5000 });
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });
});
