/**
 * E2 — useDraftProposal hook tests. (Renamed from the brief's
 * use-gardener.test.tsx — useDraftProposal is the smaller, more
 * self-contained hook so it's where mock-Axios coverage adds value;
 * the larger useGardener hook is integration-heavy and would need a
 * full React Query Provider + Axios mock-server.)
 */
import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useDraftProposal } from "@/hooks/use-draft-proposal";

function makeCommitMock(overrides: Partial<{ isPending: boolean; isError: boolean }> = {}) {
    return {
        mutate: vi.fn(),
        isPending: overrides.isPending ?? false,
        isError: overrides.isError ?? false,
        // Other UseMutationResult fields the consumer doesn't actually read
    } as unknown as Parameters<typeof useDraftProposal>[0]["commitDocs"];
}

describe("useDraftProposal", () => {
    it("initializes with first filename selected and edit mode", () => {
        const draft = { "README.md": "# hi", "CONTRIBUTING.md": "# c" };
        const commitDocs = makeCommitMock();
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        expect(result.current.filenames).toEqual(["README.md", "CONTRIBUTING.md"]);
        expect(result.current.activeTab).toBe("README.md");
        expect(result.current.editorMode).toBe("edit");
        expect(result.current.selected).toEqual({
            "README.md": true,
            "CONTRIBUTING.md": true,
        });
        expect(result.current.selectedFiles).toEqual(["README.md", "CONTRIBUTING.md"]);
    });

    it("toggleFile flips a file's selection", () => {
        const draft = { "a.md": "a" };
        const commitDocs = makeCommitMock();
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        expect(result.current.selected["a.md"]).toBe(true);
        act(() => result.current.toggleFile("a.md"));
        expect(result.current.selected["a.md"]).toBe(false);
        expect(result.current.selectedFiles).toEqual([]);
    });

    it("handleContentChange updates editedContents", () => {
        const draft = { "a.md": "original" };
        const commitDocs = makeCommitMock();
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        act(() => result.current.handleContentChange("a.md", "edited"));
        expect(result.current.editedContents["a.md"]).toBe("edited");
    });

    it("setEditorMode toggles edit/preview", () => {
        const draft = { "a.md": "a" };
        const commitDocs = makeCommitMock();
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        act(() => result.current.setEditorMode("preview"));
        expect(result.current.editorMode).toBe("preview");
    });

    it("handleCommit calls commitDocs.mutate with selected files", () => {
        const draft = { "a.md": "a", "b.md": "b" };
        const mutate = vi.fn();
        const commitDocs = { ...makeCommitMock(), mutate } as Parameters<typeof useDraftProposal>[0]["commitDocs"];
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 42, draft, commitDocs }),
        );
        act(() => result.current.toggleFile("b.md")); // deselect b.md
        act(() => result.current.handleCommit());
        expect(mutate).toHaveBeenCalledTimes(1);
        const firstCall = mutate.mock.calls[0];
        if (!firstCall) throw new Error("mutate not called");
        const [args] = firstCall;
        expect(args.repoId).toBe(42);
        expect(args.selectedFiles).toEqual(["a.md"]);
        expect(args.editedContents).toEqual({ "a.md": "a", "b.md": "b" });
    });

    it("handleCommit no-ops when no files selected", () => {
        const draft = { "a.md": "a" };
        const mutate = vi.fn();
        const commitDocs = { ...makeCommitMock(), mutate } as Parameters<typeof useDraftProposal>[0]["commitDocs"];
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        act(() => result.current.toggleFile("a.md")); // deselect
        act(() => result.current.handleCommit());
        expect(mutate).not.toHaveBeenCalled();
    });

    it("isCommitting + isError reflect commitDocs flags", () => {
        const draft = { "a.md": "a" };
        const commitDocs = makeCommitMock({ isPending: true, isError: false });
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        expect(result.current.isCommitting).toBe(true);
        expect(result.current.isError).toBe(false);
    });

    it("handles empty draft (no filenames)", () => {
        const draft = {};
        const commitDocs = makeCommitMock();
        const { result } = renderHook(() =>
            useDraftProposal({ repoId: 1, draft, commitDocs }),
        );
        expect(result.current.filenames).toEqual([]);
        expect(result.current.activeTab).toBe("");
        expect(result.current.selectedFiles).toEqual([]);
    });
});
