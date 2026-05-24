import asyncio
import json

from temporalio import activity
from github import Auth, Github, GithubException

from app.db.session import get_session
from app.db.crud import update_structure_map


# ---------------------------------------------------------------------------
# Phase 12/13: Documentation Suite PR Creation
# ---------------------------------------------------------------------------

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
# Phase 19: Portfolio Architect
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
