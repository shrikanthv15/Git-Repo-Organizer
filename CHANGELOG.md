# Changelog

All notable changes to Git-Repo-Organizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Test coverage to 61%** (E2): backend pytest suite expanded from 65 → 104 tests; new files `tests/test_crud.py` (26 tests for all 11 CRUD functions × happy + miss paths), `tests/api/test_routes_repos.py` (16 integration tests for /repos, /analyze, /fix, /sync, /commit + idempotency-hit paths), `tests/api/test_routes_portfolio.py` (7 integration tests for /portfolio/generate, /status, /publish). Frontend Vitest + React Testing Library scaffold (`vitest.config.ts`, `tests/setup.ts`) + 13 tests covering `RepoCard` rendering and the `useDraftProposal` editor-state hook. CI workflow `.github/workflows/test.yml` runs backend (uv + pytest with `--cov-fail-under=60`) + frontend (pnpm typecheck + vitest + build) on every PR + push to main. `Makefile` exposes `make test` / `make test-backend` / `make test-frontend` / `make test-cov` / `make build` / `make typecheck` for the same flow locally.
- **Production guardrails** (E5): three independent guardrails on the
  backend, each with its own typed exception + structlog event stream:
  - **GitHub rate-limit-aware client** (`app/services/github_client.py`):
    wraps PyGithub with pre-flight `rate_limit.core` checks; backs off
    with jitter when `remaining < 100`; raises `GithubRateLimitError`
    (carrying `reset_at`) when exhausted so Temporal activities can
    sleep + retry. All `github_service.py` calls now go through it.
  - **LLM cost cap** (`app/services/llm_service.py`): pre-flight token
    count (via `tiktoken`) + cost estimate (`_PRICE_TABLE` for 7 known
    models + conservative default for unknown); rejects when prompt
    tokens > `LLM_MAX_TOKENS_PER_REQUEST` (default 4000) or estimated
    cost > `LLM_MAX_COST_PER_REQUEST_USD` (default 0.50). FastAPI
    exception handler converts the resulting `LLMCostExceededError` to
    HTTP 400 with `{error, detail, estimated_cost_usd, max_cost_usd,
    prompt_tokens}`. Post-call usage logged via `llm_post_call` event.
  - **Idempotency keys** (`app/services/idempotency.py` + Alembic
    migration 004): mutating endpoints `/garden`, `/fix/{repo_id}`,
    `/portfolio/generate`, `/repos/{repo_id}/commit` accept an
    `Idempotency-Key` header. Same key + same Bearer token within 24h
    returns the previously-issued `workflow_id` (or `pr_url` for
    `/commit`) instead of starting new work. Raw tokens are never
    persisted — only a sha256-truncated fingerprint.
- **Structured logging** (E4, PR #10): backend uses `structlog` with JSON output in prod (toggle via `LOG_FORMAT` env, default `json` in prod / `human` in dev) and `LOG_LEVEL` env. `LoggingMiddleware` binds `request_id` + `user_id` per HTTP request; `temporal_activity_context()` binds `workflow_id`/`activity_name`/`repo_id`/`user_id` per Temporal activity. Frontend gains `app/error.tsx` + `app/global-error.tsx` page-level boundaries and a `lib/logger.ts` wrapper that ships errors to `/api/log`.
- **Frontend split** (E1b, PR #11): `repo-detail-sheet.tsx` (439 LOC) refactored into `repo-detail-sheet.tsx` (241 — orchestration), `components/dashboard/draft-proposal-editor.tsx` (196 — extracted editor), and `hooks/use-draft-proposal.ts` (75 — editor state). External `RepoDetailSheet` props unchanged.
- **Backend activity modules** (E1, PR #9): Split monolithic `backend/app/temporal/activities.py` (948 LOC) into focused concern-based modules:
  - `activities/analysis.py` — repo health analysis, codebase activity scanning
  - `activities/github.py` — PR creation, repo fetching, status synchronization
  - `activities/generation.py` — README and documentation generation
  - `activities/persistence.py` — database writes and status updates
  - `activities/portfolio.py` — portfolio deep-scan and framework detection
- **Backend route modules**: Split monolithic `backend/app/api/routes.py` (304 LOC) into focused resource-based modules:
  - `routes/health.py` — health check endpoint
  - `routes/auth.py` — GitHub OAuth exchange
  - `routes/repos.py` — repository CRUD and analysis endpoints
  - `routes/garden.py` — garden workflow orchestration
  - `routes/portfolio.py` — portfolio generation and publishing
- **Shared dependencies module**: Extracted `get_temporal_client()`, `get_current_token()` into `api/deps.py` for reuse across route modules.
- **Comprehensive test suite**: 26+ tests covering all activities and routes with configurable fixtures (`conftest.py`, `pytest.ini`).

### Changed
- **Backend structure**: Activities and routes now live in packages with per-concern modules instead of monolithic files. Each module ≤250 LOC.
- **Import paths** (backwards compatible): All activity imports (`from app.temporal.activities import analyze_repo_health`) continue to work via re-exports in `__init__.py`.
- **Route registration**: `app/main.py` now imports `api_router` from `app.api.routes` instead of `router`.

### Fixed
- **HTTPException hoisting** (E1): Moved `HTTPException` to module-level imports in `backend/app/api/routes/auth.py` for proper error handling.
- **structlog `merge_contextvars`** (E4): Added missing `structlog.contextvars.merge_contextvars` processor in `backend/app/main.py` — without it, `bind_contextvars()` writes context but the renderer never reads it, so `request_id`/`workflow_id`/etc would never appear in log lines. Whole logging feature was no-op before this fix.
- **Test discovery** (E4): Moved `test_logging.py` from `backend/tests/` to `tests/` so `pytest.ini`'s `testpaths = tests` actually picks it up.

## [0.1.0] - 2026-05-23

- Initial release. Monolithic backend (single `activities.py` file + single `routes.py` file). Full Docker Compose stack with Temporal, Postgres, FastAPI, and Next.js.
