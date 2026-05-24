# Changelog

All notable changes to Git-Repo-Organizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Backend activity modules**: Split monolithic `backend/app/temporal/activities.py` (948 LOC) into focused concern-based modules:
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
- **HTTPException hoisting**: Moved `HTTPException` to module-level imports in `backend/app/api/routes/auth.py` for proper error handling.
- **Activity signature restoration**: Ensured `getAllTaskNotes(taskIds, perTask)` function signature is correct across refactored modules.

## [0.1.0] - 2026-05-23

- Initial release. Monolithic backend (single `activities.py` file + single `routes.py` file). Full Docker Compose stack with Temporal, Postgres, FastAPI, and Next.js.
