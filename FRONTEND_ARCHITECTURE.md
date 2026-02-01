# Frontend Architecture & Repair Manual

## 1. Component Tree (`src/`)

- `src/app/`
    - `page.tsx`: Landing page.
    - `login/page.tsx`: Login page (OAuth handling).
    - `dashboard/page.tsx`: Main dashboard (Repo list, Analysis trigger).
- `src/components/`
    - `repo-grid.tsx`: Displays list of repositories.
    - `providers.tsx`: React Query / Context providers.
- `src/services/`
    - `api.ts`: API client (Axios).
- `src/hooks/`
    - `use-gardener.ts`: Hooks for gardening workflows.

## 2. Service Layer Audit (`src/services/api.ts`)

Included in `gardenApi` object:
- `startBatchAnalysis` -> `POST /garden/start`
- `getBatchStatus` -> `GET /garden/status/{id}`
- `triggerFix` -> `POST /fix/{id}`
- `triggerAnalysis` -> `POST /analyze/{id}`

**MISSING / GAPS:**
- 🔴 `GET /repos`: Not exposed in `gardenApi`! The dashboard likely needs this to show the initial list.
- 🔴 `POST /auth/exchange`: Not exposed in `api.ts`. Check `login/page.tsx` - if it calls axios directly, refactor it here.
- 🔴 `GET /health`: Useful for a status indicator/banner, currently missing.

## 3. Environment Config (`.env.local`)

| Variable | Required | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | URL of Backend API (e.g., `http://localhost:8000` or ngrok URL). |
| `NEXT_PUBLIC_GITHUB_CLIENT_ID` | ✅ | Client ID for "Login with GitHub" button. |

## 4. UI/UX Gaps

- **Repo Listing**: Since `GET /repos` is missing in the service layer, ensure the Dashboard can actually list repos before analysis starts.
- **Janitor Feedback**: Frontend has `triggerFix`, but does it show the resulting PR URL? The backend returns `workflow_id`, subsequent status polling for Janitor isn't clearly defined in the frontend types.
- **Progress Visualization**: `BatchStatus` has `total` vs `completed`. Ensure `dashboard/page.tsx` renders a progress bar.

## 5. Dead Code / Cleanups

- `src/lib/api-contract.ts`: Check if this duplicates `types/api.ts`. Consolidate to one source of truth.
- `src/lib/use-repos.ts`: Check if this duplicates `hooks/use-gardener.ts`. Consolidate logic.
- `ANTIGRAVITY_SYNC.md` / `BACKEND_HANDOFF.md`: Old sync files, can be archived.
