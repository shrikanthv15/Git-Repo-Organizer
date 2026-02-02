"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
    ArrowLeft,
    Sparkles,
    Loader2,
    ExternalLink,
    Search,
    BarChart3,
    Cpu,
    Upload,
    CheckCircle,
    AlertCircle,
} from "lucide-react";
import { usePortfolio } from "@/hooks/use-gardener";
import { cn } from "@/lib/utils";

const STAGES: Record<string, { label: string; icon: typeof Search; index: number }> = {
    scanning: { label: "Scanning your repositories...", icon: Search, index: 0 },
    analyzing: { label: "Analyzing repo health scores...", icon: BarChart3, index: 1 },
    selecting: { label: "Identifying top projects...", icon: Sparkles, index: 2 },
    generating: { label: "Designing your profile...", icon: Cpu, index: 3 },
    publishing: { label: "Publishing to GitHub...", icon: Upload, index: 4 },
    complete: { label: "Profile Ready!", icon: CheckCircle, index: 5 },
    failed: { label: "Something went wrong", icon: AlertCircle, index: 5 },
};

export default function PortfolioPage() {
    const router = useRouter();
    const { generate, status, isPolling } = usePortfolio();

    // Auth guard
    useEffect(() => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (!token) router.push("/");
        }
    }, [router]);

    const isWorking = generate.isPending || isPolling;
    const isComplete = status?.stage === "complete";
    const isFailed = status?.stage === "failed";
    const currentStage = status?.stage ? STAGES[status.stage] : null;

    return (
        <div className="flex min-h-screen flex-col bg-gray-50 text-gray-900 dark:bg-black dark:text-gray-50">
            {/* Top bar */}
            <header className="border-b border-gray-200 px-6 py-4 dark:border-zinc-800">
                <div className="mx-auto flex max-w-4xl items-center gap-3">
                    <button
                        onClick={() => router.push("/dashboard")}
                        className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Dashboard
                    </button>
                </div>
            </header>

            {/* Main content */}
            <main className="flex flex-1 items-center justify-center p-6">
                <div className="w-full max-w-lg text-center">
                    {/* Hero */}
                    {!isWorking && !isComplete && !isFailed && (
                        <div className="space-y-6">
                            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg">
                                <Sparkles className="h-10 w-10 text-white" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-extrabold tracking-tight">
                                    Build Your Developer Brand
                                </h1>
                                <p className="mt-3 text-gray-500 dark:text-gray-400">
                                    The Portfolio Architect scans all your repositories,
                                    identifies your best work, and generates a professional
                                    GitHub Profile README.
                                </p>
                            </div>
                            <button
                                onClick={() => generate.mutate()}
                                disabled={generate.isPending}
                                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-8 py-3 text-base font-semibold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110 disabled:opacity-50"
                            >
                                <Sparkles className="h-5 w-5" />
                                Generate Professional Profile
                            </button>
                            {generate.isError && (
                                <p className="mt-2 text-sm text-red-500">
                                    Failed to start workflow. Is the backend running?
                                </p>
                            )}
                        </div>
                    )}

                    {/* Working state */}
                    {isWorking && (
                        <div className="space-y-8">
                            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg">
                                <Loader2 className="h-10 w-10 animate-spin text-white" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">
                                    Crafting Your Profile
                                </h2>
                                <p className="mt-2 text-sm text-gray-500">
                                    {status?.total_repos
                                        ? `${status.analyzed}/${status.total_repos} repos analyzed`
                                        : "Initializing..."}
                                </p>
                            </div>

                            {/* Stage progress */}
                            <div className="mx-auto max-w-xs space-y-3 text-left">
                                {Object.entries(STAGES)
                                    .filter(([key]) => key !== "complete" && key !== "failed")
                                    .map(([key, stage]) => {
                                        const StageIcon = stage.icon;
                                        const isCurrent = status?.stage === key;
                                        const isDone =
                                            currentStage && stage.index < currentStage.index;

                                        return (
                                            <div
                                                key={key}
                                                className={cn(
                                                    "flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm transition-all",
                                                    isCurrent &&
                                                    "bg-violet-50 font-semibold text-violet-700 dark:bg-violet-900/20 dark:text-violet-300",
                                                    isDone &&
                                                    "text-green-600 dark:text-green-400",
                                                    !isCurrent &&
                                                    !isDone &&
                                                    "text-gray-400 dark:text-gray-600",
                                                )}
                                            >
                                                {isDone ? (
                                                    <CheckCircle className="h-4 w-4 shrink-0" />
                                                ) : isCurrent ? (
                                                    <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                                                ) : (
                                                    <StageIcon className="h-4 w-4 shrink-0" />
                                                )}
                                                {stage.label}
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>
                    )}

                    {/* Success state */}
                    {isComplete && status && (
                        <div className="space-y-6">
                            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 shadow-lg">
                                <CheckCircle className="h-10 w-10 text-white" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">Profile Ready!</h2>
                                <p className="mt-2 text-gray-500 dark:text-gray-400">
                                    Your professional GitHub Profile has been generated
                                    with your top projects.
                                </p>
                            </div>
                            <div className="flex flex-col items-center gap-3">
                                {status.pr_url && (
                                    <a
                                        href={status.pr_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3 text-base font-semibold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110"
                                    >
                                        <ExternalLink className="h-4 w-4" />
                                        View Pull Request
                                    </a>
                                )}
                                {status.profile_url && (
                                    <a
                                        href={status.profile_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 text-sm font-medium text-violet-600 hover:text-violet-700 dark:text-violet-400 dark:hover:text-violet-300"
                                    >
                                        <ExternalLink className="h-3.5 w-3.5" />
                                        View Profile Repository
                                    </a>
                                )}
                            </div>
                            {status.errors.length > 0 && (
                                <div className="rounded-lg bg-yellow-50 p-3 text-left text-sm text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                                    <p className="font-medium">Warnings:</p>
                                    <ul className="mt-1 list-inside list-disc">
                                        {status.errors.map((err, i) => (
                                            <li key={i}>{err}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            <button
                                onClick={() => router.push("/dashboard")}
                                className="text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                            >
                                Back to Dashboard
                            </button>
                        </div>
                    )}

                    {/* Failed state */}
                    {isFailed && status && (
                        <div className="space-y-6">
                            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500 to-rose-600 shadow-lg">
                                <AlertCircle className="h-10 w-10 text-white" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">Generation Failed</h2>
                                <p className="mt-2 text-gray-500 dark:text-gray-400">
                                    Something went wrong while building your profile.
                                </p>
                            </div>
                            {status.errors.length > 0 && (
                                <div className="rounded-lg bg-red-50 p-3 text-left text-sm text-red-800 dark:bg-red-900/20 dark:text-red-300">
                                    <ul className="list-inside list-disc">
                                        {status.errors.map((err, i) => (
                                            <li key={i}>{err}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            <button
                                onClick={() => generate.mutate()}
                                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110"
                            >
                                Try Again
                            </button>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
