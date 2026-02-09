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
    clear_pending_fix_for_repo,
    get_repos_with_pending_pr,
    save_draft_proposal,
    set_repo_status,
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

    # Check 4: Last Gardener run — scan recent commits for our signature
    last_gardener_run_at: datetime | None = None
    try:
        commits = repo.get_commits()
        for commit in commits[:20]:  # check last 20 commits
            msg = commit.commit.message or ""
            if "\U0001f33f Gardener:" in msg:
                last_gardener_run_at = commit.commit.author.date
                break
    except GithubException:
        pass  # Non-critical

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
                last_gardener_run_at=last_gardener_run_at,
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
        "last_gardener_run_at": last_gardener_run_at.isoformat() if last_gardener_run_at else None,
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
    """Fetch the user's repos and return the top N as dicts (0 = all)."""
    repos = await github_service.list_user_repos(access_token)
    if limit > 0:
        repos = repos[:limit]
    return [r.model_dump() for r in repos]


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
        activity.logger.info("Branch %s reset to %s HEAD (force-push).", target_branch, default_branch_name)
    except GithubException:
        repo.create_git_ref(ref=f"refs/heads/{target_branch}", sha=default_branch.commit.sha)
        activity.logger.info("Created new branch %s", target_branch)

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
        activity.logger.info("PR already exists: %s", pr.html_url)
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
            activity.logger.info("No changes detected between %s and %s. Skipping PR.", target_branch, default_branch_name)
            g.close()
            # Return the branch URL or repo URL so the frontend has something to link to
            return f"{repo.html_url}/tree/{target_branch}"
        raise e


@activity.defn
async def create_pull_request_activity(repo_full_name: str, content: str, access_token: str) -> str:
    """Create a branch with README.md and open a Pull Request."""
    return await asyncio.to_thread(_create_pull_request, repo_full_name, content, access_token)


# ---------------------------------------------------------------------------
# Phase 12: Multi-Agent Documentation Squad
# ---------------------------------------------------------------------------

