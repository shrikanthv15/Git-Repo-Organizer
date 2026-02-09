"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
    ArrowLeft,
    Sparkles,
    Loader2,
    ExternalLink,
    Search,
    Cpu,
    Upload,
    CheckCircle,
    AlertCircle,
    Eye,
    Pencil,
    RotateCcw,
    Check,
} from "lucide-react";
import { usePortfolio, useRepos } from "@/hooks/use-gardener";
import { cn } from "@/lib/utils";
import type { Repo } from "@/types/api";

// ---------------------------------------------------------------------------
// Stage progress map for Step 2 (generating)
// ---------------------------------------------------------------------------
const STAGES: Record<string, { label: string; icon: typeof Search; index: number }> = {
    resolving: { label: "Resolving selected repos...", icon: Search, index: 0 },
    scanning: { label: "Deep scanning repos...", icon: Search, index: 1 },
    generating: { label: "Designing your profile...", icon: Cpu, index: 2 },
    draft_ready: { label: "Draft ready!", icon: CheckCircle, index: 3 },
    failed: { label: "Something went wrong", icon: AlertCircle, index: 3 },
};

const MAX_REPOS = 6;

export default function PortfolioPage() {
    const router = useRouter();
    const { generate, status, publish, publishResult, isPolling, reset } = usePortfolio();
    const { data: repos } = useRepos();

    // Step tracking: "select" | "generating" | "editor" | "published"
    const [step, setStep] = useState<"select" | "generating" | "editor" | "published">("select");

    // Step 1 state
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
    const [bio, setBio] = useState("");
    const [linkedin, setLinkedin] = useState("");
    const [email, setEmail] = useState("");
    const [website, setWebsite] = useState("");

    // Step 3 state
    const [editorContent, setEditorContent] = useState("");
    const [previewMode, setPreviewMode] = useState(false);

    // Auth guard
    useEffect(() => {
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (!token) router.push("/");
        }
    }, [router]);

    // Transition to editor when draft is ready
    useEffect(() => {
        if (status?.stage === "draft_ready" && status.draft_readme) {
            setEditorContent(status.draft_readme);
            setStep("editor");
        }
        if (status?.stage === "failed") {
            setStep("select");
        }
    }, [status]);

    // Transition to published state
    useEffect(() => {
        if (publishResult) {
            setStep("published");
        }
    }, [publishResult]);

    // Filter repos: only non-fork, public
    const eligibleRepos = useMemo(() => {
        if (!repos) return [];
        return repos.filter((r) => !r.private);
    }, [repos]);

    const toggleRepo = (id: number) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else if (next.size < MAX_REPOS) {
                next.add(id);
            }
            return next;
        });
    };

    const handleGenerate = () => {
        const links: Record<string, string> = {};
        if (linkedin.trim()) links.linkedin = linkedin.trim();
        if (email.trim()) links.email = email.trim();
        if (website.trim()) links.website = website.trim();

        generate.mutate({
            repo_ids: Array.from(selectedIds),
            bio: bio.trim() || undefined,
            links: Object.keys(links).length > 0 ? links : undefined,
        });
        setStep("generating");
    };

    const handlePublish = () => {
        publish.mutate(editorContent);
    };

    const handleStartOver = () => {
        reset();
        setStep("select");
        setSelectedIds(new Set());
        setBio("");
        setLinkedin("");
        setEmail("");
        setWebsite("");
        setEditorContent("");
        setPreviewMode(false);
    };

    const currentStage = status?.stage ? STAGES[status.stage] : null;

    return (
        <div className="flex min-h-screen flex-col bg-gray-50 text-gray-900 dark:bg-black dark:text-gray-50">
            {/* Top bar */}
            <header className="border-b border-gray-200 px-6 py-4 dark:border-zinc-800">
                <div className="mx-auto flex max-w-5xl items-center justify-between">
                    <button
                        onClick={() => router.push("/dashboard")}
                        className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Dashboard
                    </button>
                    <div className="flex items-center gap-2">
                        {/* Step indicators */}
                        {["Select", "Generate", "Review"].map((label, i) => {
                            const stepIdx = i;
                            const currentIdx = step === "select" ? 0 : step === "generating" ? 1 : step === "editor" || step === "published" ? 2 : 0;
                            return (
                                <div key={label} className="flex items-center gap-1.5">
                                    {i > 0 && <div className="h-px w-6 bg-gray-300 dark:bg-zinc-700" />}
                                    <div className={cn(
                                        "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold",
                                        stepIdx < currentIdx && "bg-green-500 text-white",
                                        stepIdx === currentIdx && "bg-violet-600 text-white",
                                        stepIdx > currentIdx && "bg-gray-200 text-gray-500 dark:bg-zinc-800 dark:text-zinc-500",
                                    )}>
                                        {stepIdx < currentIdx ? <Check className="h-3 w-3" /> : i + 1}
                                    </div>
                                    <span className={cn(
                                        "text-xs font-medium",
                                        stepIdx === currentIdx ? "text-gray-900 dark:text-white" : "text-gray-400 dark:text-zinc-500",
                                    )}>
                                        {label}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </header>

            <main className="flex flex-1 flex-col p-6">
                {/* ============================================================ */}
                {/* STEP 1: Select Repos + Bio/Links                             */}
                {/* ============================================================ */}
                {step === "select" && (
                    <div className="mx-auto w-full max-w-5xl space-y-8">
                        {/* Hero */}
                        <div className="text-center">
                            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg">
                                <Sparkles className="h-8 w-8 text-white" />
                            </div>
                            <h1 className="text-3xl font-extrabold tracking-tight">
                                Portfolio Studio
                            </h1>
                            <p className="mt-2 text-gray-500 dark:text-gray-400">
                                Choose your best repos, add your bio, and generate a professional GitHub Profile README.
                            </p>
                        </div>

                        {/* Repo grid */}
                        <div>
                            <div className="mb-3 flex items-center justify-between">
                                <h2 className="text-lg font-semibold">
                                    Select Repositories
                                    <span className="ml-2 text-sm font-normal text-gray-500">
                                        ({selectedIds.size}/{MAX_REPOS} selected)
                                    </span>
                                </h2>
                            </div>

                            {!repos ? (
                                <div className="flex items-center justify-center py-12">
                                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                                </div>
                            ) : eligibleRepos.length === 0 ? (
                                <p className="py-8 text-center text-sm text-gray-500">No public repositories found.</p>
                            ) : (
                                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                    {eligibleRepos.map((repo) => (
                                        <RepoSelectCard
                                            key={repo.id}
                                            repo={repo}
                                            selected={selectedIds.has(repo.id)}
                                            disabled={!selectedIds.has(repo.id) && selectedIds.size >= MAX_REPOS}
                                            onToggle={() => toggleRepo(repo.id)}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Bio + Links */}
                        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                            <div>
                                <label className="mb-1.5 block text-sm font-medium">
                                    Bio <span className="text-gray-400">(optional)</span>
                                </label>
                                <textarea
                                    value={bio}
                                    onChange={(e) => setBio(e.target.value)}
                                    placeholder="Full-stack developer passionate about developer tools and AI..."
                                    rows={3}
                                    maxLength={500}
                                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-900"
                                />
                            </div>
                            <div className="space-y-3">
                                <label className="mb-1.5 block text-sm font-medium">
                                    Links <span className="text-gray-400">(optional)</span>
                                </label>
                                <input
                                    type="url"
                                    value={linkedin}
                                    onChange={(e) => setLinkedin(e.target.value)}
                                    placeholder="LinkedIn URL"
                                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-900"
                                />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Email address"
                                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-900"
                                />
                                <input
                                    type="url"
                                    value={website}
                                    onChange={(e) => setWebsite(e.target.value)}
                                    placeholder="Website URL"
                                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-900"
                                />
                            </div>
                        </div>

                        {/* Generate button */}
                        <div className="flex justify-center pt-2">
                            <button
                                onClick={handleGenerate}
                                disabled={selectedIds.size === 0 || generate.isPending}
                                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-8 py-3 text-base font-semibold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <Sparkles className="h-5 w-5" />
                                Generate Profile
                            </button>
                        </div>

                        {generate.isError && (
                            <p className="text-center text-sm text-red-500">
                                Failed to start workflow. Is the backend running?
                            </p>
                        )}

                        {status?.stage === "failed" && status.errors.length > 0 && (
                            <div className="mx-auto max-w-lg rounded-lg bg-red-50 p-3 text-left text-sm text-red-800 dark:bg-red-900/20 dark:text-red-300">
                                <ul className="list-inside list-disc">
                                    {status.errors.map((err, i) => (
                                        <li key={i}>{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {/* ============================================================ */}
                {/* STEP 2: Generating (Progress)                                */}
                {/* ============================================================ */}
                {step === "generating" && (
                    <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center text-center">
                        <div className="space-y-8">
                            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg">
                                <Loader2 className="h-10 w-10 animate-spin text-white" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">Crafting Your Profile</h2>
                                <p className="mt-2 text-sm text-gray-500">
                                    {status?.total_repos
                                        ? `${status.scanned}/${status.total_repos} repos scanned`
                                        : "Initializing..."}
                                </p>
                            </div>

                            {/* Stage progress */}
                            <div className="mx-auto max-w-xs space-y-3 text-left">
                                {Object.entries(STAGES)
                                    .filter(([key]) => key !== "draft_ready" && key !== "failed")
                                    .map(([key, stage]) => {
                                        const StageIcon = stage.icon;
                                        const isCurrent = status?.stage === key;
                                        const isDone = currentStage && stage.index < currentStage.index;

                                        return (
                                            <div
                                                key={key}
                                                className={cn(
                                                    "flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm transition-all",
                                                    isCurrent && "bg-violet-50 font-semibold text-violet-700 dark:bg-violet-900/20 dark:text-violet-300",
                                                    isDone && "text-green-600 dark:text-green-400",
                                                    !isCurrent && !isDone && "text-gray-400 dark:text-gray-600",
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
                    </div>
                )}

                {/* ============================================================ */}
                {/* STEP 3: Editor with Edit/Preview toggle                      */}
                {/* ============================================================ */}
                {step === "editor" && (
                    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col">
                        {/* Editor toolbar */}
                        <div className="mb-4 flex items-center justify-between">
                            <h2 className="text-lg font-semibold">Review Your Profile README</h2>
                            <div className="flex items-center gap-3">
                                {/* Edit/Preview toggle */}
                                <div className="flex rounded-lg border border-gray-300 dark:border-zinc-700">
                                    <button
                                        onClick={() => setPreviewMode(false)}
                                        className={cn(
                                            "flex items-center gap-1.5 rounded-l-lg px-3 py-1.5 text-sm font-medium transition-colors",
                                            !previewMode
                                                ? "bg-violet-600 text-white"
                                                : "text-gray-500 hover:text-gray-900 dark:hover:text-white",
                                        )}
                                    >
                                        <Pencil className="h-3.5 w-3.5" />
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => setPreviewMode(true)}
                                        className={cn(
                                            "flex items-center gap-1.5 rounded-r-lg px-3 py-1.5 text-sm font-medium transition-colors",
                                            previewMode
                                                ? "bg-violet-600 text-white"
                                                : "text-gray-500 hover:text-gray-900 dark:hover:text-white",
                                        )}
                                    >
                                        <Eye className="h-3.5 w-3.5" />
                                        Preview
                                    </button>
                                </div>

                                <button
                                    onClick={handleStartOver}
                                    className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-500 transition-colors hover:text-gray-900 dark:border-zinc-700 dark:hover:text-white"
                                >
                                    <RotateCcw className="h-3.5 w-3.5" />
                                    Start Over
                                </button>

                                <button
                                    onClick={handlePublish}
                                    disabled={publish.isPending || !editorContent.trim()}
                                    className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-all hover:shadow-md hover:brightness-110 disabled:opacity-50"
                                >
                                    {publish.isPending ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Upload className="h-4 w-4" />
                                    )}
                                    Publish to GitHub
                                </button>
                            </div>
                        </div>

                        {publish.isError && (
                            <p className="mb-3 text-sm text-red-500">
                                Failed to publish. Please try again.
                            </p>
                        )}

                        {/* Editor / Preview area */}
                        <div className="flex-1 overflow-hidden rounded-xl border border-gray-300 dark:border-zinc-700">
                            {previewMode ? (
                                <div className="h-full overflow-auto bg-white p-6 dark:bg-zinc-900">
                                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap break-words">
                                        {editorContent}
                                    </div>
                                </div>
                            ) : (
                                <textarea
                                    value={editorContent}
                                    onChange={(e) => setEditorContent(e.target.value)}
                                    className="h-full min-h-[500px] w-full resize-none bg-white p-4 font-mono text-sm leading-relaxed focus:outline-none dark:bg-zinc-900"
                                    spellCheck={false}
                                />
                            )}
                        </div>

                        {/* Warnings */}
                        {status?.errors && status.errors.length > 0 && (
                            <div className="mt-4 rounded-lg bg-yellow-50 p-3 text-left text-sm text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                                <p className="font-medium">Warnings:</p>
                                <ul className="mt-1 list-inside list-disc">
                                    {status.errors.map((err, i) => (
                                        <li key={i}>{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {/* ============================================================ */}
                {/* PUBLISHED: Success card                                      */}
                {/* ============================================================ */}
                {step === "published" && publishResult && (
                    <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center text-center">
                        <div className="space-y-6">
                            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 shadow-lg">
                                <CheckCircle className="h-10 w-10 text-white" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">Profile Published!</h2>
                                <p className="mt-2 text-gray-500 dark:text-gray-400">
                                    Your professional GitHub Profile README has been published.
                                </p>
                            </div>
                            <div className="flex flex-col items-center gap-3">
                                {publishResult.pr_url && (
                                    <a
                                        href={publishResult.pr_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3 text-base font-semibold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110"
                                    >
                                        <ExternalLink className="h-4 w-4" />
                                        View Pull Request
                                    </a>
                                )}
                                {publishResult.profile_url && (
                                    <a
                                        href={publishResult.profile_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 text-sm font-medium text-violet-600 hover:text-violet-700 dark:text-violet-400 dark:hover:text-violet-300"
                                    >
                                        <ExternalLink className="h-3.5 w-3.5" />
                                        View Profile Repository
                                    </a>
                                )}
                            </div>
                            <div className="flex items-center justify-center gap-4">
                                <button
                                    onClick={handleStartOver}
                                    className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                                >
                                    <RotateCcw className="h-3.5 w-3.5" />
                                    Generate Another
                                </button>
                                <button
                                    onClick={() => router.push("/dashboard")}
                                    className="text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white"
                                >
                                    Back to Dashboard
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Repo selection card component
// ---------------------------------------------------------------------------
function RepoSelectCard({
    repo,
    selected,
    disabled,
    onToggle,
}: {
    repo: Repo;
    selected: boolean;
    disabled: boolean;
    onToggle: () => void;
}) {
    return (
        <button
            onClick={onToggle}
            disabled={disabled}
            className={cn(
                "relative flex flex-col rounded-xl border p-4 text-left transition-all",
                selected
                    ? "border-green-500 bg-green-50 shadow-sm dark:border-green-600 dark:bg-green-900/10"
                    : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700",
                disabled && !selected && "cursor-not-allowed opacity-50",
            )}
        >
            {/* Selection indicator */}
            <div className={cn(
                "absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full border-2 transition-all",
                selected
                    ? "border-green-500 bg-green-500"
                    : "border-gray-300 dark:border-zinc-600",
            )}>
                {selected && <Check className="h-3 w-3 text-white" />}
            </div>

            <h3 className="pr-8 text-sm font-semibold truncate">{repo.name}</h3>
            {repo.description && (
                <p className="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
                    {repo.description}
                </p>
            )}
            <div className="mt-auto flex items-center gap-3 pt-2 text-xs text-gray-400">
                {repo.health && (
                    <span className={cn(
                        "font-medium",
                        repo.health.health_score >= 80 ? "text-green-600" :
                        repo.health.health_score >= 50 ? "text-yellow-600" :
                        "text-red-500",
                    )}>
                        {repo.health.health_score}%
                    </span>
                )}
            </div>
        </button>
    );
}
