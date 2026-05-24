import asyncio
from datetime import datetime, timezone
from pathlib import Path

from temporalio import activity
from github import Auth, Github, GithubException

from app.db.crud import (
    upsert_user,
    upsert_repository,
    upsert_analysis_result,
    update_structure_map,
)
from app.db.session import get_session


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
    import subprocess
    import tempfile
    from urllib.parse import urlparse
    
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
# Phase 6: Legacy Backward Compat Activity
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
