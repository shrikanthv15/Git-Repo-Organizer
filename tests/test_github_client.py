"""E5 — GithubClient rate-limit behavior.

Mocks ``github.Github`` so tests don't hit the real API. Covers:
- Normal call (remaining high) → no sleep, returns value
- Low rate limit (remaining < 100) → backs off then returns
- Exhausted (remaining == 0) → raises GithubRateLimitError with reset_at
- RateLimitExceededException on the wire → converted to GithubRateLimitError
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.github_client import (
    GithubClient,
    GithubRateLimitError,
    REMAINING_WARN_THRESHOLD,
)


def _make_mock_rate_limit(remaining: int, reset_minutes_ahead: int = 30) -> MagicMock:
    rl = MagicMock()
    rl.core.remaining = remaining
    rl.core.reset = datetime.now(timezone.utc) + timedelta(minutes=reset_minutes_ahead)
    return rl


def _patched_client(remaining: int):
    """Build a GithubClient whose underlying Github is fully mocked."""
    with patch("app.services.github_client.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_rate_limit.return_value = _make_mock_rate_limit(remaining)
        client = GithubClient("fake-token-test-only")
        return client, instance


class TestRateLimitBranches:
    def test_remaining_high_no_backoff(self):
        client, gh = _patched_client(remaining=4500)
        gh.get_user.return_value.login = "alice"
        # No sleep should fire; call returns immediately
        with patch("app.services.github_client.time.sleep") as sleep_mock:
            assert client.get_user_login() == "alice"
            sleep_mock.assert_not_called()

    def test_remaining_low_triggers_backoff(self):
        client, gh = _patched_client(remaining=50)  # below 100 threshold
        gh.get_user.return_value.login = "bob"
        with patch("app.services.github_client.time.sleep") as sleep_mock:
            assert client.get_user_login() == "bob"
            # Sleep was called once with a positive duration
            sleep_mock.assert_called_once()
            slept_for = sleep_mock.call_args[0][0]
            assert slept_for > 0
            assert slept_for <= 60  # MAX_BACKOFF_SECONDS

    def test_remaining_zero_raises(self):
        client, gh = _patched_client(remaining=0)
        with pytest.raises(GithubRateLimitError) as exc_info:
            client.get_user_login()
        # The raised error carries a future reset_at
        assert exc_info.value.reset_at > datetime.now(timezone.utc) - timedelta(seconds=5)

    def test_remaining_at_threshold_no_backoff(self):
        # Exactly at threshold should NOT trigger backoff (strict <)
        client, gh = _patched_client(remaining=REMAINING_WARN_THRESHOLD)
        gh.get_user.return_value.login = "carol"
        with patch("app.services.github_client.time.sleep") as sleep_mock:
            assert client.get_user_login() == "carol"
            sleep_mock.assert_not_called()


class TestApiErrorConversion:
    def test_rate_limit_exception_converted(self):
        """When PyGithub itself raises RateLimitExceededException, we convert to GithubRateLimitError."""
        from github.GithubException import RateLimitExceededException

        client, gh = _patched_client(remaining=500)  # pre-flight passes
        # First get_rate_limit() (pre-flight): remaining=500. Second
        # (post-error, for reset_at): also 500. The actual call raises.
        gh.get_user.side_effect = RateLimitExceededException(
            403, {"message": "API rate limit exceeded"}, {"X-RateLimit-Remaining": "0"}
        )
        with pytest.raises(GithubRateLimitError):
            client.get_user_login()


class TestPublicSurface:
    def test_list_user_repos_as_dicts_shape(self):
        client, gh = _patched_client(remaining=4500)
        # MagicMock(name=...) sets the mock's display name, not the
        # .name attribute. Set explicitly.
        fake_repo = MagicMock(
            id=123, full_name="alice/r", private=False,
            html_url="https://github.com/alice/r", description="d",
        )
        fake_repo.name = "r"
        gh.get_user.return_value.get_repos.return_value = [fake_repo]
        out = client.list_user_repos_as_dicts()
        assert out == [{
            "id": 123, "name": "r", "full_name": "alice/r",
            "private": False, "html_url": "https://github.com/alice/r",
            "description": "d",
        }]

    def test_get_repo_full_name(self):
        client, gh = _patched_client(remaining=4500)
        gh.get_repo.return_value.full_name = "alice/proj"
        assert client.get_repo_full_name(42) == "alice/proj"

    def test_get_repo_details(self):
        client, gh = _patched_client(remaining=4500)
        fake = MagicMock(name="r", full_name="alice/r", description=None)
        # MagicMock attribute aliasing — set explicitly because `name` is special
        fake.name = "r"
        gh.get_repo.return_value = fake
        out = client.get_repo_details(42)
        assert out == {"name": "r", "full_name": "alice/r", "description": ""}


class TestContextManager:
    def test_enter_exit_closes_github(self):
        with patch("app.services.github_client.Github") as MockGithub:
            instance = MockGithub.return_value
            with GithubClient("fake") as client:
                pass
            instance.close.assert_called_once()
