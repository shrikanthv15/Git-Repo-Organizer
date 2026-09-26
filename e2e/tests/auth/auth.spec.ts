import { test, expect } from '@playwright/test';

/**
 * Auth flow: the app gates API access behind a GitHub token.
 * Unauthenticated requests must be rejected with a clear error,
 * never a silent failure or HTML error page.
 */
const API = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('auth flow', () => {
  test('unauthenticated API request is rejected cleanly', async ({ request }) => {
    const res = await request.get(`${API}/api/repos/`);
    expect([401, 403]).toContain(res.status());
    const body = await res.text();
    // Must be JSON error, not an HTML stack trace.
    expect(body.trim().startsWith('{') || body.trim().startsWith('[')).toBeTruthy();
  });

  test('app home page loads without a framework error', async ({ page }) => {
    const res = await page.goto('/');
    expect(res?.status()).toBeLessThan(500);
    const html = await page.content();
    // No Next.js error page.
    expect(html).not.toContain('__next_error__');
    expect(html).not.toContain('Application error');
  });
});
