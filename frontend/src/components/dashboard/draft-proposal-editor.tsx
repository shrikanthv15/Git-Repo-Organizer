"use client";

import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useGardener } from "@/hooks/use-gardener";
import { useDraftProposal } from "@/hooks/use-draft-proposal";
import {
    CheckCircle2,
    FileCode,
    Loader2,
    GitPullRequest,
    AlertCircle,
    Eye,
    Check,
    X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DraftProposalEditorProps {
    repoId: number;
    draft: Record<string, string>;
    commitDocs: ReturnType<typeof useGardener>["commitDocs"];
    onClose: () => void;
}

export function DraftProposalEditor({
    repoId,
    draft,
    commitDocs,
}: DraftProposalEditorProps) {
    const {
        filenames,
        activeTab,
        setActiveTab,
        selected,
        toggleFile,
        selectedFiles,
        editedContents,
        handleContentChange,
        editorMode,
        setEditorMode,
        committed,
        prUrl,
        handleCommit,
        isCommitting,
        isError,
    } = useDraftProposal({ repoId, draft, commitDocs });

    if (committed && prUrl) {
        return (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-green-500/20 bg-green-500/10 p-6 text-center">
                <CheckCircle2 className="h-10 w-10 text-green-400" />
                <div>
                    <h3 className="font-semibold text-green-400">Pull Request Created!</h3>
                    <p className="text-sm text-muted-foreground">Your documentation has been committed.</p>
                </div>
                <Button asChild className="bg-purple-600 hover:bg-purple-700">
                    <a href={prUrl} target="_blank" rel="noopener noreferrer">
                        <GitPullRequest className="mr-2 h-4 w-4" />
                        View Pull Request
                    </a>
                </Button>
            </div>
        );
    }

    return (
        <div>
            <div className="mb-3 flex items-center justify-between">
                <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    Review Proposal ({filenames.length} file{filenames.length !== 1 ? "s" : ""})
                </h4>
                <Button
                    size="sm"
                    onClick={handleCommit}
                    disabled={selectedFiles.length === 0 || isCommitting}
                    className="h-7 bg-gradient-to-r from-green-500 to-emerald-500 text-xs text-background font-medium"
                >
                    {isCommitting ? (
                        <>
                            <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                            Committing...
                        </>
                    ) : (
                        <>
                            <Check className="mr-1.5 h-3 w-3" />
                            Commit Changes ({selectedFiles.length})
                        </>
                    )}
                </Button>
            </div>

            {/* File tabs */}
            <div className="flex gap-1 mb-3 overflow-x-auto">
                {filenames.map((filename) => (
                    <button
                        key={filename}
                        onClick={() => setActiveTab(filename)}
                        className={cn(
                            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap",
                            activeTab === filename
                                ? "bg-white/10 text-foreground"
                                : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                        )}
                    >
                        <FileCode className="h-3 w-3" />
                        {filename}
                        {selected[filename] ? (
                            <Check className="h-3 w-3 text-green-400" />
                        ) : (
                            <X className="h-3 w-3 text-red-400" />
                        )}
                    </button>
                ))}
            </div>

            {/* Toggle + Editor/Preview */}
            <div className="rounded-xl border border-white/10 bg-secondary/50 p-3">
                <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Include</span>
                        <button
                            onClick={() => toggleFile(activeTab)}
                            className={cn(
                                "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors",
                                selected[activeTab] ? "bg-green-500" : "bg-white/20"
                            )}
                        >
                            <span
                                className={cn(
                                    "inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow transition-transform",
                                    selected[activeTab] ? "translate-x-4" : "translate-x-0.5"
                                )}
                            />
                        </button>
                    </div>
                    {/* Edit / Preview toggle */}
                    <div className="flex rounded-lg border border-white/10 overflow-hidden">
                        <button
                            onClick={() => setEditorMode("edit")}
                            className={cn(
                                "px-2.5 py-1 text-xs font-medium transition-colors",
                                editorMode === "edit"
                                    ? "bg-white/10 text-foreground"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            Edit
                        </button>
                        <button
                            onClick={() => setEditorMode("preview")}
                            className={cn(
                                "px-2.5 py-1 text-xs font-medium transition-colors",
                                editorMode === "preview"
                                    ? "bg-white/10 text-foreground"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            Preview
                        </button>
                    </div>
                </div>

                {editorMode === "edit" ? (
                    <textarea
                        value={editedContents[activeTab] ?? ""}
                        onChange={(e) => handleContentChange(activeTab, e.target.value)}
                        className={cn(
                            "h-56 w-full resize-none rounded-lg border border-white/10 bg-background/50 p-3 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-green-500/50 focus:outline-none focus:ring-1 focus:ring-green-500/30",
                            !selected[activeTab] && "opacity-50"
                        )}
                        spellCheck={false}
                    />
                ) : (
                    <ScrollArea className="h-56">
                        <div className={cn(
                            "prose prose-sm dark:prose-invert max-w-none text-xs",
                            !selected[activeTab] && "opacity-50"
                        )}>
                            <ReactMarkdown>{editedContents[activeTab] ?? ""}</ReactMarkdown>
                        </div>
                    </ScrollArea>
                )}
            </div>

            {isError && (
                <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-500/10 p-2 text-xs text-red-400">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    Failed to commit. Please try again.
                </div>
            )}
        </div>
    );
}
