# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Git Repo Organizer (aka "GitHub Gardener") is a full-stack AI-powered platform that analyzes GitHub repositories for health issues and auto-generates fixes (READMEs, PRs). It uses Temporal workflows for orchestrating long-running tasks like batch repo analysis and LLM-powered documentation generation.

## Development Commands

### Full Stack (Docker Compose)
```bash
docker-compose up --build        # Start all services
docker-compose down              # Stop all services
```

### Frontend (Next.js + pnpm)
```bash
cd frontend
pnpm install                     # Install dependencies
pnpm dev                         # Dev server at http://localhost:3000
pnpm build                       # Production build
pnpm lint                        # ESLint
```

### Backend (FastAPI + uv)
```bash
cd backend
uv sync                          # Install dependencies
uv run python -m app.main        # API server at http://localhost:8000
uv run python -m app.temporal.worker  # Temporal worker (gardener-queue)
```

### Database Migrations (Alembic)
```bash
cd backend
uv run alembic upgrade head      # Run migrations
uv run alembic revision --autogenerate -m "description"  # New migration
```

### Local Dev Without Docker (3 terminals)
1. `temporal server start-dev` — Temporal at :7233, UI at :8233
2. `cd backend && uv run python -m app.temporal.worker`
3. `cd backend && uv run python -m app.main`

## Architecture

### Services (docker-compose.yml)
- **PostgreSQL** (:5432) — persistence for users, repos, analysis results
- **Temporal Server** (:7233) — workflow orchestration engine
- **Temporal UI** (:8233) — workflow monitoring dashboard
- **Backend API** (:8000) — FastAPI, handles auth + routes + DB
- **Temporal Worker** — executes workflow activities (same Docker image as backend, different entrypoint)
- **Frontend** (:3000) — Next.js dashboard

### Backend Structure (`backend/app/`)
- `main.py` — FastAPI app, CORS config, Alembic migration on startup
- `api/routes.py` — All API endpoints in a single router
- `core/config.py` — Pydantic Settings class, all env vars defined here
- `db/models.py` — SQLModel ORM models (User, Repository, AnalysisResult)
- `db/crud.py` — Upsert-pattern CRUD functions
- `db/session.py` — SQLModel engine + session factory
- `schemas/` — Pydantic request/response models (separate from DB models)
- `services/github_service.py` — PyGithub wrapper (sync, use `asyncio.to_thread()`)
- `services/llm_service.py` — LiteLLM wrapper for README generation
- `temporal/workflows.py` — All Temporal workflow definitions
- `temporal/activities.py` — All Temporal activity implementations
- `temporal/worker.py` — Worker startup, registers workflows + activities on `gardener-queue`

### Frontend Structure (`frontend/src/`)
- `app/` — Next.js App Router pages (landing, callback, dashboard, repo/[repoId], portfolio)
- `components/dashboard/` — Dashboard-specific components (sidebar, header, repo-grid)
- `components/landing/` — Landing page sections
- `components/ui/` — Radix UI-based shadcn/ui primitives
- `services/api.ts` — Axios client with auth interceptor (token from localStorage)
- `types/api.ts` — TypeScript interfaces matching backend Pydantic schemas
- `hooks/use-gardener.ts` — React Query hooks for all API interactions

### Key Patterns
- **Authentication**: GitHub OAuth → token stored in localStorage → Axios interceptor injects Bearer header → 401 clears token and redirects to `/`
- **Temporal workflows**: Parent-child pattern for batch operations. Parent spawns child workflows per repo. Status exposed via Temporal queries, polled by frontend every 2s with React Query.
- **Database upserts**: All CRUD functions use check-then-insert-or-update pattern in a single transaction
- **PyGithub is sync**: All GitHub API calls wrapped with `asyncio.to_thread()` to avoid blocking the async FastAPI event loop
- **LLM integration**: LiteLLM provides OpenAI-compatible interface; model, API key, and base URL are all configurable via env vars

### Temporal Workflows
| Workflow | Purpose | Key Activities |
|----------|---------|----------------|
| `AnalysisWorkflow` | Single repo health check (README, staleness, description) | `analyze_repo_health` |
| `BatchGardeningWorkflow` | Parallel analysis of N repos via child workflows | `fetch_repo_list_activity` → child `AnalysisWorkflow`s |
| `JanitorWorkflow` | Generate README via LLM and open PR on `gardener/readme-fix` branch | `get_repo_context_activity` → `generate_readme_activity` → `create_pull_request_activity` |
| `PortfolioWorkflow` | Generate developer portfolio page | Multi-stage: scan → analyze → generate |

### Health Score Calculation
Starts at 100, deductions: no README (-20), stale >6 months (-30), no description (-10).

## Environment Variables

Copy `.env.example` to `.env`. Key variables:
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — GitHub OAuth App credentials
- `LITELLM_API_KEY` / `LITELLM_API_BASE` / `LLM_MODEL` — LLM provider config
- `NEXT_PUBLIC_API_BASE_URL` — Frontend → Backend URL (default: `http://localhost:8000`)
- `NEXT_PUBLIC_GITHUB_CLIENT_ID` — Used by frontend for OAuth redirect
- `DATABASE_URL` — PostgreSQL connection string (auto-set in docker-compose)
- `TEMPORAL_ADDRESS` — Temporal server address (auto-set in docker-compose)

## Tech Stack Quick Reference
- **Backend**: Python 3.12, FastAPI, SQLModel, Temporal SDK, LiteLLM, PyGithub, Alembic, uv
- **Frontend**: TypeScript, Next.js 16, React 19, Radix UI (shadcn/ui), Tailwind CSS 4, TanStack React Query, Axios, Framer Motion
- **Infra**: Docker Compose, PostgreSQL 16, Temporal Server
