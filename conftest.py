"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_github():
    """Mock GitHub API client."""
    return MagicMock()


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    return MagicMock()


@pytest.fixture
def async_mock():
    """Provide AsyncMock for creating async mocks."""
    return AsyncMock
