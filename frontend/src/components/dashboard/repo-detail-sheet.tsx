"use client";

import { useCallback } from "react";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Repo } from "@/types/api";
import { useGardener } from "@/hooks/use-gardener";
import { DraftProposalEditor } from "@/components/dashboard/draft-proposal-editor";
import {
    CheckCircle2,
    AlertTriangle,
    Zap,
    Wrench,
    Loader2,
    ExternalLink,
    GitPullRequest,
    AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface RepoDetailSheetProps {
    repo: Repo | null;
    open: boolean;
    onClose: () => void;
}

export function RepoDetailSheet({ repo, open, onClose }: RepoDetailSheetProps) {
    const { triggerFix, triggerSingleAnalysis, commitDocs, getFixStatus } = useGardener();

    if (!repo) return null;

    const repoId = repo.id;
    const localFixStatus = getFixStatus(repoId);
    const health = repo.health;
    const score = health?.health_score ?? null;
    const hasPendingFix = !!health?.pending_fix_url;
    const hasDraft = !!(repo.draft_proposal && Object.keys(repo.draft_proposal).length > 0);
    const issues = health?.issues ?? [];
    const dbStatus = health?.status ?? "idle";
    // Trust DB status: if drafting_docs, show progress even after refresh
    const isDrafting = localFixStatus === "pending" || dbStatus === "drafting_docs";

    const handleFix = useCallback(() => {
        triggerFix.mutate(repoId);
    }, [triggerFix, repoId]);

    const handleAnalyze = useCallback(() => {
        triggerSingleAnalysis.mutate(repoId);
    }, [triggerSingleAnalysis, repoId]);

    return (
        <Sheet open={open} onOpenChange={onClose}>
            <SheetContent className="w-full border-white/10 bg-card/95 backdrop-blur-xl sm:max-w-lg">
                <SheetHeader>
                    <SheetTitle className="text-foreground">
                        <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">{repo.name}</span>
                    </SheetTitle>
                    <p className="text-sm text-muted-foreground">{repo.full_name}</p>
                </SheetHeader>

                <div className="mt-6 flex flex-col gap-6">
                    {/* Health Score */}
                    <div>
                        <h4 className="mb-3 text-sm font-medium text-muted-foreground">
                            Health Score
                        </h4>
                        <div className="rounded-xl border border-white/10 bg-secondary/50 p-4">
                            {score !== null ? (
                                <div className="flex items-center gap-4">
                                    <div className={cn(
                                        "text-3xl font-bold",
                                        score >= 80 ? "text-green-400" : score >= 50 ? "text-amber-400" : "text-red-400"
                                    )}>
                                        {score}%
                                    </div>
                                    <div>
                                        <p className={cn(
                                            "font-medium",
                                            score >= 80 ? "text-green-400" : score >= 50 ? "text-amber-400" : "text-red-400"
                                        )}>
                                            {score >= 80 ? "Healthy" : score >= 50 ? "Needs Attention" : "Critical"}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {issues.length} issue{issues.length !== 1 ? "s" : ""} detected
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-center gap-3 text-muted-foreground">
                                    <AlertCircle className="h-5 w-5" />
                                    <span className="text-sm">Not yet analyzed</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Issues List */}
                    {issues.length > 0 && (
                        <div>
                            <h4 className="mb-3 text-sm font-medium text-muted-foreground">
                                Issues Found
                            </h4>
                            <div className="rounded-xl border border-white/10 bg-secondary/50 p-3">
                                <ScrollArea className="max-h-32">
                                    <div className="flex flex-col gap-2">
                                        {issues.map((issue, i) => (
                                            <div key={i} className="flex items-start gap-2 text-sm">
                                                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                                                <span className="text-muted-foreground">{issue}</span>
                                            </div>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </div>
                        </div>
                    )}

                    {/* Draft Proposal Review */}
                    {hasDraft && repo.draft_proposal && (
                        <DraftProposalEditor
                            repoId={repoId}
                            draft={repo.draft_proposal}
                            commitDocs={commitDocs}
                            onClose={onClose}
                        />
                    )}

                    {/* Action Buttons */}
                    {!hasDraft && (
                        <div className="flex flex-col gap-3">
                            {/* Fix in progress (persisted — survives refresh) */}
                            {isDrafting && (
                                <div className="flex items-center gap-3 rounded-xl border border-green-500/20 bg-green-500/10 p-4">
                                    <Loader2 className="h-5 w-5 animate-spin text-green-400" />
                                    <div>
                                        <p className="font-medium text-green-400">Gardener Working...</p>
                                        <p className="text-xs text-green-400/70">Generating documentation for review.</p>
                                    </div>
                                </div>
                            )}

                            {/* Fix done - draft ready */}
                            {localFixStatus === "done" && (
                                <div className="flex items-center gap-3 rounded-xl border border-blue-500/20 bg-blue-500/10 p-4">
                                    <CheckCircle2 className="h-5 w-5 text-blue-400" />
                                    <div>
                                        <p className="font-medium text-blue-400">Draft Ready</p>
                                        <p className="text-xs text-blue-400/70">Refresh to review the generated docs.</p>
                                    </div>
                                </div>
                            )}

                            {/* Pending PR on GitHub */}
                            {hasPendingFix && health?.pending_fix_url && !isDrafting && (
                                <>
                                    <div className="flex items-center gap-3 rounded-xl border border-purple-500/20 bg-purple-500/10 p-4">
                                        <GitPullRequest className="h-5 w-5 text-purple-400" />
                                        <div>
                                            <p className="font-medium text-purple-400">PR Already Open</p>
                                            <p className="text-xs text-purple-400/70">A Gardener fix is waiting for review.</p>
                                        </div>
                                    </div>
                                    <Button
                                        asChild
                                        className="w-full bg-purple-600 hover:bg-purple-700"
                                    >
                                        <a href={health.pending_fix_url} target="_blank" rel="noopener noreferrer">
                                            <GitPullRequest className="mr-2 h-4 w-4" />
                                            View Pull Request
                                        </a>
                                    </Button>
                                </>
                            )}

                            {/* Auto-fix button — always visible when not mid-fix */}
                            {score !== null && !isDrafting && (
                                <Button
                                    onClick={handleFix}
                                    disabled={triggerFix.isPending}
                                    className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-background font-medium hover:from-green-400 hover:to-emerald-400 shadow-[0_0_20px_rgba(34,197,94,0.3)]"
                                >
                                    {triggerFix.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Starting Fix...
                                        </>
                                    ) : (
                                        <>
                                            <Wrench className="mr-2 h-4 w-4" />
                                            {hasPendingFix ? "Re-Fix Repository" : "Auto-Fix Repository"}
                                        </>
                                    )}
                                </Button>
                            )}

                            {/* Analyze button — always visible */}
                            {!isDrafting && (
                                <Button
                                    onClick={handleAnalyze}
                                    disabled={triggerSingleAnalysis.isPending}
                                    variant="outline"
                                    className="w-full border-white/10 hover:bg-white/5"
                                >
                                    {triggerSingleAnalysis.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <Zap className="mr-2 h-4 w-4" />
                                            {score !== null ? "Re-Analyze" : "Analyze Repository"}
                                        </>
                                    )}
                                </Button>
                            )}

                            {/* View on GitHub */}
                            <Button
                                asChild
                                variant="outline"
                                className="w-full border-white/10 hover:bg-white/5"
                            >
                                <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="mr-2 h-4 w-4" />
                                    View on GitHub
                                </a>
                            </Button>
                        </div>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}
