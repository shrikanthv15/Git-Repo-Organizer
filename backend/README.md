# backend/

FastAPI service + Temporal worker for Git-Repo-Organizer. Python 3.12,
managed via `uv`.

## Run backend alone (no Docker)

```bash
cd backend
uv sync                            # install deps + create .venv
uv run python -m app.main          # API on :8000
uv run python -m app.temporal.worker   # in another terminal: worker on gardener-queue
```

Needs Postgres + Temporal Server running externally. Easiest path is
`docker compose up postgres temporal` from the repo root for just those
services, then run the API + worker locally with auto-reload.

## Tests

Run from the **repo root** (pytest.ini lives there):

```bash
uv --project backend run pytest                 # full suite + coverage
uv --project backend run pytest --no-cov        # faster
uv --project backend run pytest tests/api/      # one folder
```

28 tests currently passing (26 from E1 + 2 from E4 logging).

## Code layout (post-E1 / E4)

```
backend/app/
├── main.py                  # FastAPI app, structlog config, middleware wiring
├── api/
│   ├── deps.py              # shared deps: get_temporal_client, get_current_token
│   └── routes/              # per-domain routers (see routes/README.md)
│       ├── __init__.py      # aggregates into api_router
│       ├── health.py        # GET /health
│       ├── auth.py          # POST /auth/exchange
│       ├── repos.py         # /repos, /analyze, /fix, /sync, /commit
│       ├── garden.py        # /garden/start, /garden/status
│       ├── portfolio.py     # /portfolio/generate, /portfolio/status, /portfolio/publish
│       └── logs.py          # POST /log (frontend error ingestion)
├── core/
│   └── config.py            # Pydantic Settings — all env vars defined here
├── db/
│   ├── models.py            # SQLModel ORM: User, Repository, AnalysisResult
│   ├── crud.py              # upsert-pattern CRUD functions
│   └── session.py           # SQLModel engine + session factory
├── middleware/
│   └── logging.py           # FastAPI middleware binding request_id + user_id to structlog
├── schemas/                 # Pydantic request/response models (separate from DB)
├── services/
│   ├── github_service.py    # PyGithub wrapper (sync, wrap calls in asyncio.to_thread)
│   └── llm_service.py       # LiteLLM wrapper for README generation
└── temporal/
    ├── activities/          # Temporal activities (see activities/README.md)
    │   ├── __init__.py      # re-exports for backward compat
    │   ├── analysis.py
    │   ├── github.py
    │   ├── generation.py
    │   ├── persistence.py
    │   └── portfolio.py
    ├── middleware.py        # temporal_activity_context() — binds workflow_id/etc to structlog
    ├── worker.py            # registers workflows + activities on gardener-queue
    └── workflows.py         # workflow defs: Analysis, BatchGardening, Janitor, Portfolio
```

## How to add a new Temporal workflow

1. **Define activities** in `app/temporal/activities/<domain>.py` (or create a new domain module). Each activity is an `@activity.defn`-decorated async function. Use `temporal_activity_context(...)` at the top of long-running activities to bind context to logs.
2. **Re-export from `activities/__init__.py`** so existing `from app.temporal.activities import …` callers still work.
3. **Define the workflow** in `app/temporal/workflows.py` with `@workflow.defn`. Call activities via `workflow.execute_activity(...)` with retry policy + timeouts.
4. **Register in `worker.py`** in the `workflows=[…]` and `activities=[…]` lists.
5. **Expose via an API route** in `app/api/routes/<domain>.py`: take a request body, look up the Temporal client via `Depends(get_temporal_client)`, call `client.start_workflow(...)`, return `{"workflow_id": <id>}`.

## How to add a new API route

1. Pick the right router file in `app/api/routes/` (or create a new domain `<domain>.py`).
2. Define an `APIRouter()` at the top, decorate handlers with `@router.<method>(<path>)`.
3. If creating a new router file, register it in `app/api/routes/__init__.py` so it gets aggregated into `api_router`.
4. Add a test in `tests/api/test_<domain>.py` covering happy + error paths.

## Logging (E4)

We use `structlog` configured in `main.py`. **Don't use `print()` or `logging.basicConfig` in app code.** To add a log line:

```python
import structlog
logger = structlog.get_logger()
logger.info("event_name", key1="value1", key2=42)
```

In a Temporal activity, wrap the work in `temporal_activity_context()`
to bind `workflow_id`/`activity_name`/`repo_id`/`user_id` for all
nested log calls:

```python
from app.temporal.middleware import temporal_activity_context

@activity.defn
async def my_activity(workflow_id: str, repo_id: int) -> str:
    with temporal_activity_context(workflow_id, "my_activity", repo_id=repo_id):
        logger.info("activity_start")
        # ... work ...
        logger.info("activity_done")
```

`LOG_FORMAT` env: `json` (default in prod) or `human` (default in dev).
`LOG_LEVEL` env: `DEBUG` / `INFO` (default) / `WARN` / `ERROR`.

For HTTP requests, `LoggingMiddleware` (registered in `main.py`)
auto-binds `request_id` (from `X-Request-ID` header or generated UUID)
and `user_id` for every request. The `request_id` is echoed back in
the response so users can include it in bug reports.

## Environment variables

Copy `.env.example` to `.env`. Key vars:

- `DATABASE_URL` — Postgres URL (auto-set in docker compose)
- `TEMPORAL_ADDRESS` — Temporal server (auto-set in docker compose)
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — GitHub OAuth app creds
- `LITELLM_API_KEY` / `LITELLM_API_BASE` / `LLM_MODEL` — LLM provider
- `FRONTEND_URL` — CORS allow-list (comma-separated)
- `LOG_FORMAT` / `LOG_LEVEL` — see "Logging" above
