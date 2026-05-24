# ADR-0001: Split backend monoliths into focused modules

- **Status:** Accepted
- **Date:** 2026-05-24
- **Owner:** Batman
- **Envelope:** `build_20260524_000601_d47f2c`

## Context

Three files have grown beyond maintainability thresholds and mix unrelated concerns:

- **`backend/app/temporal/activities.py`** (948 LOC)
  - Contains 18 activity functions spanning repo health analysis, README generation, PR creation, portfolio scanning, and profile management.
  - No internal organization; activities from all workflow phases (2, 4, 5, 6, 9, 13, 17, 18, 19) sit side-by-side.

- **`backend/app/api/routes.py`** (304 LOC)
  - Contains 13 FastAPI routes across health checks, auth, repo CRUD, garden workflows, task/PR commits, and portfolio studio.
  - Mixes global utilities (`get_temporal_client`, `get_current_token`) with route handlers.

- **`frontend/src/components/dashboard/repo-detail-sheet.tsx`** (439 LOC)
  - Monolithic Sheet component orchestrating health display, issues, draft proposal, and action buttons.
  - Embeds tight component logic (`DraftProposalSection`) that should be extractable.

Current import style:
- `from app.temporal.activities import activity_name` (works because all activities are top-level module exports)
- `router` from `app.api.routes` (no aggregate)
- React component island with no extracted hooks

## Decision

### 1) Split `backend/app/temporal/activities.py`

Refactor into a package with per-concern modules:

```
backend/app/temporal/
├── __init__.py              # Re-export all activity names (backwards compat)
├── activities/
│   ├── __init__.py
│   ├── analysis.py          # Health & activity analysis (phases 4, 5, 9)
│   ├── github.py            # PR/repo operations (phases 5, 6, 17)
│   ├── generation.py        # README & doc generation (phases 6, 13)
│   ├── persistence.py       # Status + DB writes (phases 18, greeting phase 2)
│   └── portfolio.py         # Portfolio scanning & profile ops (phases 19)
```

**File allocation:**

- **`analysis.py`** (~220 LOC target)
  - `say_hello` (Phase 2: line 34–39)
  - `analyze_repo_health` (Phase 4: lines 144–180)
  - `analyze_codebase_activity` (if extracted; currently inlined in workflows) — stub for future
  - `deep_scan_repo` (Phase 9: lines 272–276)
  - Helper: `_analyze_repo`, `_build_file_tree`, `_read_high_value_files`, `_deep_scan`

- **`github.py`** (~240 LOC target)
  - `fetch_repo_list_activity` (Phase 5: lines 154–164)
  - `fetch_repos_extended_activity` (Phase 19: lines 795–799)
  - `sync_pr_status_activity` (Phase 17: lines 638–657)
  - `create_pull_request_activity` (Phase 6: lines 404–422)
  - `create_docs_pull_request_activity` (Phase 13: lines 536–546)
  - `create_or_update_profile_repo_activity` (Phase 19: lines 939–948)
  - Helpers: `_create_pull_request`, `_create_docs_pull_request`, `_create_or_update_profile_repo`, `_fetch_repos_extended`

- **`generation.py`** (~200 LOC target)
  - `generate_readme_activity` (Phase 6: lines 309–313)
  - `generate_deep_readme_activity` (Phase 6: lines 315–326)
  - `generate_doc_activity` (Phase 12: lines 427–442)
  - `generate_profile_readme_activity` (Phase 19: lines 801–812)

- **`persistence.py`** (~120 LOC target)
  - `save_draft_proposal_activity` (Phase 13: lines 552–571)
  - `set_repo_status_activity` (Phase 18: lines 577–586)

- **`portfolio.py`** (~180 LOC target)
  - `portfolio_deep_scan_activity` (Phase 19: lines 768–772)
  - Helper: `_portfolio_deep_scan`, `_extract_frameworks`, `_FRAMEWORK_MAP`, `_PORTFOLIO_DEP_FILES`

**Backwards compatibility:** `__init__.py` re-exports all activity names so existing imports (`from app.temporal.activities import analyze_repo_health`) continue to work without caller changes.

### 2) Split `backend/app/api/routes.py`

Refactor into a package with per-resource modules:

```
backend/app/api/
├── __init__.py              # Aggregate routes into api_router
├── routes/
│   ├── __init__.py          # Define api_router; import & include all sub-routers
│   ├── health.py            # /health
│   ├── auth.py              # /auth/exchange
│   ├── repos.py             # /repos, /analyze/{repo_id}, /fix/{repo_id}, /sync, /repos/{repo_id}/commit
│   ├── garden.py            # /garden/start, /garden/status/{workflow_id}
│   └── portfolio.py         # /portfolio/generate, /portfolio/status/{workflow_id}, /portfolio/publish
```

