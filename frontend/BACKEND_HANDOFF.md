# GitHub Gardener - AI-Powered Repo Manager

**Backend Architecture & API Contract**

GitHub Gardener is an intelligent repository management system that uses AI agents to analyze, monitor, and automatically improve your GitHub repositories. Built with FastAPI and Temporal workflows, it provides automated health checks and remediation through pull requests.

---

## Architecture Stack

- **Python**: 3.12
- **Web Framework**: FastAPI
- **Workflow Engine**: Temporal
- **AI/LLM**: LiteLLM (supports multiple providers)
- **GitHub Integration**: PyGithub
- **Package Manager**: uv

---

## API Contract

All authenticated endpoints require a `Bearer` token in the `Authorization` header:
```
Authorization: Bearer <github_access_token>
```

### Endpoints

| Method | Endpoint | Auth Required | Payload | Response | Description |
|--------|----------|---------------|---------|----------|-------------|
| `GET` | `/api/health` | ❌ | None | `{"status": "healthy", "service": "Gardener Backend"}` | Health check endpoint |
| `POST` | `/api/auth/exchange` | ❌ | `{"code": "string"}` | `{"access_token": "string"}` | Exchange GitHub OAuth code for access token |
| `POST` | `/api/test-workflow` | ❌ | None | `{"result": "string"}` | Test Temporal workflow connectivity |
| `GET` | `/api/repos` | ✅ | None | `Repo[]` | List all user-owned repositories |
| `POST` | `/api/analyze/{repo_id}` | ✅ | None | `{"workflow_id": "string"}` | Trigger single repo health analysis |
| `POST` | `/api/garden/start?limit=N` | ✅ | Query: `limit` (default: 3) | `{"workflow_id": "string"}` | Start batch analysis of N repos |
| `GET` | `/api/garden/status/{workflow_id}` | ❌ | None | `BatchStatus` | Poll batch analysis progress |
| `POST` | `/api/fix/{repo_id}` | ✅ | None | `{"workflow_id": "string"}` | Trigger Janitor agent to create README PR |

---

## The Agents

### 🌿 Gardener (Batch Analysis)

**Workflow**: `BatchGardeningWorkflow`  
**Pattern**: Parent-Child Workflow

The Gardener agent performs parallel health checks across multiple repositories.

**How it works:**
1. **Parent Workflow** fetches the user's repo list (limited by `?limit=N`)
2. Spawns **Child Workflows** (one per repo) to analyze in parallel
3. Each child runs `AnalysisWorkflow` which checks:
   - ✅ README presence
   - ✅ Staleness (last push > 6 months)
   - ✅ Description presence
4. Aggregates results and exposes real-time status via **Queries**

**Health Score Calculation:**
- Start: 100 points
- No README: -20
- Stale (>6 months): -30
- No description: -10

**Use Case**: "Scan my top 10 repos and show me which ones need attention"

---

### 🧹 Janitor (Remediation)

**Workflow**: `JanitorWorkflow`  
**Pattern**: Read → Think → Act

The Janitor agent automatically fixes issues by generating documentation and creating pull requests.

**How it works:**
1. **Read**: Fetches the repository file tree (depth: 2 levels)
2. **Think**: Sends file structure to LiteLLM to generate a professional README.md
3. **Act**: Creates/updates branch `gardener/readme-fix`, commits README, opens PR

**Idempotent Design:**
- Reuses the same branch (`gardener/readme-fix`) across runs
- Updates existing PR instead of creating duplicates
- Safe to run multiple times on the same repo

**Use Case**: "My repo has no README. Generate one and create a PR for me."

---

## Data Models

### `Repo`
```json
{
  "id": 12345,
  "name": "my-project",
  "full_name": "username/my-project",
  "private": false,
  "html_url": "https://github.com/username/my-project",
  "description": "A cool project"
}
```

### `RepoHealth`
```json
{
  "repo_name": "username/my-project",
  "health_score": 70,
  "issues": ["No README", "Stale — last push 8 months ago"],
  "last_commit_date": "2025-05-15T10:30:00Z"
}
```

### `BatchStatus`
```json
{
  "total": 5,
  "completed": 3,
  "results": [
    {
      "repo_name": "username/repo1",
      "health_score": 100,
      "issues": [],
      "last_commit_date": "2026-01-20T14:22:00Z"
    }
  ]
}
```
