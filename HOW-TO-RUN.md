# How to Run GitHub Gardener (Development Mode)

This guide explains how to run all services **locally in separate terminals** for active development. This allows you to see changes immediately without rebuilding Docker containers.

---

## Prerequisites

1. **Python 3.12+** installed
2. **Node.js 18+** and **PNPM** installed
3. **PostgreSQL** running (via Docker or local install)
4. **Temporal Server** running (via Docker)
5. **Environment Variables** configured (see below)

---

## Step 0: Environment Setup

### Create `.env` file

```bash
cp .env.example .env
```

### Edit `.env` with your values:

```env
# Database
POSTGRES_USER=gardener
POSTGRES_PASSWORD=gardener_secret
POSTGRES_DB=gardener
DATABASE_URL=postgresql://gardener:gardener_secret@localhost:5432/gardener

# Temporal (localhost when running locally)
TEMPORAL_ADDRESS=localhost:7233

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# AI / LLM
LITELLM_API_KEY=your_api_key
LITELLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_github_client_id
```

**Important:** When running locally (not in Docker), change:
- `TEMPORAL_ADDRESS=temporal:7233` → `TEMPORAL_ADDRESS=localhost:7233`
- `DATABASE_URL=postgresql://gardener:gardener_secret@postgres:5432/gardener` → `DATABASE_URL=postgresql://gardener:gardener_secret@localhost:5432/gardener`

---

## Terminal 1: PostgreSQL + Temporal Server (Docker)

These services are easiest to run via Docker Compose since they require minimal changes during development.

### Start PostgreSQL and Temporal:

```bash
docker-compose up postgres temporal temporal-ui
```

**What this does:**
- Starts PostgreSQL on port **5432**
- Starts Temporal Server on port **7233**
- Starts Temporal UI on port **8233** (view at http://localhost:8233)

**Keep this terminal running.**

---

## Terminal 2: Backend (FastAPI)

The FastAPI backend serves the REST API.

### Navigate to backend directory:

```bash
cd backend
```

### Install dependencies (first time only):

```bash
pip install -e .
```

or with Poetry:

```bash
poetry install
poetry shell
```

### Run database migrations (first time or after schema changes):

```bash
alembic upgrade head
```

### Start the FastAPI server:

```bash
python -m app.main
```

or with uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What this does:**
- Starts FastAPI on port **8000**
- API documentation available at http://localhost:8000/docs
- Auto-reloads on code changes (`--reload` flag)

**Keep this terminal running.**

---

## Terminal 3: Temporal Worker

The worker executes Temporal workflows and activities (the AI brain of the system).

### Navigate to backend directory (if not already there):

```bash
cd backend
```

### Ensure you're in the virtual environment (if using Poetry):

```bash
poetry shell
```

### Start the Temporal worker:

```bash
python -m app.temporal.worker
```

**What this does:**
- Connects to Temporal Server at `localhost:7233`
- Registers workflows: `GreetingWorkflow`, `AnalysisWorkflow`, `JanitorWorkflow`, `PortfolioWorkflow`
- Registers activities: `analyze_repo_health`, `generate_readme_activity`, etc.
- Listens on task queue: `gardener-queue`

**Output you should see:**
```
Worker started, listening on queue: gardener-queue
```

**Keep this terminal running.**

---

## Terminal 4: Frontend (Next.js)

The Next.js frontend provides the user interface.

### Navigate to frontend directory:

```bash
cd frontend
```

### Install dependencies (first time only):

```bash
pnpm install
```

**Important:** Always use `pnpm`, not `npm` or `yarn`.

### Start the development server:

```bash
pnpm dev
```

**What this does:**
- Starts Next.js on port **3000**
- Auto-reloads on code changes
- Connects to backend at `http://localhost:8000`

**Access the app:** http://localhost:3000

**Keep this terminal running.**

---

## Verification Checklist

After starting all four terminals, verify everything is running:

| Service          | URL                           | Status Check                          |
|------------------|-------------------------------|---------------------------------------|
| PostgreSQL       | `localhost:5432`              | Run `psql -U gardener -d gardener`    |
| Temporal Server  | `localhost:7233`              | Check Temporal UI below               |
| Temporal UI      | http://localhost:8233         | Open in browser                       |
| Backend API      | http://localhost:8000         | Visit http://localhost:8000/docs      |
| Temporal Worker  | (no web UI)                   | Check terminal for "Worker started"   |
| Frontend         | http://localhost:3000         | Open in browser                       |

---

## Common Issues & Solutions

### Issue: "Connection refused" errors

**Solution:** Make sure PostgreSQL and Temporal are running in Terminal 1.

```bash
# Check if containers are running
docker ps
```

You should see `postgres` and `temporal` containers.

### Issue: Worker can't connect to Temporal

**Solution:** Verify `TEMPORAL_ADDRESS=localhost:7233` in your `.env` file (NOT `temporal:7233`).

### Issue: Frontend can't connect to backend

**Solution:**
1. Check backend is running on http://localhost:8000/docs
2. Verify `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env`
3. Restart frontend with `pnpm dev`

### Issue: Database migrations fail

**Solution:**
```bash
cd backend
alembic downgrade -1
alembic upgrade head
```

### Issue: Frontend shows "pnpm: command not found"

**Solution:**
```bash
npm install -g pnpm
```

---

## Quick Restart (After Making Changes)

### Backend Code Changes:
- FastAPI auto-reloads (no action needed)

### Worker Code Changes:
- Stop Terminal 3 (Ctrl+C)
- Restart: `python -m app.temporal.worker`

### Frontend Code Changes:
- Next.js auto-reloads (no action needed)

### Database Schema Changes:
1. Create migration: `cd backend && alembic revision --autogenerate -m "description"`
2. Apply migration: `alembic upgrade head`
3. Restart backend (Terminal 2)

---

## Shutdown

To stop all services:

1. **Terminal 4 (Frontend):** Press `Ctrl+C`
2. **Terminal 3 (Worker):** Press `Ctrl+C`
3. **Terminal 2 (Backend):** Press `Ctrl+C`
4. **Terminal 1 (Docker):** Press `Ctrl+C`, then:
   ```bash
   docker-compose down
   ```

---

## Alternative: Run Everything with Docker Compose

If you don't need live reloading for development, you can run everything with:

```bash
docker-compose up --build
```

This starts all services in one command, but requires rebuilding containers to see code changes.

---

## Development Workflow Summary

**Daily startup:**
1. Terminal 1: `docker-compose up postgres temporal temporal-ui`
2. Terminal 2: `cd backend && python -m app.main`
3. Terminal 3: `cd backend && python -m app.temporal.worker`
4. Terminal 4: `cd frontend && pnpm dev`

**Make changes** → See them live (auto-reload) → Test at http://localhost:3000

**When done:** `Ctrl+C` all terminals, then `docker-compose down`
