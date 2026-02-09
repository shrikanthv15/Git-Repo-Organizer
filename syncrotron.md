# Phase 18 — Syncrotron: 6 UX & Architecture Fixes

## Overview

Six production-readiness fixes addressing state management, performance, editing UX, observability, branding, and batch analysis limits.

---

## Fix 1: State Amnesia (Persistent Drafting State)

**Problem:** When a Janitor workflow was drafting docs, refreshing the page lost the "drafting" spinner because status only lived in React state.

**Solution:** Added a `status` column to the database so the backend persists the workflow stage, and the frontend reads it on every fetch.

### Files Modified

| File | Change |
|------|--------|
| `backend/app/db/models.py` | Added `status` (String, default `"idle"`) and `last_gardener_run_at` (DateTime, nullable) columns to `AnalysisResult` |
| `backend/app/db/crud.py` | Added `set_repo_status()` function and status constants (`STATUS_IDLE`, `STATUS_DRAFTING`, `STATUS_REVIEW_READY`) |
| `backend/app/schemas/analysis.py` | Added `status` and `last_gardener_run_at` fields to `RepoHealth` schema |
| `backend/app/api/routes.py` | Hydrate `status` and `last_gardener_run_at` into API response; reset status to `"idle"` after commit |
| `backend/app/temporal/activities.py` | Added `set_repo_status_activity` Temporal activity |
| `backend/app/temporal/workflows.py` | JanitorWorkflow sets `"drafting_docs"` before starting, `"review_ready"` after saving draft |
| `backend/app/temporal/worker.py` | Registered `set_repo_status_activity` in worker activity list |
| `backend/alembic/versions/003_add_status_and_last_gardener_run.py` | Alembic migration adding the two new columns |
| `frontend/src/types/api.ts` | Added `status` and `last_gardener_run_at` to `RepoHealth` interface |
| `frontend/src/components/dashboard/repo-detail-sheet.tsx` | Combined local + DB status: `isDrafting = localFixStatus === "pending" \|\| dbStatus === "drafting_docs"` |

### Status Lifecycle

```
idle → drafting_docs → review_ready → idle (after commit)
```

- **`drafting_docs`**: Set by JanitorWorkflow Step 0, before LLM generation begins
- **`review_ready`**: Set by JanitorWorkflow after `save_draft_proposal_activity` completes
- **`idle`**: Reset by `POST /repos/{id}/commit` after the PR is created

---

## Fix 2: Excessive Polling (Smart Polling)

**Problem:** `useRepos()` polled `/api/repos` every few seconds unconditionally, causing unnecessary API spam when nothing was happening.

**Solution:** Dynamic `refetchInterval` that only activates when repos are in the `drafting_docs` state.

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/hooks/use-gardener.ts` | Added `staleTime: 60_000` and conditional `refetchInterval` callback to `useRepos()` |

### Logic

```typescript
refetchInterval: (query) => {
    const repos = query.state.data;
    const hasDrafting = repos?.some(
        (r) => r.health?.status === "drafting_docs"
    );
    return hasDrafting ? 3_000 : false;  // 3s poll when drafting, stop otherwise
},
```

- **Idle state**: No automatic polling; data considered fresh for 60 seconds
- **Drafting state**: Polls every 3 seconds to catch workflow completion
- **Transition**: As soon as all repos leave `drafting_docs`, polling stops automatically

---

## Fix 3: Markdown Editor (Editable Draft Review)

**Problem:** The draft proposal preview was read-only. Users couldn't edit generated docs before committing them as a PR.

**Solution:** Replaced the read-only ReactMarkdown display with a split Edit/Preview interface using a textarea, and wired edited contents through to the backend commit endpoint.

### Files Modified

| File | Change |
|------|--------|
| `backend/app/api/routes.py` | Added `edited_contents: dict[str, str] \| None` to `CommitRequest`; apply edits to files before PR creation |
| `frontend/src/services/api.ts` | Updated `commitDocs()` to accept optional `editedContents` parameter |
| `frontend/src/hooks/use-gardener.ts` | Updated `commitDocs` mutation signature to include `editedContents` |
| `frontend/src/components/dashboard/repo-detail-sheet.tsx` | Rewrote `DraftProposalSection` with editable textarea + Edit/Preview toggle; tracks `editedContents` state |

### UX Flow

1. User clicks "Auto-Fix" → Janitor generates draft proposal
2. Draft appears with per-file checkboxes and an **Edit/Preview** toggle button
3. **Edit mode**: Textarea with monospace font for direct content editing
4. **Preview mode**: Rendered markdown (ReactMarkdown) for visual review
5. User clicks "Commit Selected" → `selectedFiles` + `editedContents` sent to backend
6. Backend applies edits on top of the original draft, then creates the PR

---

## Fix 4: "Last Pruned" Timestamp

**Problem:** No visibility into when the Gardener last touched a repo. Users couldn't tell if a repo was recently maintained.

**Solution:** During health analysis, scan recent commits for the Gardener commit signature (`🌿 Gardener:`). Store the timestamp and display it on repo cards.

### Files Modified

| File | Change |
|------|--------|
| `backend/app/temporal/activities.py` | Added Gardener signature detection in `_analyze_repo`: scans last 20 commits for `"🌿 Gardener:"` prefix |
| `backend/app/db/crud.py` | Updated `upsert_analysis_result()` to accept and store `last_gardener_run_at` |
| `backend/app/db/models.py` | Added `last_gardener_run_at` column (covered in Fix 1 migration) |
| `frontend/src/components/dashboard/repo-card.tsx` | Added `Leaf` icon and `timeAgo()` helper; displays "Last Pruned: X ago" when timestamp exists |

### Detection Logic (Backend)

```python
last_gardener_run_at = None
try:
    commits = repo.get_commits()[:20]
    for c in commits:
        msg = c.commit.message or ""
        if msg.startswith("🌿 Gardener:"):
            last_gardener_run_at = c.commit.author.date.isoformat()
            break
