import { useState, useEffect, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { gardenApi } from "@/services/api";
import type { Repo, BatchStatus, PortfolioStatus, PortfolioGenerateRequest, PortfolioPublishResponse } from "@/types/api";

// -------------------------------------------------------------------
// Polling safeguards
// -------------------------------------------------------------------
const MAX_POLL_ATTEMPTS = 60;

/** Exponential backoff: 1s → 2s → 4s → 8s (cap), stepping every 5 attempts */
function backoffDelay(attempt: number): number {
    return Math.min(1000 * Math.pow(2, Math.floor(attempt / 5)), 8000);
}

/** True for HTTP 404, 500, or any non-retryable server error */
function isTerminalHttpError(error: unknown): boolean {
    if (!axios.isAxiosError(error)) return false;
    const status = error.response?.status;
    return status === 404 || status === 500 || status === 502 || status === 503;
}

// -------------------------------------------------------------------
// useHealthCheck — connectivity probe
// -------------------------------------------------------------------
export function useHealthCheck() {
    return useQuery({
        queryKey: ["health"],
        queryFn: async () => {
            const { data } = await gardenApi.checkHealth();
            return data;
        },
        retry: 1,
        refetchOnWindowFocus: false,
    });
}

// -------------------------------------------------------------------
// useRepos — smart polling: only poll when repos are actively drafting
// -------------------------------------------------------------------
export function useRepos() {
    return useQuery({
        queryKey: ["repos"],
        queryFn: async (): Promise<Repo[]> => {
            const { data } = await gardenApi.getRepos();
            return Array.isArray(data) ? data : [];
        },
        staleTime: 60_000, // 60s — idle repos don't need constant refetch
        refetchInterval: (query) => {
            if (query.state.status === "error") return false;
            // Smart poll: if any repo is drafting, poll every 3s; otherwise stop
            const repos = query.state.data;
            const hasDrafting = repos?.some(
                (r) => r.health?.status === "drafting_docs"
            );
            return hasDrafting ? 3_000 : false;
        },
    });
}

// -------------------------------------------------------------------
// useRepo — single repo lookup from the repos cache
// -------------------------------------------------------------------
export function useRepo(repoId: number) {
    return useQuery({
        queryKey: ["repos"],
        queryFn: async (): Promise<Repo[]> => {
            const { data } = await gardenApi.getRepos();
            return Array.isArray(data) ? data : [];
        },
        select: (repos) => repos.find((r) => r.id === repoId) ?? null,
    });
}

// -------------------------------------------------------------------
// useGardener — batch analysis, single analysis, janitor fix
// -------------------------------------------------------------------
export function useGardener() {
    const queryClient = useQueryClient();
    const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
    const [isBatchComplete, setIsBatchComplete] = useState(false);

    // Track per-repo fix status: repoId -> "pending" | "done"
    const [fixStatus, setFixStatus] = useState<Record<number, "pending" | "done">>({});

    // Start Batch Mutation
    const startBatch = useMutation({
        mutationFn: async (limit: number = 0) => {
            const { data } = await gardenApi.startBatchAnalysis(limit);
            return data.workflow_id;
        },
        onSuccess: (workflowId) => {
            setCurrentWorkflowId(workflowId);
            setIsBatchComplete(false);
        },
    });

    // Polling Query for batch status
    const { data: batchStatus, error: batchError } = useQuery({
        queryKey: ["batchStatus", currentWorkflowId],
        queryFn: async (): Promise<BatchStatus | null> => {
            if (!currentWorkflowId) return null;
            const { data } = await gardenApi.getBatchStatus(currentWorkflowId);
            return data;
        },
        enabled: !!currentWorkflowId && !isBatchComplete,
        retry: false,
        refetchInterval: (query) => {
            if (query.state.status === "error") return false;
            if (query.state.dataUpdateCount > MAX_POLL_ATTEMPTS) return false;
            return 2000;
        },
    });

    // Merge batch results into the repos cache
    useEffect(() => {
        // Stop polling on HTTP error (404, 500, network failure)
        if (batchError) {
            setIsBatchComplete(true);
            setCurrentWorkflowId(null);
            return;
        }
        if (!batchStatus) return;

        if (batchStatus.completed === batchStatus.total && batchStatus.total > 0) {
            setIsBatchComplete(true);
            setCurrentWorkflowId(null);
        }

        if (batchStatus.results?.length > 0) {
            queryClient.setQueryData<Repo[]>(["repos"], (oldRepos) => {
                if (!oldRepos) return oldRepos;
                return oldRepos.map((repo) => {
                    const healthUpdate = batchStatus.results.find(
                        (r) => r.repo_name === repo.name || r.repo_name === repo.full_name,
                    );
                    return healthUpdate ? { ...repo, health: healthUpdate } : repo;
                });
            });
        }
    }, [batchStatus, batchError, queryClient]);

    // Fix Mutation (Janitor) — now polls for draft_proposal instead of pending_fix_url
    const triggerFix = useMutation({
        mutationFn: async (repoId: number) => {
            const { data } = await gardenApi.triggerFix(repoId);

            // Poll DB for draft_proposal
            let foundDraft: Record<string, string> | null = null;
            let attempts = 0;

            while (!foundDraft && attempts < MAX_POLL_ATTEMPTS) {
                await new Promise((r) => setTimeout(r, backoffDelay(attempts)));
                attempts++;
                try {
                    const res = await gardenApi.getRepos();
                    const repos = Array.isArray(res.data) ? res.data : [];
                    const updatedRepo = repos.find((r) => r.id === repoId);

                    if (updatedRepo?.draft_proposal && Object.keys(updatedRepo.draft_proposal).length > 0) {
                        foundDraft = updatedRepo.draft_proposal;
                        break;
                    }
                } catch (e) {
                    if (isTerminalHttpError(e)) {
                        throw new Error(`Janitor failed: server returned ${(e as any).response?.status}`);
                    }
                    console.error("Polling error (attempt %d/%d)", attempts, MAX_POLL_ATTEMPTS, e);
                }
            }

            if (!foundDraft) throw new Error(`Janitor timeout: draft not ready after ${MAX_POLL_ATTEMPTS} attempts`);

            return { repoId, workflowId: data.workflow_id, draft: foundDraft };
        },
        onMutate: (repoId) => {
            setFixStatus((prev) => ({ ...prev, [repoId]: "pending" }));
        },
        onSuccess: ({ repoId, draft }) => {
            setFixStatus((prev) => ({ ...prev, [repoId]: "done" }));

            // Update cache with the draft_proposal
            queryClient.setQueryData<Repo[]>(["repos"], (old) => {
                if (!old) return [];
                return old.map((repo) => {
                    if (repo.id === repoId) {
                        return { ...repo, draft_proposal: draft };
                    }
                    return repo;
                });
            });
        },
        onError: (_err, repoId) => {
            setFixStatus((prev) => {
                const next = { ...prev };
                delete next[repoId];
                return next;
            });
        },
    });

    // Commit Mutation — approve selected draft files (with optional edits), creates PR
    const commitDocs = useMutation({
        mutationFn: async ({
            repoId,
            selectedFiles,
            editedContents,
        }: {
            repoId: number;
            selectedFiles: string[];
            editedContents?: Record<string, string>;
        }) => {
            const { data } = await gardenApi.commitDocs(repoId, selectedFiles, editedContents);
            return { repoId, prUrl: data.pr_url };
        },
        onSuccess: ({ repoId, prUrl }) => {
            // Clear draft and set pending_fix_url in cache
            queryClient.setQueryData<Repo[]>(["repos"], (old) => {
                if (!old) return [];
                return old.map((repo) => {
                    if (repo.id === repoId) {
                        return {
                            ...repo,
                            draft_proposal: null,
                            health: repo.health
                                ? { ...repo.health, pending_fix_url: prUrl }
                                : repo.health,
                        };
                    }
                    return repo;
                });
            });
        },
    });

    // Sync Mutation — check GitHub for merged/closed PRs
    const syncStatus = useMutation({
        mutationFn: async () => {
            const { data } = await gardenApi.syncStatus();
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["repos"] });
        },
    });

    // Single Analysis Mutation
    const triggerSingleAnalysis = useMutation({
        mutationFn: async (repoId: number) => {
            const { data } = await gardenApi.triggerAnalysis(repoId);
            // Poll for result with backoff + terminal error bailout
            let result = null;
            let attempts = 0;
            while (!result && attempts < MAX_POLL_ATTEMPTS) {
                await new Promise((r) => setTimeout(r, backoffDelay(attempts)));
                attempts++;
                try {
                    const status = await gardenApi.getBatchStatus(data.workflow_id);
                    if (status.data.results && status.data.results.length > 0) {
                        result = status.data.results[0];
                        break;
                    }
                } catch (e) {
                    if (isTerminalHttpError(e)) {
                        throw new Error(`Analysis failed: server returned ${(e as any).response?.status}`);
                    }
                    console.error("Polling error (attempt %d/%d)", attempts, MAX_POLL_ATTEMPTS, e);
                }
            }
            if (!result) throw new Error(`Analysis timeout after ${MAX_POLL_ATTEMPTS} attempts`);
            return { repoId, health: result };
        },
        onSuccess: ({ repoId, health }) => {
            // MANUAL CACHE UPDATE (Do not refetch from server)
            queryClient.setQueryData<Repo[]>(["repos"], (old) => {
                if (!old) return [];
                return old.map((repo) => {
                    if (repo.id === repoId) {
                        return { ...repo, health: health };
                    }
                    return repo;
                });
            });
        },
    });

    const getFixStatus = useCallback(
        (repoId: number) => fixStatus[repoId] ?? null,
        [fixStatus],
    );

    return {
        startBatch,
        triggerFix,
        triggerSingleAnalysis,
        commitDocs,
        syncStatus,
        batchStatus,
        isPolling: !!currentWorkflowId && !isBatchComplete,
        getFixStatus,
    };
}

