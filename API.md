# API reference

The backend exposes a REST API at `http://localhost:8000` (dev) /
`https://<your-coolify-host>` (prod). Interactive Swagger UI lives at
`/docs` (FastAPI auto-generated).

## Authentication

All routes except `/health`, `/auth/exchange`, and `/api/log` require
a `Authorization: Bearer <token>` header. The token comes from the
GitHub OAuth flow:

```bash
# Step 1: redirect user to GitHub OAuth (frontend handles this)
#   https://github.com/login/oauth/authorize?client_id=<GITHUB_CLIENT_ID>&scope=repo,read:user

# Step 2: GitHub redirects to /callback with ?code=<oauth_code>
# Step 3: exchange code for token
curl -X POST http://localhost:8000/api/auth/exchange \
  -H "Content-Type: application/json" \
  -d '{"code": "<oauth_code>"}'
# → { "access_token": "gho_..." }
```

Store the access_token in localStorage (or wherever); inject into every
subsequent request as `Authorization: Bearer <access_token>`.

## Routers (one file per domain — see [`backend/app/api/routes/`](backend/app/api/routes/README.md))

| Router | Path prefix | Purpose |
|---|---|---|
| `health.py` | `/api/health` | Liveness probe |
| `auth.py` | `/api/auth/*` | OAuth code exchange |
| `repos.py` | `/api/repos`, `/api/analyze/*`, `/api/fix/*`, `/api/sync`, `/api/repos/*/commit` | Repository CRUD + analysis + fix workflow |
| `garden.py` | `/api/garden/*` | Batch gardening workflow |
| `portfolio.py` | `/api/portfolio/*` | Portfolio README generation + publish |
| `logs.py` | `/api/log` | Frontend error-boundary log ingestion |

## Common workflows

### Workflow 1 — Authenticate

```bash
curl -X POST http://localhost:8000/api/auth/exchange \
  -H "Content-Type: application/json" \
  -d '{"code": "<oauth_code>"}'
```

### Workflow 2 — List + analyze repos

```bash
TOKEN=gho_xxx

# List all repos for the authenticated user (with cached analysis data)
curl http://localhost:8000/api/repos -H "Authorization: Bearer $TOKEN"

# Trigger health analysis for one repo
curl -X POST http://localhost:8000/api/analyze/<repo_id> \
  -H "Authorization: Bearer $TOKEN"
# → { "workflow_id": "analyze-<repo_id>-<uuid>" }
```

### Workflow 3 — Auto-fix (Janitor workflow)

```bash
# Start the Janitor workflow: scans repo, generates README via LLM, saves as draft
curl -X POST http://localhost:8000/api/fix/<repo_id> \
  -H "Authorization: Bearer $TOKEN"
# → { "workflow_id": "janitor-<repo_id>-<uuid>" }

# Poll the draft state via /repos (status field flips to "drafting_docs" → "review_ready")
curl http://localhost:8000/api/repos -H "Authorization: Bearer $TOKEN"

# When status is "review_ready", commit the approved draft as a PR
curl -X POST http://localhost:8000/api/repos/<repo_id>/commit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"selected_files": ["README.md"], "edited_contents": {"README.md": "# ..."}}'
# → { "pr_url": "https://github.com/owner/repo/pull/<n>" }
```

### Workflow 4 — Portfolio README

```bash
# Generate portfolio README from selected repos
curl -X POST http://localhost:8000/api/portfolio/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo_ids": [123, 456, 789]}'
# → { "workflow_id": "portfolio-<uuid>" }

# Poll for completion
curl http://localhost:8000/api/portfolio/status/<workflow_id> \
  -H "Authorization: Bearer $TOKEN"

# Publish to <username>/<username>.github.io
curl -X POST http://localhost:8000/api/portfolio/publish \
  -H "Authorization: Bearer $TOKEN"
```

## Temporal workflows (behind the scenes)

The `/analyze`, `/fix`, `/garden/start`, `/portfolio/generate` endpoints
all return a `workflow_id` — these run inside the Temporal worker
(separate process / Docker service). See the Temporal UI at
`http://localhost:8233` to watch a workflow's progress, retries, and
activity outputs.

## Error format

FastAPI default: `{"detail": "<message>"}`. The `LoggingMiddleware`
binds a `request_id` to every request — include it when filing bug
reports. The `request_id` is also surfaced via response header
`X-Request-ID`.
