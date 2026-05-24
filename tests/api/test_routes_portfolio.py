"""E2 — integration coverage for app/api/routes/portfolio.py.

Same mocking pattern as test_routes_repos.py. Covers:
  - POST /portfolio/generate (happy + 400 on bad repo count +
    idempotency hit)
  - GET /portfolio/status/{workflow_id} (happy + 404)
  - POST /portfolio/publish (happy)
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-xyz"}


@pytest.fixture
def in_mem_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(
        "app.api.routes.portfolio.get_session",
        lambda: Session(engine),
    )
    return engine


@pytest.fixture
def mock_github(monkeypatch):
    get_username = AsyncMock(return_value="alice")
    monkeypatch.setattr(
        "app.api.routes.portfolio.github_service.get_username", get_username
    )
    return get_username


@pytest.fixture
def mock_temporal(monkeypatch):
    start_workflow = AsyncMock()
    handle = MagicMock()
    handle.query = AsyncMock(return_value={"stage": "generating", "progress": 0.5})
    client_mock = MagicMock()
    client_mock.start_workflow = start_workflow
    client_mock.get_workflow_handle = MagicMock(return_value=handle)

    async def fake_get_temporal():
        return client_mock

    monkeypatch.setattr(
        "app.api.routes.portfolio.get_temporal_client", fake_get_temporal
    )
    return client_mock


class TestGeneratePortfolio:
    def test_happy_path_starts_workflow(
        self, client, auth_headers, mock_github, mock_temporal, in_mem_db,
    ):
        r = client.post(
            "/api/portfolio/generate",
            json={"repo_ids": [1, 2, 3], "bio": "Hi"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["workflow_id"].startswith("portfolio-alice-")
        mock_temporal.start_workflow.assert_awaited_once()

    def test_empty_repo_ids_returns_400(self, client, auth_headers):
        r = client.post(
            "/api/portfolio/generate",
            json={"repo_ids": []},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_too_many_repos_returns_400(self, client, auth_headers):
        r = client.post(
            "/api/portfolio/generate",
            json={"repo_ids": [1, 2, 3, 4, 5, 6, 7]},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_idempotency_hit(
        self, client, auth_headers, mock_github, mock_temporal, in_mem_db,
    ):
        h = {**auth_headers, "Idempotency-Key": "my-portfolio-key"}
        body = {"repo_ids": [1, 2, 3]}
        r1 = client.post("/api/portfolio/generate", json=body, headers=h)
        assert r1.status_code == 200
        wf1 = r1.json()["workflow_id"]

        r2 = client.post("/api/portfolio/generate", json=body, headers=h)
        assert r2.status_code == 200
        assert r2.json()["workflow_id"] == wf1
        assert r2.json()["idempotent"] is True
        # only one start_workflow despite two requests
        assert mock_temporal.start_workflow.await_count == 1


class TestPortfolioStatus:
    def test_status_returns_query_payload(
        self, client, auth_headers, mock_temporal,
    ):
        r = client.get("/api/portfolio/status/wf-123", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["stage"] == "generating"

    def test_status_404_when_workflow_missing(
        self, client, auth_headers, monkeypatch,
    ):
        handle = MagicMock()
        handle.query = AsyncMock(side_effect=RuntimeError("not found"))
        client_mock = MagicMock()
        client_mock.get_workflow_handle = MagicMock(return_value=handle)

        async def fake_get_temporal():
            return client_mock
        monkeypatch.setattr(
            "app.api.routes.portfolio.get_temporal_client", fake_get_temporal
        )

        r = client.get("/api/portfolio/status/wf-bad", headers=auth_headers)
        assert r.status_code == 404


class TestPortfolioPublish:
    def test_publish_calls_activity(
        self, client, auth_headers, mock_github, monkeypatch,
    ):
        monkeypatch.setattr(
            "app.api.routes.portfolio.create_or_update_profile_repo_activity",
            AsyncMock(return_value={
                "profile_url": "https://github.com/alice/alice",
                "pr_url": "https://github.com/alice/alice/pull/1",
            }),
        )
        r = client.post(
            "/api/portfolio/publish",
            json={"readme_content": "# my profile"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "published"
        assert body["profile_url"].endswith("/alice/alice")
        assert body["pr_url"].endswith("/pull/1")