except Exception:
    pass
```

### Display (Frontend)

The `timeAgo()` function converts the ISO timestamp into a human-readable relative time (e.g., "2 days ago", "3 hours ago") shown on each repo card next to a leaf icon.

---

## Fix 5: Branding Consistency

**Problem:** Inconsistent naming — "Mission Control" in the header, "Gardener Backend" in the health check.

**Solution:** Unified all user-facing references to **"GitHub Gardener"**.

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/components/dashboard/header.tsx` | Changed `"Mission Control"` → `"GitHub Gardener"` |
| `backend/app/api/routes.py` | Changed health check response from `"Gardener Backend"` → `"GitHub Gardener"` |

---

## Fix 6: Unleash "Analyze All"

**Problem:** Batch analysis was capped at 5 repos due to hardcoded defaults scattered across backend and frontend.

**Solution:** Changed default limit to `0` (meaning "all repos") throughout the stack.

### Files Modified

| File | Change |
|------|--------|
| `backend/app/api/routes.py` | Changed `start_garden` default `limit` parameter from `3` to `0` |
| `backend/app/temporal/activities.py` | Updated `fetch_repo_list_activity` to treat `limit=0` as "fetch all" (no slicing) |
| `frontend/src/services/api.ts` | Changed `startBatchAnalysis` default from `5` to `0` |
| `frontend/src/hooks/use-gardener.ts` | Changed `startBatch` mutation default from `5` to `0` |
| `frontend/src/app/dashboard/page.tsx` | Changed `startBatch.mutate(5)` → `startBatch.mutate(repos?.length ?? 100)` |

### Backend Logic

```python
# In fetch_repo_list_activity:
if limit > 0:
    repos = repos[:limit]
# limit=0 → no slicing → all repos analyzed
```

---

## Summary of All Files Touched

### Backend (8 files)
- `backend/app/db/models.py`
- `backend/app/db/crud.py`
- `backend/app/schemas/analysis.py`
- `backend/app/api/routes.py`
- `backend/app/temporal/activities.py`
- `backend/app/temporal/workflows.py`
- `backend/app/temporal/worker.py`
- `backend/alembic/versions/003_add_status_and_last_gardener_run.py` (new)

### Frontend (6 files)
- `frontend/src/types/api.ts`
- `frontend/src/services/api.ts`
- `frontend/src/hooks/use-gardener.ts`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/components/dashboard/header.tsx`
- `frontend/src/components/dashboard/repo-detail-sheet.tsx`
- `frontend/src/components/dashboard/repo-card.tsx`

### Migration Required
Run `alembic upgrade head` to apply the `003_add_status_and_last_gardener_run` migration before starting the backend.
