import { useState, useEffect, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { gardenApi } from "@/services/api";
import type { Repo, BatchStatus } from "@/types/api";

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
// useRepos — replaces the old lib/use-repos.ts (no mock data)
// -------------------------------------------------------------------
export function useRepos() {
    return useQuery({
        queryKey: ["repos"],
        queryFn: async (): Promise<Repo[]> => {
            const { data } = await gardenApi.getRepos();
            return Array.isArray(data) ? data : [];
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
        mutationFn: async (limit: number = 5) => {
            const { data } = await gardenApi.startBatchAnalysis(limit);
            return data.workflow_id;
        },
        onSuccess: (workflowId) => {
            setCurrentWorkflowId(workflowId);
            setIsBatchComplete(false);
        },
    });

    // Polling Query for batch status
    const { data: batchStatus } = useQuery({
        queryKey: ["batchStatus", currentWorkflowId],
        queryFn: async (): Promise<BatchStatus | null> => {
            if (!currentWorkflowId) return null;
            const { data } = await gardenApi.getBatchStatus(currentWorkflowId);
            return data;
        },
        enabled: !!currentWorkflowId && !isBatchComplete,
        refetchInterval: 2000,
    });

    // Merge batch results into the repos cache
    useEffect(() => {
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
    }, [batchStatus, queryClient]);

    // Fix Mutation (Janitor)
    const triggerFix = useMutation({
        mutationFn: async (repoId: number) => {
            const { data } = await gardenApi.triggerFix(repoId);

            // Poll DB for pending_fix_url
            let foundUrl: string | null = null;
            let attempts = 0;
            const maxAttempts = 60; // 60 seconds

            while (!foundUrl && attempts < maxAttempts) {
                await new Promise((r) => setTimeout(r, 1000));
                attempts++;
                try {
                    // Fetch all repos to check if this specific repo has the update
                    const res = await gardenApi.getRepos();
                    const repos = Array.isArray(res.data) ? res.data : [];
                    const updatedRepo = repos.find((r) => r.id === repoId);

                    if (updatedRepo?.health?.pending_fix_url) {
                        foundUrl = updatedRepo.health.pending_fix_url;
                        break;
                    }
                } catch (e) {
                    console.error("Polling error", e);
                }
            }

            if (!foundUrl) throw new Error("Janitor timeout: PR URL not found after 60s");

            return { repoId, workflowId: data.workflow_id, prUrl: foundUrl };
        },
        onMutate: (repoId) => {
            setFixStatus((prev) => ({ ...prev, [repoId]: "pending" }));
        },
        onSuccess: ({ repoId, prUrl }) => {
            setFixStatus((prev) => ({ ...prev, [repoId]: "done" }));

            // Update cache with the confirmed URL
            queryClient.setQueryData<Repo[]>(["repos"], (old) => {
                if (!old) return [];
                return old.map((repo) => {
                    if (repo.id === repoId && repo.health) {
                        return {
                            ...repo,
                            health: {
                                ...repo.health,
                                pending_fix_url: prUrl,
                            },
                        };
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

    // Single Analysis Mutation
    const triggerSingleAnalysis = useMutation({
        mutationFn: async (repoId: number) => {
            const { data } = await gardenApi.triggerAnalysis(repoId);
            // Poll for result
            let result = null;
            let attempts = 0;
            while (!result && attempts < 30) {
                await new Promise((r) => setTimeout(r, 1000));
                attempts++;
                try {
                    const status = await gardenApi.getBatchStatus(data.workflow_id);
                    if (status.data.results && status.data.results.length > 0) {
                        result = status.data.results[0];
                        break;
                    }
                } catch (e) {
                    console.error("Polling error", e);
                }
            }
            if (!result) throw new Error("Analysis timeout");
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
        batchStatus,
        isPolling: !!currentWorkflowId && !isBatchComplete,
        getFixStatus,
    };
}
