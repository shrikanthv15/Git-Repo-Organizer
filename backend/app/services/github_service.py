import asyncio

import httpx
from github import Auth, Github

from app.core.config import settings
from app.schemas.github import Repo

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


async def exchange_code_for_token(code: str) -> str:
    """Exchange a GitHub OAuth code for an access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        raise ValueError(f"GitHub OAuth error: {data['error_description']}")

    return data["access_token"]


def _fetch_repos(access_token: str) -> list[Repo]:
    """Synchronous PyGithub call — run via asyncio.to_thread."""
    g = Github(auth=Auth.Token(access_token))
    repos = []
    for r in g.get_user().get_repos(affiliation="owner"):
        repos.append(
            Repo(
                id=r.id,
                name=r.name,
                full_name=r.full_name,
                private=r.private,
                html_url=r.html_url,
                description=r.description,
            )
        )
    g.close()
    return repos


async def list_user_repos(access_token: str) -> list[Repo]:
    """Fetch all repos for the authenticated user."""
    return await asyncio.to_thread(_fetch_repos, access_token)


def _get_repo_full_name(access_token: str, repo_id: int) -> str:
    """Synchronous PyGithub call — run via asyncio.to_thread."""
    g = Github(auth=Auth.Token(access_token))
    repo = g.get_repo(repo_id)
    full_name = repo.full_name
    g.close()
    return full_name


async def get_repo_full_name(access_token: str, repo_id: int) -> str:
    """Look up a repo's full_name by its integer ID."""
    return await asyncio.to_thread(_get_repo_full_name, access_token, repo_id)


def _get_repo_details(access_token: str, repo_id: int) -> dict:
    """Synchronous PyGithub call — run via asyncio.to_thread."""
    g = Github(auth=Auth.Token(access_token))
    repo = g.get_repo(repo_id)
    details = {
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description or "",
    }
    g.close()
    return details


async def get_repo_details(access_token: str, repo_id: int) -> dict:
    """Look up a repo's name, full_name, and description by ID."""
    return await asyncio.to_thread(_get_repo_details, access_token, repo_id)


def _get_username(access_token: str) -> str:
    """Synchronous PyGithub call — run via asyncio.to_thread."""
    g = Github(auth=Auth.Token(access_token))
    username = g.get_user().login
    g.close()
    return username


async def get_username(access_token: str) -> str:
    """Get the authenticated user's GitHub username."""
    return await asyncio.to_thread(_get_username, access_token)
