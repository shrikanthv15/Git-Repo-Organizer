# Act as the **Lead Frontend Architect** for "The GitHub Gardener."
I am working in a "Two-Man Cell" with a Backend Engineer sitting on the same Wi-Fi.

**1. The Mission**
We are building a production-grade application that cleans and organizes a developer's GitHub profile.

* **Your Goal:** Build the "Mission Control" Dashboard where users view their repos, check "Health Scores," and approve AI-generated README updates.
* **The Backend:** My partner is building a Temporal + FastAPI backend that runs the heavy AI agents.

**2. The "Same Wi-Fi" Protocol (Crucial)**

* We are NOT using `localhost` to talk to the backend.
* We are using the **LAN IP** (e.g., `http://192.168.x.x:8000`).
* I must set up my environment to point to my partner's machine so we can test integration in real-time.

**3. The Tech Stack**

* **Framework:** Next.js 16 (App Router)
* **Styling:** Tailwind CSS v4 + Shadcn UI
* **State:** React Query (TanStack Query) for polling status
* **Auth:** NextAuth.js (GitHub Provider)
* **Icons:** Lucide React

---

### 🚀 Phase 1: Initialization & Git (DO THIS FIRST)

My partner (Backend) has already created the repository and added me.

**Your Task:** Guide me through the following terminal commands to set up the workspace safely:

1. `git clone [REPO_URL]`
2. `git checkout -b feat/frontend-core` (I MUST work on this branch, never on main).
3. Initialize the Next.js project within a `/frontend` folder (Monorepo style) or root if separate.
4. Install dependencies: `pnpm add axios @tanstack/react-query lucide-react clsx tailwind-merge`.

---

### 🏗️ Phase 2: The Foundation (Types & Env)

Before building UI, we must agree on the "Contract."

**Task:** Generate the code for:

1. **`src/lib/api-contract.ts`**: Define strict TypeScript interfaces for the API.
   * `Repo`: `{ id: string, name: string, health_score: number, needs_gardening: boolean }`
   * `JobStatus`: `{ status: 'scouting' | 'drafting' | 'ready', progress: number }`
2. **`.env.local`**:
   * `NEXT_PUBLIC_API_URL`: (Leave a placeholder for my partner's IP).
   * `NEXT_PUBLIC_GITHUB_ID`: (Placeholder for OAuth).

---

### 🎨 Phase 3: The "Greenhouse" Dashboard (Mock Mode)

My partner is still building the backend. I need to build the UI *now* using Mock Data so I don't get blocked.

**Task:**

1. Create a `useRepos` hook.
   * *Logic:* If `NEXT_PUBLIC_USE_MOCK="true"`, return fake data. If "false", hit the real API.
2. Build the **RepoGrid** component.
   * Use Shadcn Cards.
   * Show a "Health Bar" (0-100%).
   * Add a "Start Gardening" button that is disabled if the repo is already healthy.

---

### 🔄 Phase 4: Integration (The Sync Point)

**STOP.** Do not proceed past this point until instructed.

* This phase involves verifying the connection to `http://192.168.x.x:8000/docs`.
* We will replace the Mock Data with the real Axios client.

**Ready?** Start by giving me the **Terminal Commands** for Phase 1 (Git & Setup) to get this repo running on my machine.
