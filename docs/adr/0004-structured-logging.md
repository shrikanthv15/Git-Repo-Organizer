# ADR-0004: Structured JSON logging with correlation IDs

- **Status:** Accepted
- **Date:** 2026-05-24
- **Owner:** Batman
- **Envelope:** `build_20260524_005130_e7d6b7` (GRO E4)
- **Depends on:** ADR-0001 (E1: split monoliths, merged commit a1ce786)

## Context

Current logging is ad-hoc:
- `print()` statements scattered in `backend/app/services/*` and `backend/app/temporal/activities/*`
- No correlation across Temporal workflow → activity → service calls
- Frontend has no error boundaries; JavaScript errors blank the page
- Production debugging requires SSH into VPS + grep logs; no structured filtering by workflow_id or user_id
- Acceptance metric: every log line in production must be structured JSON with `request_id` and (for Temporal) `workflow_id` / `activity_name`

## Decision

### 1) Backend: Structured logging with structlog

**Library:** structlog (flexible, supports both human-readable dev mode and JSON prod mode)

**Installation:**
- Add `structlog` to `backend/pyproject.toml` (uv + pip compatible)

**Setup in `backend/app/main.py`:**
```python
import structlog
import logging
import os

log_format = os.getenv("LOG_FORMAT", "human" if os.getenv("ENV") == "dev" else "json")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure structlog
if log_format == "json":
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
else:
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

# Root logger
logging.basicConfig(level=getattr(logging, log_level))
logger = structlog.get_logger()
logger.info("app_startup", format=log_format, level=log_level)
```

**Env vars:**
- `LOG_FORMAT` (default: "human" in dev, "json" in prod) — toggles output format
- `LOG_LEVEL` (default "INFO") — Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**FastAPI middleware for request context** (`backend/app/middleware/logging.py`):
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uuid
import structlog

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Extract user from token if present (depends on auth scheme)
        user_id = extract_user_id_from_request(request)  # app.services.github_service or auth helper
        
        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, user_id=user_id)
        
        response = await call_next(request)
        return response
```

Register in `main.py`:
```python
from app.middleware.logging import LoggingMiddleware
app.add_middleware(LoggingMiddleware)
```

**Temporal activity context** (`backend/app/temporal/middleware.py`):
New context manager for use in activities:
```python
import contextvars
import structlog

_activity_context = contextvars.ContextVar("activity_context", default=None)

@contextmanager
def temporal_activity_context(workflow_id: str, activity_name: str, repo_id: int = None, user_id: str = None):
    """Bind Temporal context to all logs emitted within this scope."""
    structlog.contextvars.bind_contextvars(
        workflow_id=workflow_id,
        activity_name=activity_name,
        repo_id=repo_id,
        user_id=user_id,
    )
    try:
        yield
    finally:
        structlog.contextvars.clear_contextvars()
```

Usage in activity:
```python
@activity.defn
async def analyze_repo_health(repo_full_name: str, access_token: str, workflow_id: str) -> dict:
    logger = structlog.get_logger()
    with temporal_activity_context(workflow_id, "analyze_repo_health", repo_id=..., user_id=...):
        logger.info("activity_start", repo=repo_full_name)
        # ... work ...
        logger.info("activity_end", repo=repo_full_name, score=score)
