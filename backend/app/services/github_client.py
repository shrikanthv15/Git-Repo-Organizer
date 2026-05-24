"""GitHub API client wrapper with rate-limit-aware retries.

Wraps :class:`github.Github` so every call:
- inspects ``rate_limit.core`` before firing (pre-flight check)
- backs off with exponential + jitter when ``remaining < REMAINING_WARN_THRESHOLD``
- raises a typed :class:`GithubRateLimitError` when ``remaining == 0``
  so calling Temporal activities can catch + sleep until ``reset_at`` + retry

Per E5 guardrails — see ``docs/adr/0005-guardrails.md`` (TODO: when JL
re-runs E5, Batman will write the ADR).
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Callable, TypeVar

import structlog
from github import Auth, Github
from github.GithubException import RateLimitExceededException

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# When core rate limit remaining drops below this, start backing off
# proactively rather than hammering until 0.
REMAINING_WARN_THRESHOLD = 100

# Max seconds to sleep in a single backoff (don't park the activity forever).
MAX_BACKOFF_SECONDS = 60


class GithubRateLimitError(Exception):
    """Raised when the GitHub API rate limit is fully exhausted.

    Attributes:
        reset_at: timezone-aware UTC datetime when the rate-limit window
            resets. Calling code (typically a Temporal activity) can sleep
            until ``reset_at`` and retry.
    """

    def __init__(self, message: str, reset_at: datetime) -> None:
        super().__init__(message)
        self.reset_at = reset_at


class GithubClient:
    """Rate-limit-aware wrapper around :class:`github.Github`.

    Use as a context manager so the underlying connection is closed:

        with GithubClient(token) as client:
            repos = client.list_user_repos()

    All call methods log the current ``remaining`` / ``reset_at`` at
    activity start (via structlog) so cross-activity logs can be filtered
    by ``github_rate_limit_*`` event names.
    """

    def __init__(self, access_token: str) -> None:
        self._github = Github(auth=Auth.Token(access_token))
        self._logged_initial_state = False

    def close(self) -> None:
        self._github.close()

    def __enter__(self) -> "GithubClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    # -- internals --------------------------------------------------------

    def _read_rate_limit(self) -> tuple[int, datetime]:
        """Return ``(remaining, reset_at_utc)`` for the core rate limit."""
        rl = self._github.get_rate_limit()
        reset_at = rl.core.reset
        # PyGithub returns a naive UTC datetime; tag it explicitly.
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        return rl.core.remaining, reset_at

    def _log_initial_state(self) -> None:
        if self._logged_initial_state:
            return
        try:
            remaining, reset_at = self._read_rate_limit()
            logger.info(
                "github_rate_limit_state",
                remaining=remaining,
                reset_at=reset_at.isoformat(),
            )
        except Exception as exc:  # pragma: no cover — network paths
            logger.warning("github_rate_limit_read_failed", error=str(exc))
        self._logged_initial_state = True

    def _wait_or_raise(self) -> None:
        """Pre-flight: check rate limit, back off or raise as appropriate."""
        try:
            remaining, reset_at = self._read_rate_limit()
        except Exception as exc:
            # If we can't read the rate limit (e.g. network blip), let the
            # actual call attempt — RateLimitExceededException will catch
            # if we truly are out.
            logger.warning("github_rate_limit_read_failed", error=str(exc))
            return

        if remaining == 0:
            now = datetime.now(timezone.utc)
            wait_seconds = max(0, int((reset_at - now).total_seconds()))
            logger.warning(
                "github_rate_limit_exhausted",
                remaining=0,
                reset_at=reset_at.isoformat(),
                wait_seconds=wait_seconds,
            )
            raise GithubRateLimitError(
                f"GitHub rate limit exhausted; resets at "
                f"{reset_at.isoformat()} ({wait_seconds}s from now)",
                reset_at=reset_at,
            )

        if remaining < REMAINING_WARN_THRESHOLD:
            # Exponential backoff with jitter. Sleep more as remaining drops.
            # remaining=99 → ~0.2s; remaining=10 → ~18s; remaining=1 → ~20s
            depth = max(1, REMAINING_WARN_THRESHOLD - remaining)
            jitter = random.uniform(0, 1)
            sleep_seconds = min(MAX_BACKOFF_SECONDS, 0.2 * depth + jitter)
            logger.warning(
                "github_rate_limit_low",
                remaining=remaining,
                reset_at=reset_at.isoformat(),
                backoff_seconds=round(sleep_seconds, 2),
            )
            time.sleep(sleep_seconds)

    def _call(self, fn: Callable[[], T]) -> T:
        """Run a PyGithub call with pre-flight check + typed-error conversion."""
        self._log_initial_state()
        self._wait_or_raise()
        try:
            return fn()
        except RateLimitExceededException as exc:
            # Server-side rate limit (the 403 with X-RateLimit-Remaining: 0)
            try:
                _, reset_at = self._read_rate_limit()
            except Exception:
                reset_at = datetime.now(timezone.utc)
            raise GithubRateLimitError(
                f"GitHub rate limit hit on the wire: {exc}",
                reset_at=reset_at,
            ) from exc

    # -- methods used by github_service.py --------------------------------

    def get_user_login(self) -> str:
        return self._call(lambda: self._github.get_user().login)

    def list_user_repos_as_dicts(self) -> list[dict]:
        """Return list of dicts matching the shape ``Repo`` schema expects."""
        def fetch() -> list[dict]:
            out: list[dict] = []
            for r in self._github.get_user().get_repos(affiliation="owner"):
                out.append({
                    "id": r.id,
                    "name": r.name,
                    "full_name": r.full_name,
                    "private": r.private,
                    "html_url": r.html_url,
                    "description": r.description,
                })
            return out
        return self._call(fetch)

    def get_repo_full_name(self, repo_id: int) -> str:
        return self._call(lambda: self._github.get_repo(repo_id).full_name)

    def get_repo_details(self, repo_id: int) -> dict:
        def fetch() -> dict:
            r = self._github.get_repo(repo_id)
            return {
                "name": r.name,
                "full_name": r.full_name,
                "description": r.description or "",
            }
        return self._call(fetch)
