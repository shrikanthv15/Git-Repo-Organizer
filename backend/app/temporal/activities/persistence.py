import asyncio
import json

from temporalio import activity

from app.db.crud import (
    save_draft_proposal,
    set_repo_status,
)
from app.db.session import get_session


# ---------------------------------------------------------------------------
# Phase 13: Human-in-the-Loop — save drafts to DB
# ---------------------------------------------------------------------------

@activity.defn
async def save_draft_proposal_activity(
    github_repo_id: int,
    files_json: str,
) -> bool:
    """Persist generated doc files as a draft_proposal in the DB."""
    files: dict = json.loads(files_json)

    def _save() -> bool:
        with get_session() as session:
            ok = save_draft_proposal(
                session,
                github_repo_id=github_repo_id,
                draft_proposal=files,
            )
            session.commit()
            return ok

    return await asyncio.to_thread(_save)


# ---------------------------------------------------------------------------
# Phase 18: Persistent status updates
# ---------------------------------------------------------------------------

@activity.defn
async def set_repo_status_activity(github_repo_id: int, status: str) -> bool:
    """Set the status field on a repo's analysis result."""
    def _set() -> bool:
        with get_session() as session:
            ok = set_repo_status(session, github_repo_id=github_repo_id, status=status)
            session.commit()
            return ok
    return await asyncio.to_thread(_set)