```

**Replace print/logging in services** (`backend/app/services/*.py`):
- Change `print(...)` → `structlog.get_logger().info(...)`
- Change `logging.info(...)` → `structlog.get_logger().info(...)`
- Log arguments as dict keys, not f-strings: `logger.info("action", key1=val1, key2=val2)`

**Testing:** `backend/tests/test_logging.py`
```python
import json
import structlog
from io import StringIO

def test_workflow_logs_structured():
    """Capture and parse JSON logs from a test activity."""
    output = StringIO()
    structlog.configure(logger_factory=lambda: structlog.PrintLogger(file=output))
    
    # Run activity with bound context
    with temporal_activity_context("wf-123", "test_activity", repo_id=456):
        structlog.get_logger().info("test_event", data="value")
    
    log_line = output.getvalue().strip()
    log_obj = json.loads(log_line)
    
    assert log_obj["workflow_id"] == "wf-123"
    assert log_obj["activity_name"] == "test_activity"
    assert log_obj["repo_id"] == 456
    assert log_obj["event"] == "test_event"
```

### 2) Frontend: Error boundaries + logger

**New file: `frontend/src/app/error.tsx`** (page-level error boundary):
```typescript
"use client";
import { useEffect } from "react";
import { ErrorLog } from "@/lib/logger";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    ErrorLog.error("page_error", { message: error.message, digest: error.digest });
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-red-900/20">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-red-400">Something went wrong</h2>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <button onClick={reset} className="mt-4 px-4 py-2 bg-red-600 rounded">
          Try again
        </button>
      </div>
    </div>
  );
}
```

**New file: `frontend/src/app/global-error.tsx`** (root layout error boundary):
```typescript
"use client";
import { ErrorLog } from "@/lib/logger";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  ErrorLog.error("root_error", { message: error.message, digest: error.digest });

  return (
    <html>
      <body>
        <div className="flex items-center justify-center min-h-screen bg-red-950">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-red-400">Critical Error</h1>
            <p className="text-muted-foreground mt-2">The application encountered a fatal error.</p>
            <button onClick={reset} className="mt-4 px-4 py-2 bg-red-600 rounded">
              Reload
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
```

**New file: `frontend/src/lib/logger.ts`** (small wrapper, no external deps):
```typescript
const LOG_ENDPOINT = process.env.NEXT_PUBLIC_LOG_ENDPOINT;
const DEFAULT_CONTEXT = {
  route: typeof window !== "undefined" ? window.location.pathname : "unknown",
  userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
  timestamp: new Date().toISOString(),
};

export const ErrorLog = {
  error: async (message: string, context?: Record<string, any>) => {
    const payload = { ...DEFAULT_CONTEXT, ...context, level: "error", message };
    console.error(`[${payload.route}]`, message, context);
    
    if (LOG_ENDPOINT) {
      try {
        await fetch(LOG_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch(() => {}); // Silent fail on network error
      } catch (e) {
        // Ignore
      }
    }
  },

  info: async (message: string, context?: Record<string, any>) => {
    const payload = { ...DEFAULT_CONTEXT, ...context, level: "info", message };
    console.info(`[${payload.route}]`, message, context);
    
    if (LOG_ENDPOINT) {
      try {
        await fetch(LOG_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch(() => {});
      } catch (e) {
        // Ignore
      }
    }
  },
};
```

**Optional API endpoint:** `backend/app/api/routes/logs.py` (if `NEXT_PUBLIC_LOG_ENDPOINT` is set):
```python
@router.post("/api/log")
async def log_frontend_error(body: dict):
    """Receive structured logs from frontend error boundaries."""
    logger = structlog.get_logger()
    logger.info("frontend_log", **body)
    return {"status": "logged"}
```

### 3) Documentation

**Update `README.md`** with new env vars and sample logs:

```markdown
## Logging

### Backend

- **LOG_FORMAT** (default: "human" in dev, "json" in prod)
  - "human": pretty-printed console output
  - "json": newline-delimited JSON for log aggregation

- **LOG_LEVEL** (default: "INFO")
  - Python logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL

#### Sample JSON log (production):
```json
{"workflow_id":"wf-123","activity_name":"analyze_repo_health","repo_id":456,"user_id":"gh-user","event":"activity_start","repo":"owner/name"}
{"workflow_id":"wf-123","activity_name":"analyze_repo_health","repo_id":456,"user_id":"gh-user","event":"activity_end","health_score":85,"elapsed_ms":1234}
```

### Frontend

- **NEXT_PUBLIC_LOG_ENDPOINT** (optional, default: undefined)
  - If set, frontend error boundaries POST their errors to this endpoint
  - Example: `/api/log`

Error boundaries are added to `app/error.tsx` (page-level) and `app/global-error.tsx` (root layout).
```

## Consequences

- **Pros**
  - Full traceability of workflow → activity → service calls via `workflow_id`
  - Dev-friendly human logs; prod JSON for log aggregation (e.g., ELK, Datadog)
  - Frontend errors no longer blank the page
  - Cost: minimal (structlog is lightweight; frontend logger is ~40 LOC)
  
- **Cons**
  - All services must migrate from `print()`/`logging` to `structlog`
  - Activities must call context manager (boilerplate, but enforced by tests)

## Implementation notes

1. Add structlog to `pyproject.toml`; run `uv lock`
2. Wire up logging in `main.py` and register middleware
3. Create `middleware/logging.py` + `temporal/middleware.py`
4. Replace `print()`/`logging` calls in all services + activities (use grep + sed to batch)
5. Create error boundaries + logger in frontend
6. Write tests in `test_logging.py`
7. Update README with env vars + sample logs
8. `uv run pytest` passes; `npm run build` clean

## Alternatives considered

- **python-json-logger**: simpler but less flexible; structlog wins on context binding
- **Python logging only**: loses ability to suppress logs per context; structlog contextvars are superior
- **Third-party frontend logger (Sentry, Datadog)**: unnecessary; simple POST is sufficient for MVP
