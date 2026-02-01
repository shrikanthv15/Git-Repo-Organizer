import asyncio
import json
import os
import subprocess
import tempfile
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from temporalio import activity

from github import Auth, Github, GithubException

from app.db.crud import (
    upsert_analysis_result,
    upsert_repository,
    upsert_user,
    update_structure_map,
)
from app.db.session import get_session
from app.services import github_service
from app.services import llm_service


# ---------------------------------------------------------------------------
# Phase 2: Greeting
# ---------------------------------------------------------------------------

@activity.defn
async def say_hello(name: str) -> str:
    return f"Hello {name}, the Gardener is ready!"


# ---------------------------------------------------------------------------
# Phase 4: Repo Health Analysis
# ---------------------------------------------------------------------------

def _analyze_repo(repo_full_name: str, access_token: str) -> dict:
    """Synchronous PyGithub analysis — run via asyncio.to_thread."""
    g = Github(auth=Auth.Token(access_token))
    try:
        repo = g.get_repo(repo_full_name)
    except GithubException as exc:
        raise ValueError(f"Could not fetch repo '{repo_full_name}': {exc.data}")

    score = 100
    issues: list[str] = []

    # Check 1: README
    try:
        repo.get_readme()
    except GithubException:
        score -= 20
        issues.append("No README")

    # Check 2: Staleness (> 6 months since last push)
    pushed_at = repo.pushed_at
    if pushed_at is not None:
        months_since_push = (datetime.now(timezone.utc) - pushed_at).days / 30
        if months_since_push > 6:
            score -= 30
            issues.append(f"Stale — last push {months_since_push:.0f} months ago")
    else:
        score -= 30
        issues.append("No push date available")

    # Check 3: Description
    if not repo.description:
        score -= 10
        issues.append("No description")

    last_commit_date = pushed_at or datetime.now(timezone.utc)

    # Check for an existing Gardener PR (pending fix detection)
    pending_fix_url: str | None = None
    try:
        open_prs = repo.get_pulls(
            state="open",
            head=f"{repo.owner.login}:gardener/readme-fix",
            sort="updated",
        )
        if open_prs.totalCount > 0:
            pending_fix_url = open_prs[0].html_url
    except GithubException:
        pass  # Non-critical — skip if PR lookup fails

    # Persist results to database
    try:
        with get_session() as session:
            db_user = upsert_user(
                session,
                github_id=repo.owner.id,
                username=repo.owner.login,
            )
            db_repo = upsert_repository(
                session,
                github_repo_id=repo.id,
                owner_id=db_user.id,
                name=repo.name,
                full_name=repo.full_name,
                html_url=repo.html_url,
            )
            upsert_analysis_result(
                session,
                repo_id=db_repo.id,
                health_score=max(score, 0),
                issues=issues,
                pending_fix_url=pending_fix_url,
            )
            session.commit()
    except Exception as exc:
        activity.logger.warning("DB persistence failed (non-fatal): %s", exc)

    g.close()

    return {
        "repo_name": repo.full_name,
        "health_score": max(score, 0),
        "issues": issues,
        "last_commit_date": last_commit_date.isoformat(),
        "pending_fix_url": pending_fix_url,
    }


@activity.defn
async def analyze_repo_health(repo_full_name: str, access_token: str) -> dict:
    """Analyze a GitHub repo and return a health report."""
    return await asyncio.to_thread(_analyze_repo, repo_full_name, access_token)


# ---------------------------------------------------------------------------
# Phase 5: Batch Repo Fetching
# ---------------------------------------------------------------------------

@activity.defn
async def fetch_repo_list_activity(access_token: str, limit: int) -> list[dict]:
    """Fetch the user's repos and return the top N as dicts."""
    repos = await github_service.list_user_repos(access_token)
    return [r.model_dump() for r in repos[:limit]]


# ---------------------------------------------------------------------------
# Phase 9: Deep Repo Scanner
# ---------------------------------------------------------------------------

HIGH_VALUE_FILES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "Cargo.toml",
    "go.mod",
}

HIGH_VALUE_ENTRY_POINTS = {
    "main.py",
    "app.py",
    "index.js",
    "index.ts",
    "src/index.js",
    "src/index.ts",
    "src/main.py",
    "src/app.py",
}

MAX_FILE_LINES = 200


def _build_file_tree(root: Path, prefix: str = "") -> list[dict]:
    """Walk a directory and return a JSON-serialisable tree structure."""
    tree: list[dict] = []
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return tree

    for entry in entries:
        if entry.name.startswith("."):
            continue
        rel = f"{prefix}{entry.name}" if not prefix else f"{prefix}/{entry.name}"
        if entry.is_dir():
            children = _build_file_tree(entry, rel)
            tree.append({"name": entry.name, "type": "dir", "path": rel, "children": children})
        else:
            tree.append({"name": entry.name, "type": "file", "path": rel})
    return tree


def _read_high_value_files(root: Path) -> dict[str, str]:
    """Read contents of known high-value files (capped at MAX_FILE_LINES)."""
    contents: dict[str, str] = {}
    all_targets = HIGH_VALUE_FILES | HIGH_VALUE_ENTRY_POINTS

    for target in all_targets:
        fpath = root / target
        if fpath.is_file():
            try:
                lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
                contents[target] = "\n".join(lines[:MAX_FILE_LINES])
            except Exception:
                pass
    return contents


