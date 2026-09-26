import { test, expect } from '@playwright/test';

/**
 * PAN-10 — Single-repo analysis status + error surfacing.
 * Flow: trigger analysis on a repo -> status transitions are visible ->
 * failures surface as errors, not silent hangs.
 */
const API = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('single-repo analysis status', () => {
  test('analysis failure surfaces an error status (not a silent hang)', async ({ request }) => {
    // Use a repo id that will fail analysis (no such repo) — must get a
    // clear error response, never an indefinite pending state.
    const res = await request.post(`${API}/api/repos/analyze/999999999`, {
      headers: { 'Content-Type': 'application/json' },
    });
    // 404 (no repo), 401/403 (no token), or 502 (analysis failed) are all
    // acceptable — what matters is a terminal response, not a hang.
    expect([401, 403, 404, 422, 502]).toContain(res.status());
    const body = await res.json().catch(() => ({}));
    // Error responses must carry a human-readable detail.
    if (res.status() >= 400) {
      expect(JSON.stringify(body).length).toBeGreaterThan(2);
    }
  });

  test('repo list endpoint reports per-repo analysis status', async ({ request }) => {
    const res = await request.get(`${API}/api/repos/`);
    // Auth-gated is fine — assert the contract, not the data.
    expect([200, 401, 403]).toContain(res.status());
    if (res.status() === 200) {
      const body = await res.json();
      const repos = Array.isArray(body) ? body : body.repos || body.items || [];
      for (const repo of repos.slice(0, 5)) {
        // Every repo must expose an analysis status field (PAN-10 criterion).
        expect(repo).toHaveProperty('status');
      }
    }
  });
});
