"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Repo } from "@/types/api";
import { Rocket, Lock, Globe, Zap, Wrench, AlertCircle, CheckCircle } from "lucide-react";
import { Providers } from "@/components/providers";
import { useGardener } from "@/hooks/use-gardener";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
    const router = useRouter();
    const { startBatch, triggerFix, triggerSingleAnalysis, batchStatus, isPolling } = useGardener();

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) {
            router.push("/login");
        }
    }, [router]);

    const {
        data: repos,
        isLoading,
        isError,
    } = useQuery({
        queryKey: ["repos"],
        queryFn: async () => {
            try {
                const response = await api.get<Repo[]>("/repos");
                console.log("[Dashboard] /repos fetch response:", response);

                if (Array.isArray(response.data)) {
                    return response.data;
                }

                console.error("[Dashboard] Expected array but got:", typeof response.data, response.data);
                return []; // Return empty array to prevent crash
            } catch (error) {
                console.error("[Dashboard] Error fetching repos:", error);
                throw error;
            }
        },
    });

    const handleFix = (repoId: number) => {
        triggerFix.mutate(repoId);
    };

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
                <div className="text-center">
                    <Rocket className="mx-auto h-8 w-8 animate-spin text-blue-600" />
                    <p className="mt-4 text-gray-500">Retrieving Mission Data...</p>
                </div>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
                <div className="text-center text-red-500">
                    <h2 className="text-xl font-bold">System Failure</h2>
                    <p>Unable to fetch repository data.</p>
                </div>
            </div>
        );
    }

    return (
        <Providers>
            <div className="min-h-screen bg-gray-50 p-6 text-gray-900 dark:bg-black dark:text-gray-50">
                <div className="mx-auto max-w-7xl">
                    {/* Header Area */}
                    <header className="mb-10 border-b border-gray-200 pb-6 dark:border-zinc-800">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <Rocket className="h-8 w-8 text-blue-600" />
                                <h1 className="text-3xl font-extrabold tracking-tight">
                                    Mission Control
                                </h1>
                            </div>
                            <div className="flex items-center gap-4">
                                <button
                                    onClick={() => startBatch.mutate(5)}
                                    disabled={isPolling || startBatch.isPending}
                                    className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                                >
                                    <Zap className="h-4 w-4" />
                                    {isPolling ? "Analyzing..." : "Batch Analyze"}
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

                        {/* Progress Bar */}
                        {isPolling && batchStatus && (
                            <div className="mt-6">
                                <div className="mb-2 flex justify-between text-xs font-medium text-gray-500">
                                    <span>
                                        Batch in progress... ({batchStatus.completed}/{batchStatus.total})
                                    </span>
                                    <span>
                                        {Math.round((batchStatus.completed / batchStatus.total) * 100)}%
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

                    {/* Repo Grid */}
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {repos?.map((repo) => (
                            <div
                                key={repo.id}
                                className="flex flex-col justify-between rounded-xl border bg-white p-6 shadow-sm transition-all hover:shadow-md dark:bg-zinc-900 dark:border-zinc-800"
                            >
                                <div>
                                    <div className="flex items-start justify-between">
                                        <h3 className="text-lg font-bold tracking-tight">
                                            {repo.name}
                                        </h3>
                                        <div className="flex items-center gap-2">
                                            {repo.health !== undefined && (
                                                <span className={cn(
                                                    "flex items-center gap-1 rounded px-2 py-0.5 text-xs font-bold",
                                                    repo.health.health_score >= 80 ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                                                        repo.health.health_score >= 50 ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                                                            "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                                                )}>
                                                    {repo.health.health_score}%
                                                </span>
                                            )}
                                            {repo.private ? (
                                                <Lock className="h-4 w-4 text-gray-400" />
                                            ) : (
                                                <Globe className="h-4 w-4 text-gray-400" />
                                            )}
                                        </div>
                                    </div>
                                    <p className="mt-2 text-sm text-gray-500 line-clamp-2">
                                        {repo.description || "No description provided."}
                                    </p>

                                    {/* Issues List */}
                                    {repo.health && repo.health.health_score < 80 && repo.health.issues.length > 0 && (
                                        <div className="mt-4 rounded-md bg-red-50 p-3 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300">
                                            <p className="font-semibold mb-1 flex items-center gap-1">
                                                <AlertCircle className="h-3 w-3" />
                                                Attention Needed:
                                            </p>
                                            <ul className="list-disc pl-4 space-y-1">
                                                {repo.health.issues.slice(0, 2).map((issue, idx) => (
                                                    <li key={idx}>{issue}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-6 flex items-center justify-between">
                                    <span className="text-xs font-mono text-gray-400">
                                        {repo.private ? "Private" : "Public"}
                                    </span>

                                    {repo.health && repo.health.health_score < 80 ? (
                                        <button
                                            onClick={() => handleFix(repo.id)}
                                            disabled={triggerFix.isPending}
                                            className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-700 disabled:opacity-70"
                                        >
                                            {triggerFix.isPending ? (
                                                <Rocket className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Wrench className="h-4 w-4" />
                                            )}
                                            Auto-Fix
                                        </button>
                                    ) : repo.health && repo.health.health_score >= 80 ? (
                                        <div className="flex items-center gap-2 text-sm font-semibold text-green-600 dark:text-green-500">
                                            <CheckCircle className="h-4 w-4" />
                                            Healthy
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => triggerSingleAnalysis.mutate(repo.id)}
                                            disabled={triggerSingleAnalysis.isPending}
                                            className="rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-800 dark:bg-white dark:text-black hover:dark:bg-gray-200 disabled:opacity-70"
                                        >
                                            {triggerSingleAnalysis.isPending ? "Analyzing..." : "Analyze"}
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </Providers>
    );
}
