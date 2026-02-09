// --------------------------------------------------
// Types matching Backend Pydantic models exactly
// See: backend/app/schemas/github.py & analysis.py
// --------------------------------------------------

/** backend/app/schemas/github.py -> Repo */
export interface Repo {
    id: number;
    name: string;
    full_name: string;
    private: boolean;
    html_url: string;
    description: string | null;
    /** Populated client-side after analysis */
    health?: RepoHealth;
    /** Draft doc files awaiting human review (Phase 13) */
    draft_proposal?: Record<string, string> | null;
}

/** backend/app/schemas/analysis.py -> RepoHealth */
export interface RepoHealth {
    repo_name: string;
    health_score: number;
    issues: string[];
    last_commit_date: string;
    pending_fix_url: string | null;
    status: string;
    last_gardener_run_at: string | null;
}

/** backend/app/schemas/analysis.py -> BatchStatus */
export interface BatchStatus {
    total: number;
    completed: number;
    results: RepoHealth[];
}

/** Response from GET /api/health */
export interface HealthCheckResponse {
    status: string;
    service: string;
}

/** Response from POST /api/auth/exchange */
export interface AuthExchangeResponse {
    access_token: string;
}

/** Response from POST /api/garden/start, /api/analyze/{id}, /api/fix/{id} */
export interface WorkflowResponse {
    workflow_id: string;
}

/** Response from POST /api/repos/{id}/commit */
export interface CommitResponse {
    status: string;
    pr_url: string;
}

/** Response from POST /api/sync */
export interface SyncResponse {
    status: string;
    updated_count: number;
}

/** Request body for POST /api/portfolio/generate */
export interface PortfolioGenerateRequest {
    repo_ids: number[];
    bio?: string;
    links?: {
        linkedin?: string;
        email?: string;
        website?: string;
    };
}

/** Response from POST /api/portfolio/generate */
export interface PortfolioGenerateResponse {
    workflow_id: string;
}

/** Response from GET /api/portfolio/status/{workflow_id} */
export interface PortfolioStatus {
    stage: string;
    total_repos: number;
    scanned: number;
    draft_readme: string | null;
    errors: string[];
}

/** Response from POST /api/portfolio/publish */
export interface PortfolioPublishResponse {
    status: string;
    profile_url: string | null;
    pr_url: string | null;
}
