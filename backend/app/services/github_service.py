"""High-level async GitHub helpers.

Wraps :class:`app.services.github_client.GithubClient` (which adds
rate-limit-aware retries) in ``asyncio.to_thread()`` so they're safe to
call from FastAPI / Temporal activity event loops.

The non-rate-limited bit — :func:`exchange_code_for_token` — uses ``httpx``
directly since OAuth code exchange isn't governed by the same per-token
rate limits.
"""
import asyncio

import httpx

from app.core.config import settings
from app.schemas.github import Repo
from app.services.github_client import GithubClient

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
    """Sync helper — run via asyncio.to_thread."""
    with GithubClient(access_token) as client:
        return [Repo(**row) for row in client.list_user_repos_as_dicts()]


async def list_user_repos(access_token: str) -> list[Repo]:
    """Fetch all repos for the authenticated user."""
    return await asyncio.to_thread(_fetch_repos, access_token)


def _get_repo_full_name(access_token: str, repo_id: int) -> str:
    with GithubClient(access_token) as client:
        return client.get_repo_full_name(repo_id)


async def get_repo_full_name(access_token: str, repo_id: int) -> str:
    """Look up a repo's full_name by its integer ID."""
    return await asyncio.to_thread(_get_repo_full_name, access_token, repo_id)


def _get_repo_details(access_token: str, repo_id: int) -> dict:
    with GithubClient(access_token) as client:
        return client.get_repo_details(repo_id)


async def get_repo_details(access_token: str, repo_id: int) -> dict:
    """Look up a repo's name, full_name, and description by ID."""
    return await asyncio.to_thread(_get_repo_details, access_token, repo_id)


def _get_username(access_token: str) -> str:
    with GithubClient(access_token) as client:
        return client.get_user_login()


async def get_username(access_token: str) -> str:
    """Get the authenticated user's GitHub username."""
    return await asyncio.to_thread(_get_username, access_token)
