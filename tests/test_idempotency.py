"""E5 — Idempotency-Key dedup for mutating endpoints.

Covers:
- fingerprint_token determinism
- lookup_idempotency_key returns None when no row / outside window
- lookup returns workflow_id when row exists within window
- record_idempotency_key roundtrip
- record is idempotent on duplicate (race safety)
- get_idempotency_key header parser (empty / too-long / good)
- End-to-end: POST /api/garden twice with same key spawns ONE workflow
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.models import IdempotencyKey


def _make_inmem_engine():
    """SQLite in-memory engine that shares ONE connection across the engine.

    Without StaticPool, every Session opens a fresh connection — and each
    fresh ``sqlite://`` connection is its own isolated database, so a table
    created on one connection is invisible on the next. StaticPool reuses
    one underlying connection so create_all + every session see the same DB.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    return engine
from app.services.idempotency import (
    DEDUP_WINDOW,
    fingerprint_token,
    get_idempotency_key,
    lookup_idempotency_key,
    record_idempotency_key,
)


@pytest.fixture
def session():
    """In-memory SQLite session with our models loaded."""
    engine = _make_inmem_engine()
    with Session(engine) as s:
        yield s


class TestFingerprint:
    def test_deterministic(self):
        assert fingerprint_token("abc") == fingerprint_token("abc")

    def test_distinct_for_distinct_tokens(self):
        assert fingerprint_token("abc") != fingerprint_token("xyz")

    def test_length_32(self):
        # 32 hex chars = 128 bits of entropy
        assert len(fingerprint_token("token")) == 32

    def test_does_not_contain_raw_token(self):
        secret = "ghp_supersecrettokenvalue"
        fp = fingerprint_token(secret)
        assert secret not in fp


class TestLookup:
    def test_returns_none_when_no_row(self, session):
        assert lookup_idempotency_key(
            session, key="k1", token="tok", endpoint="/garden",
        ) is None

    def test_returns_workflow_id_when_within_window(self, session):
        record_idempotency_key(
            session, key="k1", token="tok",
            endpoint="/garden", workflow_id="wf-123",
        )
        session.commit()
        out = lookup_idempotency_key(
            session, key="k1", token="tok", endpoint="/garden",
        )
        assert out == "wf-123"

    def test_returns_none_when_outside_window(self, session):
        # Insert an old row directly
        old = IdempotencyKey(
            token_fingerprint=fingerprint_token("tok"),
            key="k1", endpoint="/garden", workflow_id="wf-old",
            created_at=datetime.now(timezone.utc) - DEDUP_WINDOW - timedelta(hours=1),
        )
        session.add(old)
        session.commit()
        out = lookup_idempotency_key(
            session, key="k1", token="tok", endpoint="/garden",
        )
        assert out is None

    def test_endpoint_scoping(self, session):
        record_idempotency_key(
            session, key="k1", token="tok",
            endpoint="/garden", workflow_id="wf-garden",
        )
        session.commit()
        # Same key, same token, DIFFERENT endpoint → miss
        assert lookup_idempotency_key(
            session, key="k1", token="tok", endpoint="/fix",
        ) is None

    def test_token_scoping(self, session):
        record_idempotency_key(
            session, key="k1", token="alice-token",
            endpoint="/garden", workflow_id="wf-alice",
        )
        session.commit()
        # Same key, different token → miss
        assert lookup_idempotency_key(
            session, key="k1", token="bob-token", endpoint="/garden",
        ) is None


class TestRecord:
    def test_roundtrip(self, session):
        record_idempotency_key(
            session, key="k", token="t", endpoint="/x", workflow_id="wf-1",
        )
        session.commit()
        assert lookup_idempotency_key(session, key="k", token="t", endpoint="/x") == "wf-1"

    def test_idempotent_on_duplicate(self, session):
        record_idempotency_key(session, key="k", token="t", endpoint="/x", workflow_id="wf-1")
        session.commit()
        # Same triple again — should not raise
        record_idempotency_key(session, key="k", token="t", endpoint="/x", workflow_id="wf-2")
        session.commit()
        # Original wins (we don't overwrite)
        assert lookup_idempotency_key(session, key="k", token="t", endpoint="/x") == "wf-1"


@pytest.mark.asyncio
class TestHeaderDep:
    async def test_returns_value(self):
        assert await get_idempotency_key("my-key-123") == "my-key-123"

    async def test_strips_whitespace(self):
        assert await get_idempotency_key("  trimmed  ") == "trimmed"

    async def test_empty_returns_none(self):
        assert await get_idempotency_key("") is None
        assert await get_idempotency_key("   ") is None

    async def test_missing_returns_none(self):
        assert await get_idempotency_key(None) is None

    async def test_too_long_returns_none(self):
        long_key = "x" * 200
        assert await get_idempotency_key(long_key) is None


class TestEndToEnd:
    """POST /api/garden twice with same Idempotency-Key spawns one workflow."""

    def test_garden_endpoint_dedups(self, monkeypatch):
        """End-to-end: same key → same workflow_id, only one Temporal call."""
        from unittest.mock import AsyncMock, MagicMock
        from fastapi.testclient import TestClient
        from app.main import app

        # Mock the Temporal client + DB session at the boundary used by /garden
        start_workflow = AsyncMock()
        fake_client = MagicMock()
        fake_client.start_workflow = start_workflow

        # In-memory DB (StaticPool so the FastAPI route's session sees
        # the same DB as the test's setup).
        engine = _make_inmem_engine()

        def fake_get_session():
            return Session(engine)

        async def fake_get_temporal():
            return fake_client

        monkeypatch.setattr("app.api.routes.garden.get_session", fake_get_session)
        monkeypatch.setattr("app.api.routes.garden.get_temporal_client", fake_get_temporal)
        # Pre-existing bug: BatchGardeningInput doesn't accept `repo_ids` but
        # the route passes it. Out of E5 scope — see FINDINGS.md F-009. Mock
        # the input class to a permissive stand-in for this test.
        monkeypatch.setattr(
            "app.api.routes.garden.BatchGardeningInput",
            lambda **kw: MagicMock(**kw),
        )

        client = TestClient(app)
        headers = {
            "Authorization": "Bearer fake-test-token",
            "Idempotency-Key": "user-key-abc",
        }
        body = {"repo_ids": [1, 2, 3]}

        # First call: should start a workflow
        r1 = client.post("/api/garden", json=body, headers=headers)
        assert r1.status_code == 200
        wf1 = r1.json()["workflow_id"]
        assert wf1.startswith("batch-gardening-")
        assert start_workflow.call_count == 1

        # Second call with the SAME key: should return cached workflow_id,
        # NOT call start_workflow again.
        r2 = client.post("/api/garden", json=body, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["workflow_id"] == wf1
        assert r2.json().get("idempotent") is True
        assert start_workflow.call_count == 1  # still 1, not 2

        # Third call with a DIFFERENT key: starts a new workflow.
        headers2 = {**headers, "Idempotency-Key": "user-key-xyz"}
        r3 = client.post("/api/garden", json=body, headers=headers2)
        assert r3.status_code == 200
        wf3 = r3.json()["workflow_id"]
        assert wf3 != wf1
        assert start_workflow.call_count == 2
