"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Rocket, AlertCircle } from "lucide-react";
import { useGardener, useRepos, useHealthCheck } from "@/hooks/use-gardener";
import { DashboardSidebar } from "@/components/dashboard/sidebar";
import { DashboardHeader } from "@/components/dashboard/header";
import { RepoGrid } from "@/components/dashboard/repo-grid";
import { RepoDetailSheet } from "@/components/dashboard/repo-detail-sheet";
import type { Repo } from "@/types/api";

export default function DashboardPage() {
    const router = useRouter();
    const queryClient = useQueryClient();

    // 1. Health check
    const { data: health, isError: isBackendDown } = useHealthCheck();

    // 2. Auth guard
    useEffect(() => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (!token) router.push("/");
        }
    }, [router]);

    // 3. Fetch repos
    const { data: repos, isLoading, isError, isFetching } = useRepos();

    // 4. Batch analysis
    const { startBatch, batchStatus, isPolling } = useGardener();

    // 5. Selected repo for detail sheet
    const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
    const [activeTab, setActiveTab] = useState("home");

    const handleAnalyzeAll = () => {
        startBatch.mutate(5);
    };

    // Refresh: invalidate cache and refetch fresh data from DB
    const handleRefresh = () => {
        queryClient.invalidateQueries({ queryKey: ["repos"] });
    };

    // Full-screen loading
    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <div className="text-center">
                    <Rocket className="mx-auto h-8 w-8 animate-spin text-green-400" />
                    <p className="mt-4 text-muted-foreground">Loading repositories...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (isError) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <div className="text-center text-red-400">
                    <AlertCircle className="mx-auto mb-2 h-8 w-8" />
                    <h2 className="text-xl font-bold">Connection Failed</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Unable to fetch repository data from the backend.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-background relative overflow-hidden">
            {/* Background glow effects */}
            <div className="pointer-events-none absolute inset-0 overflow-hidden">
                <div className="absolute -top-1/2 -left-1/4 h-96 w-96 rounded-full bg-green-500/10 blur-3xl" />
                <div className="absolute -bottom-1/2 -right-1/4 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
                <div className="absolute top-1/4 right-1/4 h-64 w-64 rounded-full bg-teal-500/5 blur-3xl" />
            </div>

            {/* Sidebar */}
            <DashboardSidebar activeTab={activeTab} onTabChange={setActiveTab} />

            {/* Main content */}
            <div className="flex flex-1 flex-col">
                {/* Header with Analyze All and Refresh buttons */}
                <DashboardHeader
                    onAnalyzeAll={handleAnalyzeAll}
                    onRefresh={handleRefresh}
                    isAnalyzing={isPolling || startBatch.isPending}
                    isRefreshing={isFetching && !isLoading}
                    isBackendDown={isBackendDown}
                    batchStatus={batchStatus}
                />

                {/* Repo grid */}
                <main className="flex-1 overflow-auto p-6">
                    <RepoGrid
                        repos={repos ?? []}
                        isLoading={isLoading}
                        onRepoClick={setSelectedRepo}
                    />
                </main>
            </div>

            {/* Repo detail sheet */}
            <RepoDetailSheet
                repo={selectedRepo}
                open={!!selectedRepo}
                onClose={() => setSelectedRepo(null)}
            />
        </div>
    );
}

