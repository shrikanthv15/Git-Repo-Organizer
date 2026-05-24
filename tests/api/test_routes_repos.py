"""E2 — integration coverage for app/api/routes/repos.py.

Mocks github_service + temporal client + activities at the route boundary
so we exercise the routing + auth + DB layers without hitting real
external services. Covers most paths in:
  - /repos (GET, hydration with stored analysis)
  - /analyze/{repo_id} (POST + 404)
  - /fix/{repo_id} (POST + 404 + idempotency hit)
  - /sync (POST)
  - /repos/{repo_id}/commit (POST happy + 404 no draft + 400 no files +
    repo not found + idempotency hit)
  - /test-workflow (POST)
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.crud import (
    save_draft_proposal,
    upsert_analysis_result,
    upsert_repository,
    upsert_user,
)
from app.main import app


def _engine():
    e = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(e)
    return e


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-xyz"}


@pytest.fixture
def seeded_db(monkeypatch):
    """Patch get_session in routes/repos.py to use an in-memory DB
    pre-loaded with a user + one repo + one analysis result.
    """
    engine = _engine()
    with Session(engine) as s:
        user = upsert_user(s, github_id=42, username="alice")
        repo = upsert_repository(
            s, github_repo_id=12345, owner_id=user.id, name="proj",
            full_name="alice/proj", html_url="https://github.com/alice/proj",
        )
        upsert_analysis_result(
            s, repo_id=repo.id, health_score=85, issues=["No CHANGELOG"],
            pending_fix_url=None,
        )
        s.commit()

    def fake_get_session():
        return Session(engine)

    monkeypatch.setattr("app.api.routes.repos.get_session", fake_get_session)
    return engine


@pytest.fixture
def mock_temporal(monkeypatch):
    """Patch get_temporal_client in all routes to a no-op AsyncMock client."""
    start_workflow = AsyncMock()
    execute_workflow = AsyncMock(return_value="mocked-result")
    client_mock = MagicMock()
    client_mock.start_workflow = start_workflow
    client_mock.execute_workflow = execute_workflow

    async def fake_get_temporal():
        return client_mock

    monkeypatch.setattr("app.api.routes.repos.get_temporal_client", fake_get_temporal)
    return client_mock


@pytest.fixture
def mock_github(monkeypatch):
    """Patch github_service module functions used by routes/repos.py."""
    from app.schemas.github import Repo as RepoSchema

    list_user_repos = AsyncMock(return_value=[
        RepoSchema(
            id=12345, name="proj", full_name="alice/proj",
            private=False, html_url="https://github.com/alice/proj",
            description="d",
        ),
        RepoSchema(
            id=99, name="other", full_name="alice/other",
            private=False, html_url="https://github.com/alice/other",
            description=None,
        ),
    ])
    get_repo_full_name = AsyncMock(return_value="alice/proj")
    get_repo_details = AsyncMock(return_value={
        "name": "proj", "full_name": "alice/proj", "description": "d",
    })

    monkeypatch.setattr("app.api.routes.repos.github_service.list_user_repos", list_user_repos)
    monkeypatch.setattr("app.api.routes.repos.github_service.get_repo_full_name", get_repo_full_name)
    monkeypatch.setattr("app.api.routes.repos.github_service.get_repo_details", get_repo_details)


class TestAuth:
    def test_missing_auth_returns_401(self, client):
        # /repos requires auth; without header → 401
        assert client.get("/api/repos").status_code == 401

    def test_empty_bearer_returns_401(self, client):
        r = client.get("/api/repos", headers={"Authorization": "Bearer "})
        assert r.status_code == 401


class TestListRepos:
    def test_hydrates_with_stored_analysis(
        self, client, auth_headers, seeded_db, mock_github,
    ):
        r = client.get("/api/repos", headers=auth_headers)
        assert r.status_code == 200
        repos = r.json()
        assert len(repos) == 2
        proj = next(x for x in repos if x["id"] == 12345)
        # Hydrated from DB
        assert proj["health"]["health_score"] == 85
        assert proj["health"]["issues"] == ["No CHANGELOG"]
        # The other repo has no analysis → no health field populated
        other = next(x for x in repos if x["id"] == 99)
        assert other.get("health") is None

    def test_github_fail_returns_502(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.repos.github_service.list_user_repos",
            AsyncMock(side_effect=RuntimeError("oops")),
        )
        r = client.get("/api/repos", headers=auth_headers)
        assert r.status_code == 502

    def test_db_fail_falls_back_to_empty_analysis(
        self, client, auth_headers, mock_github, monkeypatch,
    ):
        # Don't seed the DB; let get_latest_analysis_for_repos raise
        def fake_session():
            raise RuntimeError("db down")
        monkeypatch.setattr("app.api.routes.repos.get_session", fake_session)

        r = client.get("/api/repos", headers=auth_headers)
        # Route catches DB errors and returns repos without analysis
        assert r.status_code == 200
        for repo in r.json():
            assert repo.get("health") is None


class TestAnalyzeRepo:
    def test_starts_workflow(
        self, client, auth_headers, mock_github, mock_temporal,
    ):
        r = client.post("/api/analyze/12345", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["workflow_id"].startswith("analysis-12345-")
        mock_temporal.start_workflow.assert_awaited_once()

    def test_repo_not_found_returns_404(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.repos.github_service.get_repo_full_name",
            AsyncMock(side_effect=RuntimeError("404")),
        )
        r = client.post("/api/analyze/99999", headers=auth_headers)
        assert r.status_code == 404


class TestFixRepo:
    def test_starts_janitor_workflow(
        self, client, auth_headers, mock_github, mock_temporal,
    ):
        r = client.post("/api/fix/12345", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["workflow_id"].startswith("janitor-12345-")
        mock_temporal.start_workflow.assert_awaited_once()

    def test_repo_not_found_returns_404(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.repos.github_service.get_repo_details",
            AsyncMock(side_effect=RuntimeError("404")),
        )
        r = client.post("/api/fix/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_idempotency_hit_returns_cached_workflow(
        self, client, auth_headers, mock_github, mock_temporal, seeded_db,
    ):
        # First call records the key
        h1 = {**auth_headers, "Idempotency-Key": "my-fix-key"}
        r1 = client.post("/api/fix/12345", headers=h1)
        assert r1.status_code == 200
        wf1 = r1.json()["workflow_id"]
        # Second call: same key → cached, NOT a new Temporal call
        r2 = client.post("/api/fix/12345", headers=h1)
        assert r2.status_code == 200
        assert r2.json()["workflow_id"] == wf1
        assert r2.json()["idempotent"] is True
        # start_workflow only fired once
        assert mock_temporal.start_workflow.await_count == 1


class TestSync:
    def test_calls_sync_pr_status_activity(self, client, auth_headers, monkeypatch):
        sync_mock = AsyncMock(return_value=3)
        monkeypatch.setattr(
            "app.temporal.activities.sync_pr_status_activity",
            sync_mock,
        )
        r = client.post("/api/sync", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "synced"
        assert body["updated_count"] == 3


class TestCommitDocs:
    def _seed_draft(self, engine, draft):
        with Session(engine) as s:
            user = upsert_user(s, github_id=43, username="bob")
            repo = upsert_repository(
                s, github_repo_id=12345, owner_id=user.id, name="proj",
                full_name="alice/proj", html_url="https://github.com/alice/proj",
            )
            upsert_analysis_result(
                s, repo_id=repo.id, health_score=80, issues=[], pending_fix_url=None,
            )
            save_draft_proposal(s, github_repo_id=12345, draft_proposal=draft)
            s.commit()

    def test_no_draft_returns_404(self, client, auth_headers, monkeypatch):
        engine = _engine()
        monkeypatch.setattr("app.api.routes.repos.get_session", lambda: Session(engine))
        r = client.post(
            "/api/repos/12345/commit",
            json={"selected_files": ["README.md"]},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_no_valid_files_returns_400(self, client, auth_headers, monkeypatch):
        engine = _engine()
        self._seed_draft(engine, {"README.md": "# hi"})
        monkeypatch.setattr("app.api.routes.repos.get_session", lambda: Session(engine))
        r = client.post(
            "/api/repos/12345/commit",
            json={"selected_files": ["NOT_PRESENT.md"]},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_repo_not_found_after_draft_returns_404(
        self, client, auth_headers, monkeypatch,
    ):
        engine = _engine()
        self._seed_draft(engine, {"README.md": "# hi"})
        monkeypatch.setattr("app.api.routes.repos.get_session", lambda: Session(engine))
        monkeypatch.setattr(
            "app.api.routes.repos.github_service.get_repo_details",
            AsyncMock(side_effect=RuntimeError("nope")),
        )
        r = client.post(
            "/api/repos/12345/commit",
            json={"selected_files": ["README.md"]},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_happy_path(self, client, auth_headers, monkeypatch):
        engine = _engine()
        self._seed_draft(engine, {"README.md": "# hi", "CONTRIBUTING.md": "# c"})
        monkeypatch.setattr("app.api.routes.repos.get_session", lambda: Session(engine))
        monkeypatch.setattr(
            "app.api.routes.repos.github_service.get_repo_details",
            AsyncMock(return_value={
                "name": "proj", "full_name": "alice/proj", "description": "",
            }),
        )
        # The route calls create_docs_pull_request_activity directly
        monkeypatch.setattr(
            "app.api.routes.repos.create_docs_pull_request_activity",
            AsyncMock(return_value="https://github.com/alice/proj/pull/42"),
        )
        r = client.post(
            "/api/repos/12345/commit",
            json={
                "selected_files": ["README.md"],
                "edited_contents": {"README.md": "# edited"},
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "committed"
        assert body["pr_url"].endswith("/pull/42")


class TestTestWorkflow:
    def test_test_workflow_executes(self, client, auth_headers, mock_temporal):
        r = client.post("/api/test-workflow", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["result"] == "mocked-result"
