export interface RepoHealth {
    repo_name: string;
    health_score: number; // 0-100
    issues: string[]; // e.g. ["No README"]
    last_commit_date: string;
}

export interface Repo {
    id: number;
    name: string;
    full_name: string;
    private: boolean;
    html_url: string;
    description: string | null;
    health?: RepoHealth;
}

export interface AuthExchangeResponse {
    access_token: string;
    token_type: string;
}

export interface BatchStatus {
    total: number;
    completed: number;
    results: RepoHealth[]; // The array of finished analyses
}
