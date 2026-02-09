# Deployment Checklist — GitHub Gardener (Coolify)

## 1. Environment Variables to Set in Coolify

| Variable | Required | Example / Default | Description |
|----------|----------|-------------------|-------------|
| `POSTGRES_USER` | Yes | `gardener` | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | *(generate a strong password)* | PostgreSQL password |
| `POSTGRES_DB` | Yes | `gardener` | PostgreSQL database name |
| `GITHUB_CLIENT_ID` | Yes | `Ov23li...` | GitHub OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | Yes | *(from GitHub Developer Settings)* | GitHub OAuth App Client Secret |
| `LITELLM_API_KEY` | Yes | `sk-...` | API key for LLM provider |
| `LITELLM_API_BASE` | No | `https://api.openai.com/v1` | Base URL for LLM API (omit for OpenAI default) |
| `LLM_MODEL` | No | `gpt-4o-mini` | Model name for LLM calls |
| `FRONTEND_URL` | Yes | `https://gardener.yourdomain.com` | Comma-separated allowed CORS origins |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `https://api.gardener.yourdomain.com` | Backend URL as seen by the browser |
| `NEXT_PUBLIC_GITHUB_CLIENT_ID` | Yes | *(same as GITHUB_CLIENT_ID)* | GitHub Client ID for frontend OAuth redirect |

> **Note:** `DATABASE_URL` and `TEMPORAL_ADDRESS` are constructed automatically inside `docker-compose.prod.yml` from the above variables. Do not set them manually.

## 2. Auth Audit — Route Security Report

### Intentionally Public (no auth required)
| Route | Reason |
|-------|--------|
| `GET /api/health` | Health check for monitoring/load balancers |
| `POST /api/auth/exchange` | OAuth login flow — exchanges code for token |

### Secured (require Bearer token) — All Other Routes
| Route | Auth |
|-------|------|
| `POST /api/test-workflow` | `get_current_token` |
| `GET /api/repos` | `get_current_token` |
| `POST /api/analyze/{repo_id}` | `get_current_token` |
| `POST /api/garden/start` | `get_current_token` |
| `GET /api/garden/status/{workflow_id}` | `get_current_token` |
| `POST /api/fix/{repo_id}` | `get_current_token` |
| `POST /api/sync` | `get_current_token` |
| `POST /api/repos/{repo_id}/commit` | `get_current_token` |
| `POST /api/portfolio/generate` | `get_current_token` |
| `GET /api/portfolio/status/{workflow_id}` | `get_current_token` |
| `POST /api/portfolio/publish` | `get_current_token` |

### Previously Unsecured Routes (fixed in Phase 20)
| Route | Issue | Resolution |
|-------|-------|------------|
| `POST /api/test-workflow` | No auth dependency | Added `Depends(get_current_token)` |
| `GET /api/garden/status/{workflow_id}` | No auth dependency | Added `Depends(get_current_token)` |
| `GET /api/portfolio/status/{workflow_id}` | No auth dependency | Added `Depends(get_current_token)` |

## 3. Code Sanitization Summary

| Area | Finding | Action Taken |
|------|---------|--------------|
| Frontend `console.log` | 0 instances | Already clean |
| Frontend `console.error` | 3 instances (all in `catch` blocks) | Kept — appropriate error logging |
| Backend `print()` | 5 instances across `activities.py`, `worker.py` | Replaced with `activity.logger.info()` / `logger.info()` |
| CORS `allow_origins=["*"]` | Allows any origin | Now reads `FRONTEND_URL` env var; falls back to `["*"]` only if unset |
| Hardcoded secrets in `config.py` | GitHub/LLM keys had dev defaults | Replaced with empty string defaults; values must come from env |

## 4. Coolify Deployment Steps

1. **Create a new project** in Coolify and connect your Git repository.
2. **Set Docker Compose file** to `docker-compose.prod.yml`.
3. **Configure environment variables** in Coolify's UI using the table above.
4. **Set up domains** in Coolify:
   - Frontend: `gardener.yourdomain.com` → service `frontend`, port `3000`
   - Backend API: `api.gardener.yourdomain.com` → service `backend`, port `8000`
   - Temporal UI (optional): `temporal.yourdomain.com` → service `temporal-ui`, port `8080`
5. **Update GitHub OAuth App** callback URL to `https://gardener.yourdomain.com/callback`.
6. **Deploy** — Coolify will build and start all services.
7. **Verify:**
   - `curl https://api.gardener.yourdomain.com/api/health` returns `{"status": "healthy"}`
   - Frontend loads at `https://gardener.yourdomain.com`
   - GitHub OAuth login flow completes successfully

## 5. Post-Deployment Checks

- [ ] Health endpoint responds
- [ ] GitHub OAuth login works end-to-end
- [ ] Dashboard loads repos after login
- [ ] Batch analysis workflow completes
- [ ] Janitor workflow generates draft and creates PR
- [ ] Portfolio Studio generates and publishes profile
- [ ] Temporal UI accessible (if domain configured)
- [ ] CORS rejects requests from unauthorized origins
