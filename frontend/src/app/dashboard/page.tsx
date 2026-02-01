"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
    Rocket,
    Lock,
    Globe,
    Zap,
    AlertCircle,
    CheckCircle,
    GitPullRequest,
    WifiOff,
    ChevronRight,
} from "lucide-react";
import { useGardener, useRepos, useHealthCheck } from "@/hooks/use-gardener";
import { cn } from "@/lib/utils";
import type { Repo } from "@/types/api";

export default function DashboardPage() {
    const router = useRouter();

    // 1. Health check
    const { data: health, isError: isBackendDown } = useHealthCheck();

    // 2. Auth guard
    useEffect(() => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (!token) router.push("/login");
        }
    }, [router]);

    // 3. Fetch repos
    const { data: repos, isLoading, isError } = useRepos();

    // 4. Batch analysis
    const { startBatch, batchStatus, isPolling } = useGardener();

    // Count summaries
    const healthyCount = repos?.filter((r) => r.health && r.health.health_score >= 80).length ?? 0;
    const needsWorkCount = repos?.filter((r) => r.health && r.health.health_score < 80).length ?? 0;
    const unscannedCount = repos?.filter((r) => !r.health).length ?? 0;

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
                <div className="text-center">
                    <Rocket className="mx-auto h-8 w-8 animate-spin text-blue-600" />
                    <p className="mt-4 text-gray-500">Loading repositories...</p>
                </div>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
                <div className="text-center text-red-500">
                    <AlertCircle className="mx-auto mb-2 h-8 w-8" />
                    <h2 className="text-xl font-bold">Connection Failed</h2>
                    <p className="mt-1 text-sm text-gray-500">
                        Unable to fetch repository data from the backend.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-6 text-gray-900 dark:bg-black dark:text-gray-50">
            <div className="mx-auto max-w-7xl">
                {/* Backend health warning */}
                {isBackendDown && (
                    <div className="mb-4 flex items-center gap-2 rounded-lg bg-yellow-50 px-4 py-3 text-sm text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                        <WifiOff className="h-4 w-4 shrink-0" />
                        Backend is unreachable. Some features may not work.
                    </div>
                )}

                {/* Header */}
                <header className="mb-10 border-b border-gray-200 pb-6 dark:border-zinc-800">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Rocket className="h-8 w-8 text-blue-600" />
                            <h1 className="text-3xl font-extrabold tracking-tight">
                                Mission Control
                            </h1>
                            {health && (
                                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                                    Online
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => startBatch.mutate(5)}
                                disabled={isPolling || startBatch.isPending}
                                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                            >
                                <Zap className="h-4 w-4" />
                                {isPolling ? "Analyzing..." : "Analyze All"}
                            </button>
                            <button
                                onClick={() => {
                                    localStorage.removeItem("access_token");
                                    router.push("/login");
                                }}
                                className="text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                            >
                                Sign Out
                            </button>
                        </div>
                    </div>

                    {/* Batch progress bar */}
                    {isPolling && batchStatus && batchStatus.total > 0 && (
                        <div className="mt-6">
                            <div className="mb-2 flex justify-between text-xs font-medium text-gray-500">
                                <span>
                                    Analyzed {batchStatus.completed}/{batchStatus.total}
                                </span>
                                <span>
                                    {Math.round(
                                        (batchStatus.completed / batchStatus.total) * 100,
                                    )}
                                    %
                                </span>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-zinc-800">
                                <div
                                    className="h-full bg-blue-600 transition-all duration-500 ease-out"
                                    style={{
                                        width: `${(batchStatus.completed / batchStatus.total) * 100}%`,
                                    }}
                                />
                            </div>
                        </div>
                    )}
                </header>

                {/* Summary counters */}
                {repos && repos.length > 0 && (
                    <div className="mb-8 grid grid-cols-3 gap-4">
                        <SummaryCard
                            label="Healthy"
                            count={healthyCount}
                            color="text-green-600 dark:text-green-400"
                            bg="bg-green-50 dark:bg-green-900/10"
                        />
                        <SummaryCard
                            label="Needs Work"
                            count={needsWorkCount}
                            color="text-red-600 dark:text-red-400"
                            bg="bg-red-50 dark:bg-red-900/10"
                        />
                        <SummaryCard
                            label="Unscanned"
                            count={unscannedCount}
                            color="text-gray-500 dark:text-gray-400"
                            bg="bg-gray-100 dark:bg-zinc-900"
                        />
                    </div>
                )}

                {/* Repo Grid */}
                {repos && repos.length === 0 ? (
                    <div className="py-20 text-center text-gray-400">
                        No repositories found. Make sure your GitHub token has the
                        <code className="mx-1 rounded bg-gray-100 px-1 dark:bg-zinc-800">
                            repo
                        </code>
                        scope.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {repos?.map((repo) => (
                            <RepoCard
                                key={repo.id}
                                repo={repo}
                                onClick={() => router.push(`/repo/${repo.id}`)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

// -------------------------------------------------------------------
// SummaryCard — top-level counter
// -------------------------------------------------------------------
function SummaryCard({
    label,
    count,
    color,
    bg,
}: {
    label: string;
    count: number;
    color: string;
    bg: string;
}) {
    return (
        <div className={cn("rounded-xl p-4 text-center", bg)}>
            <p className={cn("text-3xl font-extrabold", color)}>{count}</p>
            <p className="mt-1 text-xs font-medium text-gray-500">{label}</p>
        </div>
    );
}

// -------------------------------------------------------------------
// RepoCard — clickable summary tile
// -------------------------------------------------------------------
function RepoCard({ repo, onClick }: { repo: Repo; onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className="group flex w-full flex-col justify-between rounded-xl border bg-white p-5 text-left shadow-sm transition-all hover:shadow-md hover:border-blue-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600"
        >
            <div>
                {/* Title row */}
                <div className="flex items-start justify-between">
                    <h3 className="text-base font-bold tracking-tight group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        {repo.name}
                    </h3>
                    <div className="flex items-center gap-1.5">
                        {/* Health badge */}
                        {repo.health != null && (
                            <span
                                className={cn(
                                    "rounded px-2 py-0.5 text-xs font-bold",
                                    repo.health.health_score >= 80
                                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                        : repo.health.health_score >= 50
                                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
                                )}
                            >
                                {repo.health.health_score}%
                            </span>
                        )}

                        {/* Pending fix badge */}
                        {repo.health?.pending_fix_url && (
                            <span className="flex items-center gap-1 rounded bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                                <GitPullRequest className="h-3 w-3" />
                                PR
                            </span>
                        )}

                        {/* Visibility icon */}
                        {repo.private ? (
                            <Lock className="h-3.5 w-3.5 text-gray-400" />
                        ) : (
                            <Globe className="h-3.5 w-3.5 text-gray-400" />
                        )}
                    </div>
                </div>

                {/* Description */}
                <p className="mt-1.5 line-clamp-2 text-sm text-gray-500">
                    {repo.description || "No description provided."}
                </p>
            </div>

            {/* Footer */}
            <div className="mt-4 flex items-center justify-between">
                <span className="font-mono text-xs text-gray-400">
                    {repo.full_name}
                </span>
                <ChevronRight className="h-4 w-4 text-gray-300 transition-transform group-hover:translate-x-0.5 group-hover:text-blue-500" />
            </div>
        </button>
    );
}
