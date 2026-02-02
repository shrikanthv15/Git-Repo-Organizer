"use client";

import { useState } from "react";
import { DashboardSidebar } from "@/components/dashboard/sidebar";
import { DashboardHeader } from "@/components/dashboard/header";
import { RepoGrid } from "@/components/dashboard/repo-grid";
import { RepoDetailSheet } from "@/components/dashboard/repo-detail-sheet";

export interface Repo {
  id: string;
  name: string;
  isPrivate: boolean;
  healthScore: number;
  lastUpdated: string;
  openPRs: number;
  issues: number;
  language: string;
}

const mockRepos: Repo[] = [
  {
    id: "1",
    name: "github-gardener",
    isPrivate: false,
    healthScore: 94,
    lastUpdated: "2 hours ago",
    openPRs: 3,
    issues: 0,
    language: "TypeScript",
  },
  {
    id: "2",
    name: "portfolio-generator",
    isPrivate: true,
    healthScore: 78,
    lastUpdated: "5 hours ago",
    openPRs: 1,
    issues: 2,
    language: "Python",
  },
  {
    id: "3",
    name: "devops-pipeline",
    isPrivate: false,
    healthScore: 100,
    lastUpdated: "1 day ago",
    openPRs: 0,
    issues: 0,
    language: "Go",
  },
  {
    id: "4",
    name: "ml-inference-api",
    isPrivate: true,
    healthScore: 62,
    lastUpdated: "3 days ago",
    openPRs: 5,
    issues: 4,
    language: "Python",
  },
  {
    id: "5",
    name: "design-system",
    isPrivate: false,
    healthScore: 88,
    lastUpdated: "12 hours ago",
    openPRs: 2,
    issues: 1,
    language: "TypeScript",
  },
  {
    id: "6",
    name: "auth-service",
    isPrivate: true,
    healthScore: 45,
    lastUpdated: "1 week ago",
    openPRs: 0,
    issues: 7,
    language: "Rust",
  },
];

export default function DashboardPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [activeTab, setActiveTab] = useState("home");

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 2000);
  };

  return (
    <div className="flex h-screen bg-background relative overflow-hidden">
      {/* Background glow effects matching landing page */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 h-96 w-96 rounded-full bg-green-500/10 blur-3xl" />
        <div className="absolute -bottom-1/2 -right-1/4 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="absolute top-1/4 right-1/4 h-64 w-64 rounded-full bg-teal-500/5 blur-3xl" />
      </div>
      <DashboardSidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex flex-1 flex-col">
        <DashboardHeader onRefresh={handleRefresh} isLoading={isLoading} />
        <main className="flex-1 overflow-auto p-6">
          <RepoGrid
            repos={mockRepos}
            isLoading={isLoading}
            onRepoClick={setSelectedRepo}
          />
        </main>
      </div>
      <RepoDetailSheet
        repo={selectedRepo}
        open={!!selectedRepo}
        onClose={() => setSelectedRepo(null)}
      />
    </div>
  );
}
