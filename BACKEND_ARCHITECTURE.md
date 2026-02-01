# Backend Architecture & Repair Manual

## 1. API Surface (`app/api/routes.py`)

| Method | Endpoint | Request Body | Response Model | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | None | `{"status": str, "service": str}` | Health check. |
| `POST` | `/api/auth/exchange` | `AuthExchangeRequest` | `{"access_token": str}` | Exchange GitHub OAuth code. |
| `POST` | `/api/test-workflow` | None | `{"result": str}` | Trigger test greeting workflow as sanity check. |
| `GET` | `/api/repos` | None | `list[Repo]` | List user's repositories. |
| `POST` | `/api/analyze/{repo_id}` | None | `{"workflow_id": str}` | Trigger single repo analysis. |
| `POST` | `/api/garden/start` | Query: `limit=int` | `{"workflow_id": str}` | Start batch analysis (Parent Workflow). |
| `GET` | `/api/garden/status/{workflow_id}` | None | `BatchStatus` | Poll for batch results. |
| `POST` | `/api/fix/{repo_id}` | None | `{"workflow_id": str}` | Trigger Janitor (Readme Repair) workflow. |

## 2. Data Models (`app/schemas/`)

### `Repo` (`github.py`)
```json
{
  "id": "int",
  "name": "str",
  "full_name": "str",
  "private": "bool",
  "html_url": "str",
  "description": "str | None"
}
```

### `RepoHealth` (`analysis.py`)
```json
{
  "repo_name": "str",
  "health_score": "int",
  "issues": "list[str]",
  "last_commit_date": "datetime"
}
```

### `BatchStatus` (`analysis.py`)
```json
{
  "total": "int",
  "completed": "int",
  "results": "list[RepoHealth]"
}
```

## 3. Agent Workflows (`temporal/workflows.py`)

- **`GreetingWorkflow`**: Simple test workflow.
- **`AnalysisWorkflow`**: Analyzes a single repo for health (README, Staleness, Description).
- **`BatchGardeningWorkflow`**: Parent workflow that spawns multiple `AnalysisWorkflow` children. Input: `access_token`, `limit`.
- **`JanitorWorkflow`**: Remediation workflow.
    1.  **Read**: Get repo file tree.
    2.  **Think**: LLM generates README.
    3.  **Act**: Create/Update `gardener/readme-fix` branch and open PR.

## 4. Environment Variables (`.env`)

| Variable | Description |
| :--- | :--- |
| `PROJECT_NAME` | Name of the project (e.g., "GitHub Gardener"). |
| `GITHUB_CLIENT_ID` | OAuth Client ID for GitHub App. |
| `GITHUB_CLIENT_SECRET` | OAuth Client Secret for GitHub App. |
| `LITELLM_API_KEY` | API Key for LLM provider (e.g., OpenAI, Anthropic). |
| `LLM_MODEL` | specific model to use (e.g., `gpt-4o-mini`). |
| `LITELLM_API_BASE` | Base URL for LiteLLM if using a proxy. |

## 5. Cleanup Candidates

- `backend/anti-gravity did this/`: This folder contains logs and guides from previous agents. Can be archived or deleted once read.
- `backend/app/temporal/worker.py`: Ensure this is robust enough for production (currently simple dev script).
