import { useState } from "react";
import type { UseMutationResult } from "@tanstack/react-query";

interface CommitArgs {
    repoId: number;
    selectedFiles: string[];
    editedContents?: Record<string, string>;
}

interface CommitResult {
    repoId: number;
    prUrl: string;
}

type CommitMutation = UseMutationResult<CommitResult, Error, CommitArgs>;

interface UseDraftProposalArgs {
    repoId: number;
    draft: Record<string, string>;
    commitDocs: CommitMutation;
}

export function useDraftProposal({ repoId, draft, commitDocs }: UseDraftProposalArgs) {
    const filenames = Object.keys(draft);
    const [activeTab, setActiveTab] = useState(filenames[0] ?? "");
    const [selected, setSelected] = useState<Record<string, boolean>>(() =>
        Object.fromEntries(filenames.map((f) => [f, true]))
    );
    const [editedContents, setEditedContents] = useState<Record<string, string>>(
        () => ({ ...draft })
    );
    const [editorMode, setEditorMode] = useState<"edit" | "preview">("edit");
    const [committed, setCommitted] = useState(false);
    const [prUrl, setPrUrl] = useState<string | null>(null);

    const toggleFile = (filename: string) => {
        setSelected((prev) => ({ ...prev, [filename]: !prev[filename] }));
    };

    const handleContentChange = (filename: string, content: string) => {
        setEditedContents((prev) => ({ ...prev, [filename]: content }));
    };

    const selectedFiles = filenames.filter((f) => selected[f]);

    const handleCommit = () => {
        if (selectedFiles.length === 0) return;
        commitDocs.mutate(
            { repoId, selectedFiles, editedContents },
            {
                onSuccess: ({ prUrl: url }) => {
                    setCommitted(true);
                    setPrUrl(url);
                },
            }
        );
    };

    return {
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
        isCommitting: commitDocs.isPending,
        isError: commitDocs.isError,
    };
}
