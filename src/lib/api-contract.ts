export interface Repo {
    id: string;
    name: string;
    description?: string;
    url: string;
    health_score: number; // 0-100
    needs_gardening: boolean;
}

export type JobStatus = 'scouting' | 'drafting' | 'ready' | 'completed' | 'failed';