def _deep_scan(repo_url: str, access_token: str, github_repo_id: int) -> dict:
    """Clone repo shallow, map files, read key files, persist structure_map."""
    parsed = urlparse(repo_url)
    # Insert token into URL for auth — masked in any log output
    auth_url = f"https://oauth2:{access_token}@{parsed.hostname}{parsed.path}.git"
    masked_url = f"https://oauth2:****@{parsed.hostname}{parsed.path}.git"

    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dir = Path(tmpdir) / "repo"
        activity.logger.info("Cloning %s into temp directory", masked_url)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", auth_url, str(clone_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            # Mask token in error output before raising
            stderr = result.stderr.replace(access_token, "****")
            raise RuntimeError(f"git clone failed: {stderr}")

        file_tree = _build_file_tree(clone_dir)
        tech_stack_files = _read_high_value_files(clone_dir)

    # Persist structure_map to DB
    try:
        with get_session() as session:
            update_structure_map(
                session,
                github_repo_id=github_repo_id,
                structure_map={"file_tree": file_tree, "tech_stack_files": list(tech_stack_files.keys())},
            )
            session.commit()
    except Exception as exc:
        activity.logger.warning("DB structure_map update failed (non-fatal): %s", exc)

    return {
        "file_tree": file_tree,
        "tech_stack_files": tech_stack_files,
    }


@activity.defn
async def deep_scan_repo(repo_url: str, access_token: str, github_repo_id: int) -> dict:
    """Ephemeral clone + deep file analysis of a repository."""
    return await asyncio.to_thread(_deep_scan, repo_url, access_token, github_repo_id)


# ---------------------------------------------------------------------------
# Phase 6: Janitor Activities (legacy — kept for backward compat)
# ---------------------------------------------------------------------------

def _get_repo_context(repo_full_name: str, access_token: str) -> list[str]:
    """Fetch file tree (depth 2) — synchronous PyGithub call."""
    g = Github(auth=Auth.Token(access_token))
    repo = g.get_repo(repo_full_name)

    file_paths: list[str] = []
    top_level = repo.get_contents("")
    for item in top_level:
        file_paths.append(item.path)
        if item.type == "dir":
            try:
                sub_items = repo.get_contents(item.path)
                for sub in sub_items:
                    file_paths.append(sub.path)
            except GithubException:
                pass

    g.close()
    return file_paths


@activity.defn
async def get_repo_context_activity(repo_full_name: str, access_token: str) -> list[str]:
    """Fetch the file tree (depth 2) for a repository."""
    return await asyncio.to_thread(_get_repo_context, repo_full_name, access_token)


@activity.defn
async def generate_readme_activity(repo_name: str, file_structure: list[str], description: str) -> str:
    """Generate a README.md using LiteLLM (legacy shallow mode)."""
    return await llm_service.generate_readme(repo_name, file_structure, description)


@activity.defn
async def generate_deep_readme_activity(
    repo_name: str,
    description: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Generate a README.md using deep code context."""
    return await llm_service.generate_deep_readme(
        repo_name, description, file_tree, tech_stack_files
    )


def _create_pull_request(repo_full_name: str, content: str, access_token: str) -> str:
    """Create a branch, commit README.md, and open a PR — synchronous PyGithub."""
    g = Github(access_token)
    repo = g.get_repo(repo_full_name)

    # 1. Define a consistent branch name (Idempotent)
    target_branch = "gardener/readme-fix"
    default_branch_name = repo.default_branch
    default_branch = repo.get_branch(default_branch_name)

    # 2. Get or Create the Branch — force-push (reset) if it already exists
    try:
        ref = repo.get_git_ref(f"heads/{target_branch}")
        # Force-update the branch to latest default HEAD so our commit is clean
        ref.edit(sha=default_branch.commit.sha, force=True)
        print(f"Branch {target_branch} reset to {default_branch_name} HEAD (force-push).")
    except GithubException:
        repo.create_git_ref(ref=f"refs/heads/{target_branch}", sha=default_branch.commit.sha)
        print(f"Created new branch {target_branch}")

    # 3. Create or Update the README file on that branch
    file_path = "README.md"
    message = "🌿 Gardener: Enhanced Documentation"
    try:
        # Check if file exists ON THE TARGET BRANCH
        contents = repo.get_contents(file_path, ref=target_branch)
        repo.update_file(
            path=file_path,
            message=message,
            content=content,
            sha=contents.sha,
            branch=target_branch,
        )
    except GithubException:
        repo.create_file(
            path=file_path,
            message=message,
            content=content,
            branch=target_branch,
        )

    # 4. Check for an existing Pull Request to avoid duplicates
    existing_prs = repo.get_pulls(
        state="open",
        head=f"{repo.owner.login}:{target_branch}",
        base=default_branch_name,
    )
    if existing_prs.totalCount > 0:
        pr = existing_prs[0]
        print(f"PR already exists: {pr.html_url}")
        g.close()
        return pr.html_url

    # 5. Create new PR if none exists
    try:
        pr = repo.create_pull(
            title="🌿 Gardener: Enhanced Documentation",
            body=(
                "This documentation was auto-generated by the GitHub Gardener AI "
                "using deep code analysis with architecture diagrams."
            ),
            head=target_branch,
            base=default_branch_name,
        )
        pr_url = pr.html_url
        g.close()
        return pr_url
    except GithubException as e:
        if e.status == 422 and "No commits between" in str(e.data):
            print(f"No changes detected between {target_branch} and {default_branch_name}. Skipping PR.")
            g.close()
            # Return the branch URL or repo URL so the frontend has something to link to
            return f"{repo.html_url}/tree/{target_branch}"
        raise e


@activity.defn
async def create_pull_request_activity(repo_full_name: str, content: str, access_token: str) -> str:
    """Create a branch with README.md and open a Pull Request."""
    return await asyncio.to_thread(_create_pull_request, repo_full_name, content, access_token)
