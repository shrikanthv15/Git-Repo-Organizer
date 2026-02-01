import axios from "axios";
import type {
    AuthExchangeResponse,
    BatchStatus,
    HealthCheckResponse,
    Repo,
    WorkflowResponse,
} from "@/types/api";

// Base URL: always targets the Backend's /api prefix
const getBaseUrl = () => {
    const url = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    return url.endsWith("/api") ? url : `${url}/api`;
};

// Axios singleton
export const api = axios.create({
    baseURL: getBaseUrl(),
    headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
    },
    timeout: 30000,
});

// Request Interceptor: Inject Bearer token
api.interceptors.request.use(
    (config) => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error),
);

// Response Interceptor: Handle 401 -> redirect to login
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            window.location.href = "/login";
        }
        return Promise.reject(error);
    },
);

// -------------------------------------------------------------------
// Unified API surface — every Backend endpoint in one place
// -------------------------------------------------------------------
export const gardenApi = {
    /** GET /api/health */
    checkHealth: () => api.get<HealthCheckResponse>("/health"),

    /** POST /api/auth/exchange */
    exchangeAuth: (code: string) =>
        api.post<AuthExchangeResponse>("/auth/exchange", { code }),

    /** GET /api/repos */
    getRepos: () => api.get<Repo[]>("/repos"),

    /** POST /api/analyze/{repo_id} */
    triggerAnalysis: (repoId: number) =>
        api.post<WorkflowResponse>(`/analyze/${repoId}`),

    /** POST /api/garden/start?limit=N */
    startBatchAnalysis: (limit: number = 5) =>
        api.post<WorkflowResponse>(`/garden/start?limit=${limit}`),

    /** GET /api/garden/status/{workflow_id} */
    getBatchStatus: (workflowId: string) =>
        api.get<BatchStatus>(`/garden/status/${workflowId}`),

    /** POST /api/fix/{repo_id} */
    triggerFix: (repoId: number) =>
        api.post<WorkflowResponse>(`/fix/${repoId}`),
};
