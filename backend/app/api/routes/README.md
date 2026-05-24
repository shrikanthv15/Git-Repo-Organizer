# backend/app/api/routes/

Per-domain FastAPI routers, split from a single 304-LOC `routes.py`
pre-E1.

## Routers

| File | Path | Purpose |
|---|---|---|
| `health.py` | `GET /health` | Liveness probe (no auth) |
| `auth.py` | `POST /auth/exchange` | GitHub OAuth code → access token (no auth) |
| `repos.py` | `GET /repos`, `POST /analyze/{repo_id}`, `POST /fix/{repo_id}`, `POST /sync`, `POST /repos/{repo_id}/commit` | Repository listing + analysis + Janitor fix workflow + draft commit |
| `garden.py` | `POST /garden/start`, `GET /garden/status/{workflow_id}` | Batch gardening workflow orchestration |
| `portfolio.py` | `POST /portfolio/generate`, `GET /portfolio/status/{workflow_id}`, `POST /portfolio/publish` | Portfolio README generation + publish |
| `logs.py` | `POST /log` | Frontend error-boundary log ingestion (no auth) |

All paths above are relative to the `/api` prefix mounted in
`app/main.py:app.include_router(api_router, prefix="/api")`.

## Aggregation

`__init__.py` creates an `api_router` that includes all per-domain
routers — `main.py` only imports `api_router`, never the individual
files.

## Shared dependencies

`app/api/deps.py` houses dependency functions shared across routers:

- `get_temporal_client()` — opens a Temporal client to the address from settings
- `get_current_token()` — extracts the Bearer token from `Authorization` header, returns 401 if missing or empty

Inject via FastAPI's `Depends(...)`:

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_token

router = APIRouter()

@router.get("/example")
async def my_handler(token: str = Depends(get_current_token)):
    return {"token_first_8": token[:8]}
```

## Adding a new endpoint

1. **Pick the right router** by URL prefix / resource ownership. If it doesn't fit any existing one, create a new `routes/<domain>.py`.
2. **Define handlers** under a module-level `router = APIRouter()`. Decorate with `@router.<method>(<path>)`.
3. **If you created a new router file**, register it in `__init__.py`:
   ```python
   from app.api.routes.<domain> import router as <domain>_router
   api_router.include_router(<domain>_router)
   ```
4. **Add a test** at `tests/api/test_<domain>.py` covering happy + auth-fail paths.
5. **Update `API.md`** at the repo root with the new endpoint + a curl example.
