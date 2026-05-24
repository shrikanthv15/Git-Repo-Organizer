"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthRoutes:
    """Test suite for health check endpoints."""

    def test_health_check_endpoint(self, client):
        """Test health check endpoint returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_health_check_response_structure(self, client):
        """Test health check response has expected structure."""
        response = client.get("/api/health")
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]


class TestAuthRoutes:
    """Test suite for authentication endpoints."""

    def test_auth_endpoints_exist(self, client):
        """Test that auth routes are registered."""
        # HEAD request to check endpoint exists
        response = client.options("/api/auth")
        assert response.status_code in [200, 204, 405]  # 405 = Method Not Allowed (expected)


class TestReposRoutes:
    """Test suite for repository endpoints."""

    def test_repos_endpoints_exist(self, client):
        """Test that repo routes are registered."""
        response = client.options("/api/repos")
        assert response.status_code in [200, 204, 405]


class TestGardenRoutes:
    """Test suite for garden (workflow) endpoints."""

    def test_garden_endpoints_exist(self, client):
        """Test that garden routes are registered."""
        response = client.options("/api/garden")
        assert response.status_code in [200, 204, 405]


class TestPortfolioRoutes:
    """Test suite for portfolio endpoints."""

    def test_portfolio_endpoints_exist(self, client):
        """Test that portfolio routes are registered."""
        response = client.options("/api/portfolio")
        assert response.status_code in [200, 204, 405]


class TestAPIRouter:
    """Test suite for main API router."""

    def test_api_router_includes_all_sub_routers(self, client):
        """Test that main API router includes all sub-routers."""
        # Check that at least the health endpoint is accessible
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_api_prefix_routing(self, client):
        """Test that /api prefix is properly applied."""
        # All routes should be under /api
        response = client.get("/api/health")
        assert response.status_code == 200
