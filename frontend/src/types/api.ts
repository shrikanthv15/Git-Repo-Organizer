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
}

/** backend/app/schemas/analysis.py -> RepoHealth */
export interface RepoHealth {
    repo_name: string;
    health_score: number;
    issues: string[];
    last_commit_date: string;
    pending_fix_url: string | null;
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
