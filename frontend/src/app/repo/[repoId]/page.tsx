"use client";

import { use, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
    ArrowLeft,
    ExternalLink,
    GitPullRequest,
    ShieldAlert,
    ShieldCheck,
    CheckCircle,
    Wrench,
    Loader2,
    AlertCircle,
    Clock,
    Rocket,
    FileText,
    Eye,
    Check,
    X,
} from "lucide-react";
import { useRepo, useGardener } from "@/hooks/use-gardener";
import { cn } from "@/lib/utils";
import type { Repo } from "@/types/api";

export default function RepoDetailPage({
    params,
}: {
    params: Promise<{ repoId: string }>;
}) {
    const { repoId: repoIdStr } = use(params);
    const repoId = Number(repoIdStr);
    const router = useRouter();

    // Auth guard
    useEffect(() => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (!token) router.push("/");
        }
    }, [router]);

    const { data: repo, isLoading, isError } = useRepo(repoId);
    const { triggerFix, triggerSingleAnalysis, commitDocs, getFixStatus } = useGardener();

    const fixStatus = getFixStatus(repoId);
    const hasDraft = !!(repo?.draft_proposal && Object.keys(repo.draft_proposal).length > 0);

    const handleFix = useCallback(() => {
        triggerFix.mutate(repoId);
    }, [triggerFix, repoId]);

    const handleAnalyze = useCallback(() => {
        triggerSingleAnalysis.mutate(repoId);
    }, [triggerSingleAnalysis, repoId]);

    // Loading
    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
                <Rocket className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        );
    }

    // 404
    if (isError || repo === null || repo === undefined) {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50 dark:bg-black">
                <ShieldAlert className="h-12 w-12 text-red-500" />
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Repository Not Found
                </h1>
                <p className="text-sm text-gray-500">
                    No repository with ID <code className="rounded bg-gray-100 px-1 dark:bg-zinc-800">{repoIdStr}</code> was found in your account.
                </p>
                <button
                    onClick={() => router.push("/dashboard")}
                    className="mt-4 flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to Dashboard
                </button>
            </div>
        );
    }

    const health = repo.health;
    const score = health?.health_score ?? null;
    const hasPendingFix = !!health?.pending_fix_url;

    return (
        <div className="min-h-screen bg-gray-50 p-6 text-gray-900 dark:bg-black dark:text-gray-50">
            <div className="mx-auto max-w-5xl">
                {/* Back nav */}
                <button
                    onClick={() => router.push("/dashboard")}
                    className="mb-6 flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Dashboard
                </button>

                {/* Header */}
                <header className="mb-8 border-b border-gray-200 pb-6 dark:border-zinc-800">
                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="text-3xl font-extrabold tracking-tight">
                                {repo.name}
                            </h1>
                            <p className="mt-1 text-sm text-gray-500">
                                {repo.full_name}
                            </p>
                            {repo.description && (
                                <p className="mt-2 max-w-xl text-gray-600 dark:text-gray-400">
                                    {repo.description}
                                </p>
                            )}
                        </div>
                        <a
                            href={repo.html_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 dark:border-zinc-700 dark:text-gray-300 dark:hover:bg-zinc-800"
                        >
                            <ExternalLink className="h-4 w-4" />
                            View on GitHub
                        </a>
                    </div>
                    {health && (
                        <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
                            <Clock className="h-3.5 w-3.5" />
                            Last activity:{" "}
                            {new Date(health.last_commit_date).toLocaleDateString(undefined, {
                                year: "numeric",
                                month: "short",
                                day: "numeric",
                            })}
                        </div>
                    )}
                </header>

                {/* Draft Proposal Review — full-width when active */}
                {hasDraft && repo.draft_proposal ? (
                    <ProposalReview
                        repoId={repoId}
                        draft={repo.draft_proposal}
                        commitDocs={commitDocs}
                    />
                ) : (
                    /* Two-column layout */
                    <div className="grid grid-cols-1 gap-8 lg:grid-cols-5">
                        {/* Left: Health Gauge + Issues (3 cols) */}
                        <div className="lg:col-span-3 space-y-6">
                            {/* Health Gauge */}
                            <div className="rounded-xl border bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                                <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
                                    Health Score
                                </h2>
                                {score !== null ? (
                                    <div className="flex items-center gap-8">
                                        <HealthGauge score={score} />
                                        <div>
                                            <p className={cn(
                                                "text-lg font-bold",
                                                score >= 80
                                                    ? "text-green-600 dark:text-green-400"
                                                    : score >= 50
                                                        ? "text-yellow-600 dark:text-yellow-400"
                                                        : "text-red-600 dark:text-red-400",
                                            )}>
                                                {score >= 80
                                                    ? "Looking Good"
                                                    : score >= 50
                                                        ? "Needs Attention"
                                                        : "Critical"}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {score >= 80
                                                    ? "This repository is well-maintained."
                                                    : `${health!.issues.length} issue${health!.issues.length !== 1 ? "s" : ""} detected.`}
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-3 text-gray-400">
                                        <ShieldAlert className="h-6 w-6" />
                                        <p className="text-sm">
                                            Not yet analyzed. Run an analysis to see the health score.
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Issues list */}
                            {health && health.issues.length > 0 && (
                                <div className="rounded-xl border bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                                    <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
                                        Issues Found
                                    </h2>
                                    <ul className="space-y-3">
                                        {health.issues.map((issue, idx) => (
                                            <li
                                                key={idx}
                                                className="flex items-start gap-3 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/15 dark:text-red-300"
                                            >
                                                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                                                {issue}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>

                        {/* Right: Action Panel (2 cols) */}
                        <div className="lg:col-span-2">
                            <div className="sticky top-6 rounded-xl border bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                                <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
                                    Actions
                                </h2>

                                <ActionPanel
                                    repo={repo}
                                    score={score}
                                    hasPendingFix={hasPendingFix}
                                    fixStatus={fixStatus}
                                    onFix={handleFix}
                                    onAnalyze={handleAnalyze}
                                    isAnalyzing={triggerSingleAnalysis.isPending}
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// -------------------------------------------------------------------
// HealthGauge — circular SVG progress ring
// -------------------------------------------------------------------
function HealthGauge({ score }: { score: number }) {
    const radius = 52;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    const color =
        score >= 80
            ? "stroke-green-500"
            : score >= 50
                ? "stroke-yellow-500"
                : "stroke-red-500";

    return (
        <div className="relative h-32 w-32 shrink-0">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
                {/* Background ring */}
                <circle
                    cx="60"
                    cy="60"
                    r={radius}
                    fill="none"
                    className="stroke-gray-200 dark:stroke-zinc-800"
                    strokeWidth="10"
                />
                {/* Score ring */}
                <circle
                    cx="60"
                    cy="60"
                    r={radius}
                    fill="none"
                    className={cn(color, "transition-all duration-700 ease-out")}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                />
            </svg>
            {/* Center text */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span
                    className={cn(
                        "text-3xl font-extrabold",
                        score >= 80
                            ? "text-green-600 dark:text-green-400"
                            : score >= 50
                                ? "text-yellow-600 dark:text-yellow-400"
                                : "text-red-600 dark:text-red-400",
                    )}
                >
                    {score}
                </span>
                <span className="text-xs text-gray-400">/ 100</span>
            </div>
        </div>
    );
}

// -------------------------------------------------------------------
// ActionPanel — primary action for the repo
// -------------------------------------------------------------------
function ActionPanel({
    repo,
    score,
    hasPendingFix,
    fixStatus,
    onFix,
    onAnalyze,
    isAnalyzing,
}: {
    repo: Repo;
    score: number | null;
    hasPendingFix: boolean;
    fixStatus: "pending" | "done" | null;
    onFix: () => void;
    onAnalyze: () => void;
    isAnalyzing: boolean;
}) {
    // Fix triggered this session, waiting
    if (fixStatus === "pending") {
        return (
            <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-green-50 p-4 dark:bg-green-900/15">
                    <Loader2 className="h-5 w-5 animate-spin text-green-600" />
                    <div>
                        <p className="font-semibold text-green-700 dark:text-green-400">
                            Gardener Working...
                        </p>
                        <p className="text-xs text-green-600/70 dark:text-green-500/70">
                            Generating documentation for review.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Fix triggered this session, done — draft ready (review UI shown above)
    if (fixStatus === "done") {
        return (
            <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-blue-50 p-4 dark:bg-blue-900/15">
                    <CheckCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    <div>
                        <p className="font-semibold text-blue-700 dark:text-blue-400">
                            Draft Ready
                        </p>
                        <p className="text-xs text-blue-600/70 dark:text-blue-500/70">
                            Review the generated docs above.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Pending fix detected from analysis (PR already exists on GitHub)
    if (hasPendingFix && repo.health?.pending_fix_url) {
        return (
            <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-purple-50 p-4 dark:bg-purple-900/15">
                    <GitPullRequest className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    <div>
                        <p className="font-semibold text-purple-700 dark:text-purple-400">
                            PR Already Open
                        </p>
                        <p className="text-xs text-purple-600/70 dark:text-purple-500/70">
                            A Gardener fix is waiting for review.
                        </p>
                    </div>
                </div>
                <a
                    href={repo.health.pending_fix_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-purple-700"
                >
                    <GitPullRequest className="h-4 w-4" />
                    View Pull Request
                </a>
            </div>
        );
    }

    // Perfect score — no action needed
    if (score !== null && score >= 100) {
        return (
            <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-green-50 p-4 dark:bg-green-900/15">
                    <ShieldCheck className="h-5 w-5 text-green-600 dark:text-green-400" />
                    <div>
                        <p className="font-semibold text-green-700 dark:text-green-400">
                            Healthy
                        </p>
                        <p className="text-xs text-green-600/70 dark:text-green-500/70">
                            No action needed. This repo is well-maintained.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Score < 100 -> offer auto-fix
    if (score !== null && score < 100) {
        return (
            <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-red-50 p-4 dark:bg-red-900/15">
                    <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400" />
                    <div>
                        <p className="font-semibold text-red-700 dark:text-red-400">
                            Needs Repair
                        </p>
                        <p className="text-xs text-red-600/70 dark:text-red-500/70">
                            The Gardener can generate a README fix for this repo.
                        </p>
                    </div>
                </div>
                <button
                    onClick={onFix}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-green-700"
                >
                    <Wrench className="h-4 w-4" />
                    Auto-Fix
                </button>
            </div>
        );
    }

    // No health data -> offer analysis
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-lg bg-gray-100 p-4 dark:bg-zinc-800">
                <ShieldAlert className="h-5 w-5 text-gray-400" />
                <div>
                    <p className="font-semibold text-gray-700 dark:text-gray-300">
                        Not Analyzed
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Run an analysis to check this repository&apos;s health.
                    </p>
                </div>
            </div>
            <button
                onClick={onAnalyze}
                disabled={isAnalyzing}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-black px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-800 disabled:opacity-70 dark:bg-white dark:text-black dark:hover:bg-gray-200"
            >
                {isAnalyzing ? (
                    <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Analyzing...
                    </>
                ) : (
                    "Analyze Repository"
                )}
            </button>
        </div>
    );
}

// -------------------------------------------------------------------
// ProposalReview — human-in-the-loop review UI for generated docs
// -------------------------------------------------------------------
function ProposalReview({
    repoId,
    draft,
    commitDocs,
}: {
    repoId: number;
    draft: Record<string, string>;
    commitDocs: ReturnType<typeof useGardener>["commitDocs"];
}) {
    const filenames = Object.keys(draft);
    const [activeTab, setActiveTab] = useState(filenames[0] ?? "");
    const [selected, setSelected] = useState<Record<string, boolean>>(() =>
        Object.fromEntries(filenames.map((f) => [f, true])),
    );
    const [committed, setCommitted] = useState(false);
    const [prUrl, setPrUrl] = useState<string | null>(null);

    const toggleFile = (filename: string) => {
        setSelected((prev) => ({ ...prev, [filename]: !prev[filename] }));
    };

    const selectedFiles = filenames.filter((f) => selected[f]);

    const handleCommit = () => {
        if (selectedFiles.length === 0) return;
        commitDocs.mutate(
            { repoId, selectedFiles },
            {
                onSuccess: ({ prUrl: url }) => {
                    setCommitted(true);
                    setPrUrl(url);
                },
            },
        );
    };

    if (committed && prUrl) {
        return (
            <div className="rounded-xl border bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex flex-col items-center gap-4 text-center">
                    <CheckCircle className="h-12 w-12 text-green-500" />
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                        Pull Request Created
                    </h2>
                    <p className="text-sm text-gray-500">
                        Your selected documentation files have been committed.
                    </p>
                    <a
                        href={prUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-lg bg-purple-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-purple-700"
                    >
                        <GitPullRequest className="h-4 w-4" />
                        View Pull Request
                    </a>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="rounded-xl border bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Eye className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        <div>
                            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                                Review Proposal
                            </h2>
                            <p className="text-sm text-gray-500">
                                The Gardener generated {filenames.length} file{filenames.length !== 1 ? "s" : ""}. Review and toggle which to include.
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleCommit}
                        disabled={selectedFiles.length === 0 || commitDocs.isPending}
                        className="flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {commitDocs.isPending ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Committing...
                            </>
                        ) : (
                            <>
                                <Check className="h-4 w-4" />
                                Approve &amp; Commit ({selectedFiles.length})
                            </>
                        )}
                    </button>
                </div>

                {commitDocs.isError && (
                    <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/15 dark:text-red-300">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        Failed to commit. Please try again.
                    </div>
                )}
            </div>

            {/* Tabs + File toggles */}
            <div className="rounded-xl border bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                {/* Tab bar */}
                <div className="flex border-b border-gray-200 dark:border-zinc-800">
                    {filenames.map((filename) => (
                        <button
                            key={filename}
                            onClick={() => setActiveTab(filename)}
                            className={cn(
                                "flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors",
                                activeTab === filename
                                    ? "border-b-2 border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                                    : "text-gray-500 hover:text-gray-900 dark:hover:text-gray-300",
                            )}
                        >
                            <FileText className="h-4 w-4" />
                            {filename}
                        </button>
                    ))}
                </div>

                {/* Toggle + Preview */}
                <div className="p-6">
                    {/* Include toggle */}
                    <div className="mb-4 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Include this file
                        </span>
                        <button
                            onClick={() => toggleFile(activeTab)}
                            className={cn(
                                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors",
                                selected[activeTab]
                                    ? "bg-green-500"
                                    : "bg-gray-300 dark:bg-zinc-600",
                            )}
                        >
                            <span
                                className={cn(
                                    "inline-block h-5 w-5 translate-y-0.5 rounded-full bg-white shadow transition-transform",
                                    selected[activeTab]
                                        ? "translate-x-5"
                                        : "translate-x-0.5",
                                )}
                            />
                        </button>
                    </div>

                    {/* Markdown preview */}
                    <div
                        className={cn(
                            "prose prose-sm dark:prose-invert max-w-none rounded-lg border p-6 overflow-auto max-h-[600px]",
                            selected[activeTab]
                                ? "border-gray-200 bg-gray-50 dark:border-zinc-700 dark:bg-zinc-800/50"
                                : "border-dashed border-gray-300 bg-gray-100 opacity-50 dark:border-zinc-600 dark:bg-zinc-800/30",
                        )}
                    >
                        <ReactMarkdown>{draft[activeTab] ?? ""}</ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
}
