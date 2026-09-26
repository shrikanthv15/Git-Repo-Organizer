import { test, expect } from '@playwright/test';

/**
 * Repos flow: listing the user's repositories.
 * Contract checks — auth-gated endpoints must respond with a
 * terminal status and a JSON body, never hang.
 */
const API = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('repos flow', () => {
  test('repo list endpoint answers with a terminal status', async ({ request }) => {
    const res = await request.get(`${API}/api/repos/`, { timeout: 15000 });
    expect([200, 401, 403]).toContain(res.status());
  });

  test('repo detail for unknown id is a clean 404, not a 500', async ({ request }) => {
    const res = await request.get(`${API}/api/repos/999999999`, { timeout: 15000 });
    // 401/403 (no token) or 404 (no repo) are fine; 500 means swallowed error.
    expect([401, 403, 404]).toContain(res.status());
  });
});
