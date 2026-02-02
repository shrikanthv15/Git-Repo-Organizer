"use client";

import type { Repo } from "@/app/dashboard/page";
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

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {repos.map((repo) => (
        <RepoCard key={repo.id} repo={repo} onClick={() => onRepoClick(repo)} />
      ))}
    </div>
  );
}
