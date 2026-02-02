"use client";

import type { Repo } from "@/types/api";
import { RepoCard } from "./repo-card";
import { RepoCardSkeleton } from "./repo-card-skeleton";

interface RepoGridProps {
    repos: Repo[];
    isLoading: boolean;
    onRepoClick: (repo: Repo) => void;
}

export function RepoGrid({ repos, isLoading, onRepoClick }: RepoGridProps) {
    if (isLoading) {
        return (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                    <RepoCardSkeleton key={i} />
                ))}
            </div>
        );
    }

    if (repos.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-muted-foreground">
                    No repositories found. Make sure your GitHub token has the{" "}
                    <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-green-400">repo</code>
                    scope.
                </p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {repos.map((repo) => (
                <RepoCard key={repo.id} repo={repo} onClick={() => onRepoClick(repo)} />
            ))}
        </div>
    );
}
