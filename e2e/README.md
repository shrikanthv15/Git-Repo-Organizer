# Gardener E2E Tests (Playwright)

**Playwright is the ONLY test framework.** All tests live here, organized by user flow — one folder per flow.

## Folders

| Folder | Flow |
|--------|------|
| `tests/auth/` | Login / GitHub token auth |
| `tests/repos/` | Repo listing + selection |
| `tests/analysis/` | Single-repo analysis status + error surfacing (PAN-10) |
| `tests/review/` | Draft-review UI + toasts (PAN-11) |

## Run on your laptop

```bash
# 1. Clone and enter
git clone https://github.com/shrikanthv15/Git-Repo-Organizer.git
cd Git-Repo-Organizer/e2e

# 2. Install (one time)
npm install
npx playwright install chromium

# 3. Start the app (from repo root, in another terminal)
#    Backend:  cd backend && python3 -m uvicorn app.main:app --port 8000
#    Frontend: cd frontend && npm run dev

# 4. Run tests
npx playwright test              # everything
npx playwright test tests/auth   # one flow folder only
npx playwright test tests/analysis

# Point at a different app URL:
E2E_BASE_URL=https://your-app-url npx playwright test
E2E_API_URL=https://your-api-url npx playwright test
```

## Rules

- New tests go in the folder matching their flow. New flow = new folder.
- No pytest, no vitest for new tests. Playwright only.
- Every spec must pass against a running app before its PR merges to `develop`.
