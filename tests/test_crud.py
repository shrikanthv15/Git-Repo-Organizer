"""E2 — coverage for app/db/crud.py.

11 CRUD functions × happy + miss paths. Uses the same StaticPool
in-memory SQLite pattern as test_idempotency.py so all sessions see
the same DB.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.crud import (
    clear_pending_fix_for_repo,
    get_draft_proposal,
    get_latest_analysis_for_repos,
    get_repos_with_pending_pr,
    save_draft_proposal,
    set_repo_status,
    update_structure_map,
    upsert_analysis_result,
    upsert_repository,
    upsert_user,
)
from app.db.models import AnalysisResult, Repository, User


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def user(session):
    u = upsert_user(session, github_id=42, username="alice")
    session.commit()
    return u


@pytest.fixture
def repo(session, user):
    r = upsert_repository(
        session,
        github_repo_id=12345,
        owner_id=user.id,
        name="proj",
        full_name="alice/proj",
        html_url="https://github.com/alice/proj",
    )
    session.commit()
    return r


# ---------- upsert_user ----------------------------------------------------

class TestUpsertUser:
    def test_insert_new(self, session):
        u = upsert_user(session, github_id=1, username="bob")
        assert u.github_id == 1
        assert u.username == "bob"
        assert u.id is not None

    def test_update_existing_username(self, session):
        u1 = upsert_user(session, github_id=1, username="bob")
        session.commit()
        u2 = upsert_user(session, github_id=1, username="bob-renamed")
        session.commit()
        # Same row, updated username
        assert u2.id == u1.id
        assert u2.username == "bob-renamed"


# ---------- upsert_repository ----------------------------------------------

class TestUpsertRepository:
    def test_insert_new(self, session, user):
        r = upsert_repository(
            session, github_repo_id=999, owner_id=user.id,
            name="r", full_name="alice/r", html_url="https://x/r",
        )
        assert r.github_repo_id == 999
        assert r.name == "r"

    def test_update_existing(self, session, user, repo):
        # Re-upsert with same github_repo_id, new name → updates
        r = upsert_repository(
            session, github_repo_id=repo.github_repo_id, owner_id=user.id,
            name="proj-renamed", full_name="alice/proj-renamed",
            html_url="https://github.com/alice/proj-renamed",
        )
        session.commit()
        assert r.id == repo.id
        assert r.name == "proj-renamed"


# ---------- upsert_analysis_result -----------------------------------------

class TestUpsertAnalysisResult:
    def test_insert_new(self, session, repo):
        ar = upsert_analysis_result(
            session, repo_id=repo.id, health_score=85,
            issues=["No CHANGELOG"], pending_fix_url=None,
        )
        assert ar.health_score == 85
        assert ar.issues == ["No CHANGELOG"]
        assert ar.pending_fix_url is None
        assert ar.last_gardener_run_at is None

    def test_update_existing_keeps_id(self, session, repo):
        ar1 = upsert_analysis_result(
            session, repo_id=repo.id, health_score=50,
            issues=["No README"], pending_fix_url=None,
        )
        session.commit()
        ar2 = upsert_analysis_result(
            session, repo_id=repo.id, health_score=80,
            issues=[], pending_fix_url="https://github.com/alice/proj/pull/1",
        )
        session.commit()
        assert ar2.id == ar1.id  # row updated, not appended
        assert ar2.health_score == 80
        assert ar2.issues == []
        assert ar2.pending_fix_url.endswith("/pull/1")

    def test_update_preserves_last_gardener_run_at_when_none(self, session, repo):
        # Initial insert sets last_gardener_run_at
        t = datetime.now(timezone.utc) - timedelta(days=1)
        upsert_analysis_result(
            session, repo_id=repo.id, health_score=70, issues=[],
            pending_fix_url=None, last_gardener_run_at=t,
        )
        session.commit()
        # Update WITHOUT passing last_gardener_run_at → field unchanged
        ar2 = upsert_analysis_result(
            session, repo_id=repo.id, health_score=72, issues=[],
            pending_fix_url=None,
        )
        session.commit()
        # The "is not None" guard in crud.py means the existing value stays
        assert ar2.last_gardener_run_at is not None


# ---------- update_structure_map -------------------------------------------

class TestUpdateStructureMap:
    def test_existing_repo(self, session, repo):
        out = update_structure_map(
            session, github_repo_id=repo.github_repo_id,
            structure_map={"files": ["a.py", "b.py"]},
        )
        assert out is not None
        assert out.structure_map == {"files": ["a.py", "b.py"]}

    def test_missing_repo_returns_none(self, session):
        assert update_structure_map(session, github_repo_id=9999, structure_map={}) is None


# ---------- save_draft_proposal / get_draft_proposal -----------------------

class TestDraftProposal:
    def test_save_and_get_roundtrip(self, session, repo):
        upsert_analysis_result(
            session, repo_id=repo.id, health_score=80, issues=[],
            pending_fix_url=None,
        )
        session.commit()

        draft = {"README.md": "# New README"}
        assert save_draft_proposal(
            session, github_repo_id=repo.github_repo_id, draft_proposal=draft,
        )
        session.commit()
        out = get_draft_proposal(session, github_repo_id=repo.github_repo_id)
        assert out == draft

    def test_save_returns_false_when_no_repo(self, session):
        assert save_draft_proposal(
            session, github_repo_id=9999, draft_proposal={"a": "b"},
        ) is False

    def test_save_returns_false_when_no_analysis(self, session, repo):
        # repo exists but no AnalysisResult yet
        assert save_draft_proposal(
            session, github_repo_id=repo.github_repo_id, draft_proposal={"a": "b"},
        ) is False

    def test_get_returns_none_when_no_repo(self, session):
        assert get_draft_proposal(session, github_repo_id=9999) is None

    def test_get_returns_none_when_no_analysis(self, session, repo):
        assert get_draft_proposal(session, github_repo_id=repo.github_repo_id) is None

    def test_clear_draft_with_none(self, session, repo):
        upsert_analysis_result(
            session, repo_id=repo.id, health_score=80, issues=[], pending_fix_url=None,
        )
        save_draft_proposal(
            session, github_repo_id=repo.github_repo_id, draft_proposal={"a": "b"},
        )
        session.commit()
        save_draft_proposal(
            session, github_repo_id=repo.github_repo_id, draft_proposal=None,
        )
        session.commit()
        assert get_draft_proposal(session, github_repo_id=repo.github_repo_id) is None


# ---------- set_repo_status -------------------------------------------------

class TestSetRepoStatus:
    def test_existing(self, session, repo):
        upsert_analysis_result(
            session, repo_id=repo.id, health_score=80, issues=[], pending_fix_url=None,
        )
        session.commit()
        assert set_repo_status(
            session, github_repo_id=repo.github_repo_id, status="drafting_docs",
        )
        session.commit()
        ar = session.exec(
            __import__("sqlmodel").select(AnalysisResult).where(
                AnalysisResult.repo_id == repo.id
            )
        ).first()
        assert ar.status == "drafting_docs"

    def test_missing_repo(self, session):
        assert set_repo_status(
            session, github_repo_id=9999, status="drafting_docs",
        ) is False

    def test_missing_analysis(self, session, repo):
        assert set_repo_status(
            session, github_repo_id=repo.github_repo_id, status="idle",
        ) is False


# ---------- get_repos_with_pending_pr / clear_pending_fix_for_repo ---------

class TestPendingPR:
    def test_get_returns_only_repos_with_pr(self, session, user):
        # Repo A: has pending PR
        ra = upsert_repository(
            session, github_repo_id=1, owner_id=user.id,
            name="a", full_name="alice/a", html_url="https://x/a",
        )
        upsert_analysis_result(
            session, repo_id=ra.id, health_score=80, issues=[],
            pending_fix_url="https://github.com/alice/a/pull/1",
        )
        # Repo B: no pending PR
        rb = upsert_repository(
            session, github_repo_id=2, owner_id=user.id,
            name="b", full_name="alice/b", html_url="https://x/b",
        )
        upsert_analysis_result(
            session, repo_id=rb.id, health_score=80, issues=[],
            pending_fix_url=None,
        )
        # Repo C: empty string treated as no PR (per query filter)
        rc = upsert_repository(
            session, github_repo_id=3, owner_id=user.id,
            name="c", full_name="alice/c", html_url="https://x/c",
        )
        upsert_analysis_result(
            session, repo_id=rc.id, health_score=80, issues=[],
            pending_fix_url="",
        )
        session.commit()

        out = get_repos_with_pending_pr(session)
        names = {full_name for full_name, _ in out}
        assert names == {"alice/a"}

    def test_clear_existing(self, session, user):
        ra = upsert_repository(
            session, github_repo_id=1, owner_id=user.id,
            name="a", full_name="alice/a", html_url="https://x/a",
        )
        upsert_analysis_result(
            session, repo_id=ra.id, health_score=80, issues=[],
            pending_fix_url="https://github.com/alice/a/pull/1",
        )
        session.commit()
        assert clear_pending_fix_for_repo(session, repo_full_name="alice/a") is True
        session.commit()
        out = get_repos_with_pending_pr(session)
        assert out == []

    def test_clear_missing_repo(self, session):
        assert clear_pending_fix_for_repo(session, repo_full_name="ghost/x") is False

    def test_clear_no_pending(self, session, user):
        ra = upsert_repository(
            session, github_repo_id=1, owner_id=user.id,
            name="a", full_name="alice/a", html_url="https://x/a",
        )
        upsert_analysis_result(
            session, repo_id=ra.id, health_score=80, issues=[],
            pending_fix_url=None,
        )
        session.commit()
        # No row had a pending_fix_url to clear → returns False per len > 0 check
        assert clear_pending_fix_for_repo(session, repo_full_name="alice/a") is False


# ---------- get_latest_analysis_for_repos ----------------------------------

class TestGetLatestAnalysis:
    def test_empty_input(self, session):
        assert get_latest_analysis_for_repos(session, []) == {}

    def test_single_repo(self, session, repo):
        ar = upsert_analysis_result(
            session, repo_id=repo.id, health_score=80, issues=[],
            pending_fix_url=None,
        )
        session.commit()
        out = get_latest_analysis_for_repos(session, [repo.github_repo_id])
        assert repo.github_repo_id in out
        assert out[repo.github_repo_id].id == ar.id

    def test_dedup_to_latest(self, session, repo):
        # Two AnalysisResult rows for the same repo — return the most-recent one
        ar_old = AnalysisResult(
            repo_id=repo.id, health_score=50, issues=[], pending_fix_url=None,
            last_analyzed_at=datetime.now(timezone.utc) - timedelta(days=7),
        )
        ar_new = AnalysisResult(
            repo_id=repo.id, health_score=80, issues=[], pending_fix_url=None,
            last_analyzed_at=datetime.now(timezone.utc),
        )
        session.add(ar_old)
        session.add(ar_new)
        session.commit()
        out = get_latest_analysis_for_repos(session, [repo.github_repo_id])
        # SQLite may or may not preserve tz; just compare on health_score
        assert out[repo.github_repo_id].health_score == 80

    def test_missing_repo_ids_filtered_out(self, session, repo):
        upsert_analysis_result(
            session, repo_id=repo.id, health_score=80, issues=[],
            pending_fix_url=None,
        )
        session.commit()
        out = get_latest_analysis_for_repos(
            session, [repo.github_repo_id, 99999, 88888]
        )
        # Only the existing repo shows up
        assert set(out.keys()) == {repo.github_repo_id}
