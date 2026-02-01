"use client";

import { useRepos } from "@/lib/use-repos";
import { cn } from "@/lib/utils";

export function RepoGrid() {
    const { data: repos, isLoading, isError } = useRepos();

    if (isLoading) {
        return (
            <div className="flex h-64 items-center justify-center text-lg font-medium text-gray-500 animate-pulse">
                Scanning GitHub...
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex h-64 items-center justify-center text-red-500 font-bold">
                System Failure: Check Connection
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {repos?.map((repo) => (
                <div
                    key={repo.id}
                    className="flex flex-col justify-between rounded-xl border bg-white p-6 shadow-sm transition-all hover:shadow-md dark:bg-zinc-900 dark:border-zinc-800"
                >
                    <div className="space-y-2">
                        <h3 className="text-xl font-bold tracking-tight">{repo.name}</h3>
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-500">Health Score:</span>
                            <span
                                className={cn(
                                    "font-mono font-bold",
                                    repo.health_score > 80
                                        ? "text-green-600"
                                        : repo.health_score > 50
                                            ? "text-yellow-600"
                                            : "text-red-600"
                                )}
                            >
                                {repo.health_score}%
                            </span>
                        </div>
                    </div>

                    <div className="mt-6">
                        {repo.needs_gardening ? (
                            <button className="w-full rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-700">
                                Start Gardening
                            </button>
                        ) : (
                            <button
                                disabled
                                className="w-full cursor-not-allowed rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-400 dark:bg-zinc-800 dark:text-gray-600"
                            >
                                Healthy
                            </button>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}