// -------------------------------------------------------------------
// usePortfolio — Portfolio Studio: generate, poll, publish
// -------------------------------------------------------------------
export function usePortfolio() {
    const [workflowId, setWorkflowId] = useState<string | null>(null);
    const [isComplete, setIsComplete] = useState(false);
    const [publishResult, setPublishResult] = useState<PortfolioPublishResponse | null>(null);

    const generate = useMutation({
        mutationFn: async (body: PortfolioGenerateRequest) => {
            const { data } = await gardenApi.generatePortfolio(body);
            return data.workflow_id;
        },
        onSuccess: (wfId) => {
            setWorkflowId(wfId);
            setIsComplete(false);
            setPublishResult(null);
        },
    });

    const { data: status, error: portfolioError } = useQuery({
        queryKey: ["portfolioStatus", workflowId],
        queryFn: async (): Promise<PortfolioStatus | null> => {
            if (!workflowId) return null;
            const { data } = await gardenApi.getPortfolioStatus(workflowId);
            return data;
        },
        enabled: !!workflowId && !isComplete,
        retry: false,
        refetchInterval: (query) => {
            if (query.state.status === "error") return false;
            if (query.state.dataUpdateCount > MAX_POLL_ATTEMPTS) return false;
            return 2000;
        },
    });

    useEffect(() => {
        if (portfolioError) {
            setIsComplete(true);
            return;
        }
        if (!status) return;
        if (status.stage === "draft_ready" || status.stage === "failed") {
            setIsComplete(true);
        }
    }, [status, portfolioError]);

    const publish = useMutation({
        mutationFn: async (readmeContent: string) => {
            const { data } = await gardenApi.publishPortfolio(readmeContent);
            return data;
        },
        onSuccess: (result) => {
            setPublishResult(result);
        },
    });

    const reset = useCallback(() => {
        setWorkflowId(null);
        setIsComplete(false);
        setPublishResult(null);
    }, []);

    return {
        generate,
        status,
        publish,
        publishResult,
        isPolling: !!workflowId && !isComplete,
        reset,
    };
}
