# Roles & Responsibilities: Project "GitHub Gardener"

**Protocol:** Same Wi-Fi / Local Network Development
**Date:** January 2026

---

## 1. The Shared Environment (Read First)

Both engineers must adhere to this network protocol to ensure seamless connectivity.

* **Network Strategy:** Hybrid Local.
  * **NO `localhost`:** We do not use `127.0.0.1` for inter-service communication.
  * **YES `192.168.x.x`:** All services must bind to the machine's LAN IP.
* **Tooling:**
  * **IDE:** Antigravity (Google) / VS Code
  * **Containerization:** Docker Desktop (Running Temporal Server & DB only)
  * **Package Managers:** `uv` (Python Backend), `pnpm` (Node Frontend)

---

## 2. Person A: The Backend Architect

**Primary Focus:** Logic, State Management, and AI Agents.

### 🛠️ The Stack

* **Language:** Python 3.12+
* **API Framework:** FastAPI (`uvicorn`)
* **Orchestration:** Temporal.io (Python SDK)
* **Agent Framework:** LangGraph
* **GitHub Integration:** `PyGithub` / `Octokit`

### 📋 Key Responsibilities

1. **The API Server (FastAPI):**
   * **Critical:** Must run with `--host 0.0.0.0` to expose endpoints to the Frontend laptop.
   * Implement the OAuth Token Exchange logic.
   * Expose endpoints for starting workflows and checking status.
2. **The "Gardening" Workflow (Temporal):**
   * **Workflow:** `GardeningWorkflow` - The state machine that manages the cloning, auditing, and committing process.
   * **Activities:**
     * `ScoutActivity`: Fetches list of repos via GitHub API.
     * `AuditActivity`: Clones a specific repo to a local temporary sandbox.
     * `CommitActivity`: Pushes changes to a new branch (`ai-cleanup`).
3. **The "Brain" (LangGraph):**
   * **Agent:** `RepoGardenerAgent`.
   * **Logic:** A graph that accepts file context and outputs:
     * A structured `README.md`.
     * A proposed "Modularity Plan" (e.g., "Move these 5 scripts to `/utils`").
4. **Security:**
   * Manage the `.env` file containing `OPENAI_API_KEY` and `GITHUB_CLIENT_SECRET`.

---

## 3. Person B: The Frontend Commander

**Primary Focus:** User Experience, Visualization, and Approval Flows.

### 🛠️ The Stack

* **Framework:** Next.js 16 (App Router)
* **Styling:** Tailwind CSS v4 + Shadcn UI
* **State Management:** React Query (TanStack Query)
* **Auth:** NextAuth.js (GitHub Provider)

### 📋 Key Responsibilities

1. **The "Greenhouse" Dashboard:**
   * A responsive Grid View of all user repositories.
   * **Visuals:** "Health Cards" showing repo stats (Language, Stars, AI Score).
   * **Interaction:** Multi-select repos to trigger the "Start Gardening" action.
2. **Real-Time Status Tracking:**
   * Implement **Polling** (via React Query) to hit the Backend status endpoint every 1 second.
   * Show a progress stepper: *Scouting → Cloning → AI Thinking → Ready for Review*.
3. **The "Diff" Experience:**
   * A specialized "Split View" component.
   * **Left:** Old README (rendered Markdown).
   * **Right:** AI Proposed README (rendered Markdown with green highlights).
4. **Network Configuration:**
   * Maintain the `.env.local` file pointing `NEXT_PUBLIC_API_URL` to the Backend Partner's IP (e.g., `http://192.168.1.50:8000`).

---

## 4. The API Contract (The Handshake)

*Both parties agree to this schema before writing code.*

### Authentication

* **POST** `/api/auth/exchange`
  * **Input:** `{ "code": "github_oauth_code" }`
  * **Output:** `{ "access_token": "gho_..." }`

### Repository Management

* **GET** `/api/repos`
  * **Output:** `[ { "id": "123", "name": "my-repo", "health_score": 85, "needs_gardening": true } ]`

### The Gardening Process

* **POST** `/api/garden/start`

  * **Input:** `{ "repo_ids": ["123", "456"], "github_token": "gho_..." }`
  * **Output:** `{ "job_id": "workflow_uuid_789" }`
* **GET** `/api/garden/status/{job_id}`

  * **Output:**
    ```json
    {
      "status": "in_progress",
      "current_step": "analyzing_code",
      "percent_complete": 45
    }
    ```
* **GET** `/api/garden/preview/{repo_id}`

  * **Output:**
    ```json
    {
      "original_readme": "# Old Content...",
      "proposed_readme": "# New Content...",
      "proposed_file_moves": [
        { "from": "script.py", "to": "src/script.py" }
      ]
    }
    ```
* **POST** `/api/garden/approve`

  * **Input:** `{ "repo_id": "123", "job_id": "uuid", "approved": true }`
  * **Action:** Triggers the Temporal Signal to execute `git push`.

---

## 5. The "Same Wi-Fi" Launch Checklist

1. **Backend Dev:**
   * Run `ipconfig` / `ifconfig` to find LAN IP.
   * Start Temporal: `temporal server start-dev`.
   * Start FastAPI: `uvicorn main:app --host 0.0.0.0 --port 8000`.
2. **Frontend Dev:**
   * Update `.env.local`: `NEXT_PUBLIC_API_URL=http://<BACKEND_IP>:8000`.
   * Start Next.js: `pnpm run dev`.
3. **Connection Test:**
   * Frontend Dev opens browser to `http://<BACKEND_IP>:8000/docs`.
   * If Swagger UI loads, **START CODING.**
