import asyncio
import uuid as _uuid
from datetime import datetime, timezone

from temporalio import activity

from github import Auth, Github, GithubException

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

    g.close()

    return {
        "repo_name": repo.full_name,
        "health_score": max(score, 0),
        "issues": issues,
        "last_commit_date": last_commit_date.isoformat(),
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
# Phase 6: Janitor Activities
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
    """Generate a README.md using LiteLLM."""
    return await llm_service.generate_readme(repo_name, file_structure, description)


def _create_pull_request(repo_full_name: str, content: str, access_token: str) -> str:
    """Create a branch, commit README.md, and open a PR — synchronous PyGithub."""
    g = Github(access_token)
    repo = g.get_repo(repo_full_name)

    # 1. Define a consistent branch name (Idempotent)
    target_branch = "gardener/readme-fix"
    default_branch_name = repo.default_branch
    default_branch = repo.get_branch(default_branch_name)

    # 2. Get or Create the Branch
    try:
        # Try to find the existing gardener branch
        repo.get_git_ref(f"heads/{target_branch}")
        print(f"Branch {target_branch} already exists. Reusing it.")
    except GithubException:
        # Create it if it doesn't exist, pointing to the latest default branch commit
        repo.create_git_ref(ref=f"refs/heads/{target_branch}", sha=default_branch.commit.sha)
        print(f"Created new branch {target_branch}")

    # 3. Create or Update the README file on that branch
    file_path = "README.md"
    message = "🌿 Gardener: Enhanced Documentation"
    try:
        # Check if file exists ON THE TARGET BRANCH
        contents = repo.get_contents(file_path, ref=target_branch)
        # Update it
        repo.update_file(
            path=file_path,
            message=message,
            content=content,
            sha=contents.sha,
            branch=target_branch
        )
    except GithubException:
        # File doesn't exist on target branch, create it
        repo.create_file(
            path=file_path,
            message=message,
            content=content,
            branch=target_branch
        )

    # 4. Check for an existing Pull Request to avoid duplicates
    existing_prs = repo.get_pulls(
        state='open',
        head=f"{repo.owner.login}:{target_branch}",
        base=default_branch_name
    )
    if existing_prs.totalCount > 0:
        pr = existing_prs[0]
        print(f"PR already exists: {pr.html_url}")
        g.close()
        return pr.html_url

    # 5. Create new PR if none exists
    pr = repo.create_pull(
        title="🌿 Gardener: Added README.md",
        body="This documentation was auto-generated by the GitHub Gardener AI based on a file structure analysis.",
        head=target_branch,
        base=default_branch_name
    )

    pr_url = pr.html_url
    g.close()
    return pr_url


@activity.defn
async def create_pull_request_activity(repo_full_name: str, content: str, access_token: str) -> str:
    """Create a branch with README.md and open a Pull Request."""
    return await asyncio.to_thread(_create_pull_request, repo_full_name, content, access_token)
