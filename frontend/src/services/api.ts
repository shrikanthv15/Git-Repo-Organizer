import axios from "axios";
import { BatchStatus } from "@/types/api";

// Create Axios instance singleton
// Helper to ensure /api suffix
const getBaseUrl = () => {
    const url = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const finalUrl = url.endsWith("/api") ? url : `${url}/api`;
    console.log("[API] Base URL initialized:", finalUrl);
    return finalUrl;
};

// Create Axios instance singleton
export const api = axios.create({
    baseURL: getBaseUrl(),
    headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
    },
    timeout: 10000,
});

// Request Interceptor: Inject Token
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
    (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 & HTML Warnings
api.interceptors.response.use(
    (response) => {
        const contentType = response.headers["content-type"];
        if (contentType && contentType.includes("text/html")) {
            console.warn("[API] Received HTML from Backend. Possible Auth or Ngrok issue.");
        }
        return response;
    },
    (error) => {
        if (error.response && error.response.status === 401) {
            if (typeof window !== "undefined") {
                localStorage.removeItem("access_token");
                window.location.href = "/login";
            }
        }
        return Promise.reject(error);
    }
);

export const gardenApi = {
    startBatchAnalysis: async (limit: number = 5) => {
        return api.post<{ workflow_id: string }>(`/garden/start?limit=${limit}`);
    },
    getBatchStatus: async (workflow_id: string) => {
        return api.get<BatchStatus>(`/garden/status/${workflow_id}`);
    },
    triggerFix: async (repo_id: number) => {
        return api.post<{ workflow_id: string; status: string }>(`/fix/${repo_id}`);
    },
    triggerAnalysis: async (repo_id: number) => {
        return api.post<{ workflow_id: string; status: string }>(`/analyze/${repo_id}`);
    },
};
