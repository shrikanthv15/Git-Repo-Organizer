# Phase 17 — Smart Sync & Always-On Analysis

## Files Modified

### Backend
- **`backend/app/temporal/activities.py`** — Added `sync_pr_status_activity`, `_sync_pr_status`, and `_extract_pr_number` functions
- **`backend/app/db/crud.py`** — Added `get_repos_with_pending_pr()` and `clear_pending_fix_for_repo()` CRUD functions
- **`backend/app/api/routes.py`** — Added `POST /api/sync` endpoint; imported `sync_pr_status_activity`

### Frontend
- **`frontend/src/types/api.ts`** — Added `SyncResponse` interface
- **`frontend/src/services/api.ts`** — Added `syncStatus()` API method; imported `SyncResponse` type
- **`frontend/src/hooks/use-gardener.ts`** — Added `syncStatus` mutation with automatic repo cache invalidation on success
- **`frontend/src/app/dashboard/page.tsx`** — Wired `handleSync` handler; passed `onSync`/`isSyncing` props to header
- **`frontend/src/components/dashboard/header.tsx`** — Added "Sync Status" button with `ArrowDownUp` icon between Refresh and Analyze All
- **`frontend/src/components/dashboard/repo-detail-sheet.tsx`** — Unlocked Analyze and Auto-Fix buttons for all repos regardless of health score or PR status

## Logic Implemented

### `sync_pr_status_activity` (Backend)

1. Queries the database for all `AnalysisResult` records where `pending_fix_url` is not null (i.e., repos with tracked open PRs).
2. For each result, extracts the PR number from the stored GitHub URL.
3. Uses the PyGithub API (`repo.get_pull(pr_number)`) to check the actual PR state on GitHub.
4. **If the PR is no longer open** (merged or closed): clears `pending_fix_url` to `None` in the database, releasing the repo back to "idle" state.
5. **If the PR is still open**: no changes are made.
6. Returns the count of repos that were updated.

The endpoint (`POST /api/sync`) calls this activity directly (not through Temporal) for speed, since it's a lightweight check that doesn't need workflow orchestration.

### Always-On Analysis (Frontend)

The "Analyze" button in the repo detail sheet is now **always visible** regardless of:
- Health score (previously hidden when score was 100)
- PR status (previously hidden when a PR was open)

When a repo has already been analyzed, the button text changes to **"Re-Analyze"**. When a PR is open, the fix button text changes to **"Re-Fix Repository"**.

## Status

- The "Analyze" button is now visible and clickable for repos with 100% health scores.
- The "Auto-Fix" button is now visible even when a PR is open (labeled "Re-Fix Repository").
- The "Sync Status" button in the dashboard header allows users to manually check for merged/closed PRs and refresh the dashboard state.
