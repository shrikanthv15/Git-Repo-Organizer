# Prompt: Phase 10 - System Stabilization & UI Fixes

**Role:** Senior Full Stack Reliability Engineer

**Context:**

We have built a Dockerized AI Agent ("GitHub Gardener"). We are close to the finish line, but we have 3 critical blockers:

1. **Backend Crash:** The worker fails immediately with `AttributeError: module 'temporalio.workflow' has no attribute 'RetryPolicy'`.
2. **Temporal UI Dead:** Accessing `localhost:8233` fails.
3. **Frontend UI Glitches:** The "Fix" button sometimes disappears or doesn't update correctly after analysis.

**Objective:**

Fix these three issues to achieve a stable, error-free run where `docker-compose up` results in a fully functional system.

---

## Part 1: Fix the Backend Crash (Critical)

**Target:** `backend/app/temporal/workflows.py`

* **The Bug:** We are importing `RetryPolicy` from the wrong module. It is NOT in `temporalio.workflow`.
* **The Fix:**

  1. Import `RetryPolicy` from `temporalio.common`.
  2. Update the `JanitorWorkflow` code to use this imported class.

  * *Change:* `retry_policy=workflow.RetryPolicy(...)` → `retry_policy=RetryPolicy(...)`.

## Part 2: Fix the Temporal UI (Docker Networking)

**Target:** `docker-compose.yml`

* **The Bug:** We mapped `8233:8233`, but the official `temporalio/auto-setup` image listens on port **8080** for the Web UI by default.
* **The Fix:** Update the ports mapping to forward Host 8233 to Container 8080.

  ```yaml
  temporal:
    # ...
    ports:
      - "7233:7233"
      - "8233:8080"  # <--- FIX: Map host 8233 to container 8080
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PWD=${POSTGRES_PASSWORD}
      - POSTGRES_SEEDS=postgres
  ```

## Part 3: Frontend "Fix Button" Resilience

**Target:** `frontend/src/app/repo/[repoId]/page.tsx` (or `RepoDetail` component)

* **Logic Audit:**
  * Ensure the "Fix" button logic is strictly binary:
    * **IF** `repo.pending_fix_url` exists AND is not empty → Show **Purple "View PR"** button.
    * **ELSE IF** `repo.health_score < 100` → Show **Green "Auto-Fix"** button.
    * **ELSE** → Show "Healthy" (Disabled).
* **State Management:**
  * When "Auto-Fix" is clicked, set a local loading state (`isFixing = true`).
  * **Do not rely solely on refetching.** If the mutation succeeds, force the local state to show "View PR" immediately (optimistic update) while waiting for the background refetch.

## Part 4: Environment Verification

* **Dockerfile Check:** Ensure `frontend/Dockerfile` still contains the `ARG` and `ENV` lines we added for `NEXT_PUBLIC_...` variables.
* **Env File:** Ensure the backend reads `LITELLM_API_BASE` correctly from the environment.

## Part 5: The "Self-Healing" Verification Script

Create a new script `scripts/system_check.py` that:

1. Pings `http://localhost:8000/api/health` (Backend).
2. Pings `http://localhost:8233` (Temporal UI).
3. Checks if the `worker` container is running (using `docker ps`).
4. Prints a big green "SYSTEM ONLINE" message if all pass.

**Deliverables:**

1. Corrected `backend/app/temporal/workflows.py` (Import fix).
2. Corrected `docker-compose.yml` (Port fix).
3. Hardened Frontend Logic for the Fix Button.
4. The `system_check.py` script.

**Action:** Execute these fixes now.
