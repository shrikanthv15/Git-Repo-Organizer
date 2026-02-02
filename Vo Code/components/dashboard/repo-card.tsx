"use client";

import { useState } from "react";
import { Lock, Globe, GitPullRequest, AlertCircle, Wrench } from "lucide-react";
import type { Repo } from "@/app/dashboard/page";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RepoCardProps {
  repo: Repo;
  onClick: () => void;
}

function HealthScoreRing({
  score,
  size = 48,
}: {
  score: number;
  size?: number;
}) {
  const strokeWidth = 4;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const getColor = (score: number) => {
    if (score >= 80) return "stroke-green-400";
    if (score >= 60) return "stroke-amber-400";
    return "stroke-red-400";
  };

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="-rotate-90" width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-white/10"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={cn("transition-all duration-500", getColor(score))}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-foreground">
        {score}
      </span>
    </div>
  );
}

export function RepoCard({ repo, onClick }: RepoCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="group relative w-full text-left"
    >
      {/* Hover gradient border effect matching landing page */}
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 from-green-500/50 via-emerald-500/50 to-teal-500/50 blur-sm" />
      
      <div className={cn(
        "relative rounded-2xl border border-white/10 bg-card/50 backdrop-blur-sm p-4 transition-all duration-300",
        "hover:border-white/20 hover:bg-card/80"
      )}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-foreground">{repo.name}</h3>
              {repo.isPrivate ? (
                <Lock className="h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <Globe className="h-3.5 w-3.5 text-muted-foreground" />
              )}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{repo.language}</p>
          </div>
          <HealthScoreRing score={repo.healthScore} />
        </div>

        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-muted-foreground/70">Updated {repo.lastUpdated}</p>
          <div className="flex items-center gap-2">
            {repo.openPRs > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
                <GitPullRequest className="h-3 w-3" />
                {repo.openPRs} PR
              </span>
            )}
            {repo.issues > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-400">
                <AlertCircle className="h-3 w-3" />
                {repo.issues}
              </span>
            )}
          </div>
        </div>

        <div
          className={cn(
            "absolute bottom-4 right-4 transition-all duration-200",
            isHovered ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
          )}
        >
          <Button
            size="sm"
            className="h-7 bg-gradient-to-r from-green-500 to-emerald-500 text-xs text-background font-medium hover:from-green-400 hover:to-emerald-400 shadow-[0_0_15px_rgba(34,197,94,0.3)]"
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <Wrench className="mr-1.5 h-3 w-3" />
            Quick Fix
          </Button>
        </div>
      </div>
    </button>
  );
}
