import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RepoCard } from "@/components/dashboard/repo-card";
import type { Repo } from "@/types/api";

const baseRepo = (overrides: Partial<Repo> = {}): Repo =>
    ({
        id: 1,
        name: "my-repo",
        full_name: "alice/my-repo",
        private: false,
        html_url: "https://github.com/alice/my-repo",
        description: "A demo repo",
        ...overrides,
    }) as Repo;


describe("RepoCard", () => {
    it("renders repo name + full_name", () => {
        render(<RepoCard repo={baseRepo()} onClick={() => {}} />);
        expect(screen.getByText("my-repo")).toBeInTheDocument();
    });

    it("shows the Globe icon for public repos", () => {
        const { container } = render(<RepoCard repo={baseRepo({ private: false })} onClick={() => {}} />);
        // lucide-react renders an SVG with a class containing the icon name
        // (e.g. lucide-globe). Public repos → globe icon.
        const globeSvg = container.querySelector("svg.lucide-globe");
        const lockSvg = container.querySelector("svg.lucide-lock");
        expect(globeSvg).toBeInTheDocument();
        expect(lockSvg).not.toBeInTheDocument();
    });

    it("shows the Lock icon for private repos", () => {
        const { container } = render(<RepoCard repo={baseRepo({ private: true })} onClick={() => {}} />);
        const lockSvg = container.querySelector("svg.lucide-lock");
        const globeSvg = container.querySelector("svg.lucide-globe");
        expect(lockSvg).toBeInTheDocument();
        expect(globeSvg).not.toBeInTheDocument();
    });

    it("renders health-score percentage when score is present", () => {
        const repo = baseRepo({
            health: {
                repo_name: "alice/my-repo",
                health_score: 87,
                issues: [],
                last_commit_date: "2026-05-20T00:00:00Z",
                pending_fix_url: null,
                status: "idle",
                last_gardener_run_at: null,
            },
        } as unknown as Partial<Repo>);
        render(<RepoCard repo={repo} onClick={() => {}} />);
        expect(screen.getByText(/87/)).toBeInTheDocument();
    });

    it("fires onClick when the card is clicked", () => {
        const onClick = vi.fn();
        render(<RepoCard repo={baseRepo()} onClick={onClick} />);
        // Click the repo name (which is inside the clickable card region).
        const name = screen.getByText("my-repo");
        // Walk up to the clickable parent that has the handler.
        fireEvent.click(name);
        expect(onClick).toHaveBeenCalled();
    });
});
