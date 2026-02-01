import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { gardenApi } from "@/services/api";
import { RepoHealth, BatchStatus } from "@/types/api";

export function useGardener() {
    const queryClient = useQueryClient();
    const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
    const [isBatchComplete, setIsBatchComplete] = useState(false);

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

    // Polling Query
    const { data: batchStatus } = useQuery({
        queryKey: ["batchStatus", currentWorkflowId],
        queryFn: async () => {
            if (!currentWorkflowId) return null;
            const { data } = await gardenApi.getBatchStatus(currentWorkflowId);
            return data;
        },
        enabled: !!currentWorkflowId && !isBatchComplete,
        refetchInterval: 2000, // Poll every 2 seconds
    });

    // Effect to merge results
    useEffect(() => {
        if (batchStatus) {
            if (batchStatus.completed === batchStatus.total && batchStatus.total > 0) {
                setIsBatchComplete(true);
                setCurrentWorkflowId(null); // Stop polling
            }

            // Merge results into Repos Cache if we have completed items
            if (batchStatus.results && batchStatus.results.length > 0) {
                queryClient.setQueryData<any>(["repos"], (oldRepos: any[]) => {
                    if (!oldRepos) return oldRepos;
                    return oldRepos.map((repo) => {
                        const healthUpdate = batchStatus.results.find(
                            (r) => r.repo_name === repo.name
                        );
                        return healthUpdate ? { ...repo, health: healthUpdate } : repo;
                    });
                });
            }
        }
    }, [batchStatus, queryClient]);

    // Fix Mutation
    const triggerFix = useMutation({
        mutationFn: async (repoId: number) => {
            return gardenApi.triggerFix(repoId);
        },
    });

    // Single Analysis Mutation
    const triggerSingleAnalysis = useMutation({
        mutationFn: async (repoId: number) => {
            return gardenApi.triggerAnalysis(repoId);
        },
        onSuccess: () => {
            // Invalidate repos to refresh health status
            queryClient.invalidateQueries({ queryKey: ["repos"] });
        }
    });

    return {
        startBatch,
        triggerFix,
        triggerSingleAnalysis,
        batchStatus,
        isPolling: !!currentWorkflowId && !isBatchComplete,
    };
}
