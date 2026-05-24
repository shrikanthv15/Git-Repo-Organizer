"""Tests for temporal activities analysis module."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from app.temporal.activities.analysis import say_hello, _analyze_repo


class TestAnalysisActivities:
    """Test suite for analysis activities module."""

    @pytest.mark.asyncio
    async def test_say_hello_happy_path(self):
        """Test greeting activity with valid input."""
        result = await say_hello("Alice")
        assert result == "Hello Alice, the Gardener is ready!"
        assert "Gardener" in result

    @pytest.mark.asyncio
    async def test_say_hello_empty_name(self):
        """Test greeting activity with empty name."""
        result = await say_hello("")
        assert result == "Hello , the Gardener is ready!"

    @pytest.mark.asyncio
    async def test_say_hello_special_chars(self):
        """Test greeting activity with special characters in name."""
        result = await say_hello("Alice@#$%")
        assert "Alice@#$%" in result
        assert "Gardener" in result

    @pytest.mark.asyncio
    async def test_say_hello_numeric(self):
        """Test greeting activity with numeric name."""
        result = await say_hello("12345")
        assert "12345" in result
        assert "Gardener" in result

    def test_analyze_repo_invalid_token_error(self):
        """Test repo analysis with invalid GitHub token - error path."""
        with pytest.raises(ValueError) as exc_info:
            _analyze_repo("invalid-org/invalid-repo", "invalid-token")
        assert "Could not fetch repo" in str(exc_info.value)

    def test_analyze_repo_nonexistent_repo_error(self):
        """Test repo analysis with nonexistent repo - error path."""
        with pytest.raises(ValueError) as exc_info:
            _analyze_repo("nonexistent-org-99999/nonexistent-repo-88888", "fake-token")
        assert "Could not fetch repo" in str(exc_info.value)

    @patch('app.temporal.activities.analysis.get_session')
    @patch('app.temporal.activities.analysis.Github')
    def test_analyze_repo_happy_path_healthy_repo(self, mock_github_class, mock_session):
        """Test repo analysis happy path with healthy repo."""
        # Setup mock repo
        mock_pull_list = MagicMock()
        mock_pull_list.totalCount = 0
        
        mock_repo = MagicMock()
        mock_repo.full_name = "owner/healthy-repo"
        mock_repo.name = "healthy-repo"
        mock_repo.id = 12345
        mock_repo.html_url = "https://github.com/owner/healthy-repo"
        mock_repo.owner.id = 123
        mock_repo.owner.login = "owner"
        mock_repo.pushed_at = datetime.now(timezone.utc)
        mock_repo.description = "A healthy repo"
        mock_repo.get_readme.return_value = MagicMock()
        mock_repo.get_commits.return_value = []
        mock_repo.get_pulls.return_value = mock_pull_list

        mock_github = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Mock database operations
        mock_session_context = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_context.__enter__ = MagicMock(return_value=mock_session_instance)
        mock_session_context.__exit__ = MagicMock(return_value=None)
        mock_session.return_value = mock_session_context

        result = _analyze_repo("owner/healthy-repo", "valid-token")
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "repo_name" in result
        assert "health_score" in result
        assert "issues" in result
        assert result["repo_name"] == "owner/healthy-repo"
        assert result["health_score"] >= 90  # Should be high for healthy repo

    @patch('app.temporal.activities.analysis.get_session')
    @patch('app.temporal.activities.analysis.Github')
    def test_analyze_repo_returns_correct_structure(self, mock_github_class, mock_session):
        """Test that repo analysis returns the correct data structure."""
        # Setup minimal mock repo
        mock_pull_list = MagicMock()
        mock_pull_list.totalCount = 0
        
        mock_repo = MagicMock()
        mock_repo.full_name = "org/repo"
        mock_repo.name = "repo"
        mock_repo.id = 111
        mock_repo.html_url = "https://github.com/org/repo"
        mock_repo.owner.id = 222
        mock_repo.owner.login = "org"
        mock_repo.pushed_at = datetime.now(timezone.utc) - timedelta(days=5)
        mock_repo.description = "Test repo"
        mock_repo.get_readme.return_value = MagicMock()
        mock_repo.get_commits.return_value = []
        mock_repo.get_pulls.return_value = mock_pull_list

        mock_github = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Mock database operations
        mock_session_context = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_context.__enter__ = MagicMock(return_value=mock_session_instance)
        mock_session_context.__exit__ = MagicMock(return_value=None)
        mock_session.return_value = mock_session_context

        result = _analyze_repo("org/repo", "token")
        
        # Verify all expected keys are present
        expected_keys = {"repo_name", "health_score", "issues", "last_commit_date"}
        assert expected_keys.issubset(result.keys())
        assert isinstance(result["health_score"], (int, float))
        assert isinstance(result["issues"], list)
