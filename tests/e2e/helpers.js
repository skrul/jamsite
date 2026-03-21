/**
 * Navigate to the app and wait for window.__app to be available.
 */
export async function waitForApp(page) {
  await page.goto('/');
  await page.waitForFunction(() => typeof window.__app === 'object');
}