@activity.defn
async def analyze_codebase_activity(
    repo_name: str,
    description: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Analyze codebase and return a JSON summary string."""
    return await llm_service.analyze_codebase(
        repo_name, description, file_tree, tech_stack_files
    )


@activity.defn
async def generate_doc_activity(
    summary_json: str,
    doc_type: str,
    repo_name: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> dict:
    """Generate a single doc file. Returns dict with filename, content, doc_type, error."""
    filename = llm_service.DOC_TYPE_FILENAMES[doc_type]
    try:
        content = await llm_service.generate_doc(
            summary_json, doc_type, repo_name, file_tree, tech_stack_files
        )
        return {
            "filename": filename,
            "content": content,
            "doc_type": doc_type,
            "error": None,
        }
    except Exception as exc:
        activity.logger.error("generate_doc_activity failed for %s: %s", doc_type, exc)
        return {
            "filename": filename,
            "content": "",
            "doc_type": doc_type,
            "error": str(exc),
        }


def _create_docs_pull_request(
    repo_full_name: str,
    files_json: str,
    access_token: str,
) -> str:
    """Create a branch, commit multiple doc files, and open a single PR."""
    files: dict[str, str] = json.loads(files_json)

    g = Github(access_token)
    repo = g.get_repo(repo_full_name)

    target_branch = "gardener/docs-suite"
    default_branch_name = repo.default_branch
    default_branch = repo.get_branch(default_branch_name)

    # Get or create the branch
    try:
        ref = repo.get_git_ref(f"heads/{target_branch}")
        ref.edit(sha=default_branch.commit.sha, force=True)
    except GithubException:
        repo.create_git_ref(
            ref=f"refs/heads/{target_branch}",
            sha=default_branch.commit.sha,
        )

    # Create or update each file on the branch
    for file_path, content in files.items():
        message = f"🌿 Gardener: Generate {file_path}"
        try:
            existing = repo.get_contents(file_path, ref=target_branch)
            repo.update_file(
                path=file_path,
                message=message,
                content=content,
                sha=existing.sha,
                branch=target_branch,
            )
        except GithubException:
            repo.create_file(
                path=file_path,
                message=message,
                content=content,
                branch=target_branch,
            )

    # Check for existing PR to avoid duplicates
    existing_prs = repo.get_pulls(
        state="open",
        head=f"{repo.owner.login}:{target_branch}",
        base=default_branch_name,
    )
    if existing_prs.totalCount > 0:
        pr = existing_prs[0]
        g.close()
        return pr.html_url

    # Create new PR
    file_list = ", ".join(files.keys())
    try:
        pr = repo.create_pull(
            title="🌿 Gardener: Documentation Suite",
            body=(
                "This PR contains auto-generated documentation by the GitHub Gardener AI "
                "using deep code analysis.\n\n"
                f"**Files generated:** {file_list}"
            ),
            head=target_branch,
            base=default_branch_name,
        )
        pr_url = pr.html_url
        g.close()
        return pr_url
    except GithubException as e:
        if e.status == 422 and "No commits between" in str(e.data):
            g.close()
            return f"{repo.html_url}/tree/{target_branch}"
        raise e


@activity.defn
async def create_docs_pull_request_activity(
    repo_full_name: str,
    files_json: str,
    access_token: str,
) -> str:
    """Create a branch with multiple doc files and open a single Pull Request."""
    return await asyncio.to_thread(
        _create_docs_pull_request, repo_full_name, files_json, access_token
    )


# ---------------------------------------------------------------------------
# Phase 13: Human-in-the-Loop — save drafts to DB
# ---------------------------------------------------------------------------

@activity.defn
async def save_draft_proposal_activity(
    github_repo_id: int,
    files_json: str,
) -> bool:
    """Persist generated doc files as a draft_proposal in the DB."""
    files: dict = json.loads(files_json)

    def _save() -> bool:
        with get_session() as session:
            ok = save_draft_proposal(
                session,
                github_repo_id=github_repo_id,
                draft_proposal=files,
            )
            session.commit()
            return ok

    return await asyncio.to_thread(_save)


# ---------------------------------------------------------------------------
# Phase 18: Persistent status updates
# ---------------------------------------------------------------------------

@activity.defn
async def set_repo_status_activity(github_repo_id: int, status: str) -> bool:
    """Set the status field on a repo's analysis result."""
    def _set() -> bool:
        with get_session() as session:
            ok = set_repo_status(session, github_repo_id=github_repo_id, status=status)
            session.commit()
            return ok
    return await asyncio.to_thread(_set)


# ---------------------------------------------------------------------------
# Phase 17: Smart Sync — check PR statuses on GitHub
# ---------------------------------------------------------------------------

def _sync_pr_status(access_token: str) -> int:
    """Check GitHub for merged/closed PRs and clear pending_fix_url. Returns count updated."""
    with get_session() as session:
        pending = get_repos_with_pending_pr(session)

    if not pending:
        return 0

    g = Github(auth=Auth.Token(access_token))
    updated_count = 0

    for repo_full_name, pr_url in pending:
        try:
            repo = g.get_repo(repo_full_name)
            # Extract PR number from URL (e.g. .../pull/42)
            pr_number = _extract_pr_number(pr_url)
            if pr_number is None:
                continue

            pr = repo.get_pull(pr_number)
            if pr.state != "open":
                # PR was merged or closed — clear the pending_fix_url
                with get_session() as session:
                    clear_pending_fix_for_repo(session, repo_full_name=repo_full_name)
                    session.commit()
                updated_count += 1
        except GithubException:
            continue  # skip repos we can't access

    g.close()
    return updated_count


def _extract_pr_number(pr_url: str) -> int | None:
    """Extract pull request number from a GitHub PR URL."""
    # Handles URLs like https://github.com/owner/repo/pull/42
    try:
        parts = pr_url.rstrip("/").split("/")
        if "pull" in parts:
            idx = parts.index("pull")
            return int(parts[idx + 1])
    except (ValueError, IndexError):
        pass
    return None


@activity.defn
async def sync_pr_status_activity(access_token: str) -> int:
    """Check all pending PRs on GitHub and clear those that are merged/closed."""
    return await asyncio.to_thread(_sync_pr_status, access_token)


# ---------------------------------------------------------------------------
# Phase 14: Portfolio Architect
# ---------------------------------------------------------------------------

# Dependency files to look for during portfolio deep scan
_PORTFOLIO_DEP_FILES = [
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "composer.json",
]

# Map of dependency names → display framework names
_FRAMEWORK_MAP: dict[str, str] = {
    # Python
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "temporalio": "Temporal",
    "sqlmodel": "SQLModel",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "scikit-learn",
    "langchain": "LangChain",
    "litellm": "LiteLLM",
    # JavaScript / TypeScript
    "next": "Next.js",
    "react": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "express": "Express",
    "tailwindcss": "Tailwind CSS",
    "@tailwindcss/postcss": "Tailwind CSS",
    "prisma": "Prisma",
    "drizzle-orm": "Drizzle",
    "trpc": "tRPC",
    "@trpc/server": "tRPC",
    "axios": "Axios",
    "@tanstack/react-query": "React Query",
    "socket.io": "Socket.IO",
    # Rust
    "actix-web": "Actix Web",
    "tokio": "Tokio",
    "serde": "Serde",
    # Go (module paths)
    "gin-gonic/gin": "Gin",
    "gorilla/mux": "Gorilla Mux",
}


def _extract_frameworks(dependencies: dict[str, str]) -> list[str]:
    """Parse dependency file contents and extract recognizable framework names."""
    frameworks: set[str] = set()
    for _filename, content in dependencies.items():
        content_lower = content.lower()
        for dep_key, framework_name in _FRAMEWORK_MAP.items():
            if dep_key.lower() in content_lower:
                frameworks.add(framework_name)
    return sorted(frameworks)


def _portfolio_deep_scan(repo_full_name: str, access_token: str) -> dict:
    """Lightweight deep scan using PyGithub API (no git clone)."""
    g = Github(auth=Auth.Token(access_token))
    try:
        repo = g.get_repo(repo_full_name)
    except GithubException as exc:
        raise ValueError(f"Could not fetch repo '{repo_full_name}': {exc.data}")

    # Read README (first 3000 chars)
    readme_content = ""
    try:
        readme = repo.get_readme()
        readme_content = readme.decoded_content.decode("utf-8", errors="replace")[:3000]
    except GithubException:
        pass

    # Read dependency files
    dep_files: dict[str, str] = {}
    for dep_file in _PORTFOLIO_DEP_FILES:
        try:
            content_file = repo.get_contents(dep_file)
            if not isinstance(content_file, list):
                dep_files[dep_file] = content_file.decoded_content.decode("utf-8", errors="replace")[:5000]
        except GithubException:
            pass

    # Extract topics
    topics: list[str] = []
    try:
        topics = repo.get_topics()
    except GithubException:
        pass

    # Extract frameworks from dependencies
    frameworks = _extract_frameworks(dep_files)

    g.close()

    return {
        "full_name": repo.full_name,
        "name": repo.name,
        "description": repo.description or "",
        "html_url": repo.html_url,
        "language": repo.language or "",
        "stargazers_count": repo.stargazers_count,
        "forks_count": repo.forks_count,
        "topics": topics,
        "readme_content": readme_content,
        "dependencies": dep_files,
        "frameworks": frameworks,
    }


@activity.defn
async def portfolio_deep_scan_activity(repo_full_name: str, access_token: str) -> dict:
    """Lightweight deep scan for portfolio — no git clone, uses GitHub API."""
    return await asyncio.to_thread(_portfolio_deep_scan, repo_full_name, access_token)


def _fetch_repos_extended(access_token: str) -> list[dict]:
    """Fetch all owner repos with extended metadata (stars, fork, language, pushed_at)."""
    g = Github(auth=Auth.Token(access_token))
    repos: list[dict] = []
    for r in g.get_user().get_repos(affiliation="owner"):
        repos.append({
            "id": r.id,
            "name": r.name,
            "full_name": r.full_name,
            "description": r.description or "",
            "html_url": r.html_url,
            "private": r.private,
            "fork": r.fork,
            "stargazers_count": r.stargazers_count,
            "language": r.language,
            "pushed_at": r.pushed_at.isoformat() if r.pushed_at else None,
        })
    g.close()
    return repos


@activity.defn
async def fetch_repos_extended_activity(access_token: str) -> list[dict]:
    """Fetch all repos with extended metadata for portfolio selection."""
    return await asyncio.to_thread(_fetch_repos_extended, access_token)


@activity.defn
async def generate_profile_readme_activity(
    top_repos_json: str,
    username: str,
    bio: str = "",
    links_json: str = "{}",
) -> str:
    """Generate a GitHub Profile README from the top repos."""
    top_repos: list[dict] = json.loads(top_repos_json)
    links: dict = json.loads(links_json) if links_json else {}
    return await llm_service.generate_profile_readme(top_repos, username, bio=bio, links=links)


def _create_or_update_profile_repo(
    username: str,
    readme_content: str,
    access_token: str,
) -> dict:
    """Create or update the username/username profile repo with a new README."""
    g = Github(access_token)
    user = g.get_user()
    profile_repo_name = username

    # Check if profile repo exists
    profile_repo = None
    try:
        profile_repo = g.get_repo(f"{username}/{profile_repo_name}")
    except GithubException as exc:
        if exc.status != 404:
            raise

    if profile_repo is None:
        # Create the special profile repo
        profile_repo = user.create_repo(
            name=profile_repo_name,
            description=f"{username}'s GitHub Profile",
            auto_init=True,
            private=False,
        )
        # Commit README directly to main since it's a new repo
        try:
            existing = profile_repo.get_contents("README.md", ref=profile_repo.default_branch)
            profile_repo.update_file(
                path="README.md",
                message="🌿 Gardener: Professional Profile README",
                content=readme_content,
                sha=existing.sha,
                branch=profile_repo.default_branch,
            )
        except GithubException:
            profile_repo.create_file(
                path="README.md",
                message="🌿 Gardener: Professional Profile README",
                content=readme_content,
                branch=profile_repo.default_branch,
            )
        g.close()
        return {
            "profile_url": profile_repo.html_url,
            "pr_url": None,
            "created_new": True,
        }

    # Profile repo exists — create a branch and PR
    target_branch = "gardener/update-profile"
    default_branch_name = profile_repo.default_branch
    default_branch = profile_repo.get_branch(default_branch_name)

    try:
        ref = profile_repo.get_git_ref(f"heads/{target_branch}")
        ref.edit(sha=default_branch.commit.sha, force=True)
    except GithubException:
        profile_repo.create_git_ref(
            ref=f"refs/heads/{target_branch}",
            sha=default_branch.commit.sha,
        )

    # Create or update README on the branch
    try:
        existing = profile_repo.get_contents("README.md", ref=target_branch)
        profile_repo.update_file(
            path="README.md",
            message="🌿 Gardener: Professional Profile README",
            content=readme_content,
            sha=existing.sha,
            branch=target_branch,
        )
    except GithubException:
        profile_repo.create_file(
            path="README.md",
            message="🌿 Gardener: Professional Profile README",
            content=readme_content,
            branch=target_branch,
        )

    # Check for existing PR
    existing_prs = profile_repo.get_pulls(
        state="open",
        head=f"{username}:{target_branch}",
        base=default_branch_name,
    )
    if existing_prs.totalCount > 0:
        pr = existing_prs[0]
        g.close()
        return {
            "profile_url": profile_repo.html_url,
            "pr_url": pr.html_url,
            "created_new": False,
        }

    # Create new PR
    try:
        pr = profile_repo.create_pull(
            title="🌿 Gardener: Professional Profile README",
            body=(
                "This profile README was auto-generated by the GitHub Gardener AI.\n\n"
                "It showcases your top projects, tech stack, and developer brand."
            ),
            head=target_branch,
            base=default_branch_name,
        )
        g.close()
        return {
            "profile_url": profile_repo.html_url,
            "pr_url": pr.html_url,
            "created_new": False,
        }
    except GithubException as e:
        if e.status == 422 and "No commits between" in str(e.data):
            g.close()
            return {
                "profile_url": profile_repo.html_url,
                "pr_url": f"{profile_repo.html_url}/tree/{target_branch}",
                "created_new": False,
            }
        raise


@activity.defn
async def create_or_update_profile_repo_activity(
    username: str,
    readme_content: str,
    access_token: str,
) -> dict:
    """Create or update the GitHub profile repo with a generated README."""
    return await asyncio.to_thread(
        _create_or_update_profile_repo, username, readme_content, access_token
    )