**File allocation:**

- **`health.py`** (~15 LOC)
  - `@router.get("/health")` (lines 32–33)

- **`auth.py`** (~25 LOC)
  - `@router.post("/auth/exchange")` (lines 36–42)

- **`repos.py`** (~140 LOC)
  - `@router.get("/repos")` (lines 45–73)
  - `@router.post("/analyze/{repo_id}")` (lines 76–89)
  - `@router.post("/fix/{repo_id}")` (lines 125–145)
  - `@router.post("/sync")` (lines 152–155)
  - `@router.post("/repos/{repo_id}/commit")` (lines 161–206)
  - Shared dependency: `get_current_token`, `get_temporal_client`

- **`garden.py`** (~50 LOC)
  - `@router.post("/garden/start")` (lines 92–103)
  - `@router.get("/garden/status/{workflow_id}")` (lines 106–116)

- **`portfolio.py`** (~80 LOC)
  - `@router.post("/portfolio/generate")` (lines 212–272)
  - `@router.get("/portfolio/status/{workflow_id}")` (lines 275–287)
  - `@router.post("/portfolio/publish")` (lines 290–304)

**Shared module:** Extract `get_current_token` and `get_temporal_client` into a new `backend/app/api/deps.py` so each route file can import them.

**Main integration:** In `backend/app/main.py`, replace:
```python
from app.api.routes import router
app.include_router(router)
```

with:
```python
from app.api.routes import api_router
app.include_router(api_router)
```

### 3) Split `frontend/src/components/dashboard/repo-detail-sheet.tsx`

Extract state management and sub-components:

```
frontend/src/components/dashboard/
├── repo-detail-sheet.tsx    # Orchestration, layout (~120 LOC target)
├── draft-proposal-editor.tsx # Preview/edit toggle, file selection, save (~200 LOC target)

frontend/src/hooks/
├── use-draft-proposal.ts    # useDraftProposal hook (~80 LOC)
```

**File allocation:**

- **`repo-detail-sheet.tsx`** (refactored to ~120 LOC)
  - Orchestration component
  - Props: `repo`, `open`, `onClose`
  - Internal state: `hasDraft`, `isDrafting`
  - Delegates: `DraftProposalEditor` (now a separate component), action buttons
  - Imports: `useGardener()` from existing hook, new `useGardenerDraft()` from `use-draft-proposal.ts`

- **`draft-proposal-editor.tsx`** (new, ~200 LOC)
  - Extracted from current `DraftProposalSection` (lines ~180–340)
  - Props: `repoId`, `draft`, `onClose`
  - Internal state: `selectedFiles`, `editedContents`, `previewMode`
  - Uses `useGardenerDraft()` for mutations
  - File selection UI, preview toggle, markdown render, save button

- **`use-draft-proposal.ts`** (new hook, ~80 LOC)
  - Encapsulates draft mutation logic currently inline in Sheet
  - Exports: `useGardenerDraft()` → `{ commit, isCommitting }`
  - Uses existing `useGardener().commitDocs`

## Consequences

- **Pros**
  - Each module ≤250 LOC; single responsibility.
  - Clear signal for where to add similar functionality (e.g., new activity type goes to relevant submodule).
  - No behavior changes; full backwards compatibility via re-exports.
  - Easier code review and testing per concern.
  
- **Cons**
  - Additional import paths; developers must know the structure.
  - Circular imports unlikely but must watch when extracting shared logic.
  - Component extraction increases fragment count (more imports in Sheet).

## Implementation notes

1. **Create package structure** with `__init__.py` files.
2. **Copy functions by concern** into new modules; run linter.
3. **Update all imports**:
   - Backend activities: test `from app.temporal.activities import analyze_repo_health` still works.
   - Backend routes: test `app.include_router(api_router)` resolves correctly in `main.py`.
   - Frontend: test `import { RepoDetailSheet } from "..."; import { DraftProposalEditor } from "..."`
4. **Remove original files** once imports verified.
5. **docker compose up** to boot both services cleanly.
6. **npm test -- --run** (should be no-op today; verify no new errors).

## Alternatives considered

- **Keep monoliths + use type hints + better docstrings**
  - Rejected: does not address navigation or cognitive load for adding similar features; LOC thresholds remain.

- **Single package `activities/` with one catch-all file**
  - Rejected: same monolith problem; defeats refactoring purpose.

- **Split by workflow (Greeting, Analysis, Janitor, etc.) instead of function type**
  - Rejected: functions span multiple workflows (e.g., `create_docs_pull_request_activity` used by Janitor + Portfolio).
