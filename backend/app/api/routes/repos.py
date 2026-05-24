import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.crud import (
    get_draft_proposal,
    get_latest_analysis_for_repos,
    save_draft_proposal,
    set_repo_status,
)
from app.db.session import get_session
from app.schemas.analysis import RepoHealth
from app.schemas.github import Repo
from app.services import github_service
from app.temporal.activities import create_docs_pull_request_activity
from app.temporal.workflows import (
    AnalysisInput,
    AnalysisWorkflow,
    BatchGardeningInput,
    BatchGardeningWorkflow,
    GreetingWorkflow,
    JanitorInput,
    JanitorWorkflow,
)
from app.api.deps import get_current_token, get_temporal_client
from app.services.idempotency import (
    get_idempotency_key,
    lookup_idempotency_key,
    record_idempotency_key,
)

router = APIRouter()

_FIX_ENDPOINT = "/fix"
_COMMIT_ENDPOINT = "/commit"


@router.post("/test-workflow")
async def test_workflow(token: str = Depends(get_current_token)):
    client = await get_temporal_client()
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Gardener",
        id=f"greeting-{uuid.uuid4()}",
        task_queue="gardener-queue",
    )
    return {"result": result}


@router.get("/repos", response_model=list[Repo])
async def list_repos(token: str = Depends(get_current_token)):
    try:
        repos = await github_service.list_user_repos(token)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch repos from GitHub")

    # Hydrate repos with persisted analysis data
    repo_ids = [r.id for r in repos]
    try:
        with get_session() as session:
            analysis_map = get_latest_analysis_for_repos(session, repo_ids)
    except Exception:
        analysis_map = {}

    enriched: list[Repo] = []
    for r in repos:
        repo_dict = r.model_dump()
        analysis = analysis_map.get(r.id)
        if analysis:
            repo_dict["health"] = RepoHealth(
                repo_name=r.full_name,
                health_score=analysis.health_score,
                issues=analysis.issues,
                last_commit_date=analysis.last_analyzed_at,
                pending_fix_url=analysis.pending_fix_url,
                status=analysis.status,
                last_gardener_run_at=analysis.last_gardener_run_at,
            )
            if analysis.draft_proposal:
                repo_dict["draft_proposal"] = analysis.draft_proposal
        enriched.append(Repo(**repo_dict))

    return enriched


@router.post("/analyze/{repo_id}")
async def analyze_repo(repo_id: int, token: str = Depends(get_current_token)):
    try:
        full_name = await github_service.get_repo_full_name(token, repo_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Repo with id {repo_id} not found")

    client = await get_temporal_client()
    workflow_id = f"analysis-{repo_id}-{uuid.uuid4()}"
    await client.start_workflow(
        AnalysisWorkflow.run,
        AnalysisInput(repo_full_name=full_name, access_token=token),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}


@router.post("/fix/{repo_id}")
async def fix_repo(
    repo_id: int,
    token: str = Depends(get_current_token),
    idem_key: str | None = Depends(get_idempotency_key),
):
    """Trigger Janitor agent to create README PR for a repo.

    E5: pass an ``Idempotency-Key`` header to dedup within 24h —
    repeated calls with the same key + token return the previously-issued
    workflow_id instead of starting a new Janitor run.
    """
    if idem_key:
        with get_session() as session:
            cached = lookup_idempotency_key(
                session, key=idem_key, token=token, endpoint=_FIX_ENDPOINT,
            )
            if cached:
                return {"workflow_id": cached, "idempotent": True}

    try:
        details = await github_service.get_repo_details(token, repo_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Repo with id {repo_id} not found")

    client = await get_temporal_client()
    workflow_id = f"janitor-{repo_id}-{uuid.uuid4()}"
    await client.start_workflow(
        JanitorWorkflow.run,
        JanitorInput(
            repo_full_name=details["full_name"],
            access_token=token,
            description=details["description"],
            github_repo_id=repo_id,
        ),
        id=workflow_id,
        task_queue="gardener-queue",
    )

    if idem_key:
        with get_session() as session:
            record_idempotency_key(
                session, key=idem_key, token=token,
                endpoint=_FIX_ENDPOINT, workflow_id=workflow_id,
            )
            session.commit()

    return {"workflow_id": workflow_id}


@router.post("/sync")
async def sync_pr_status(token: str = Depends(get_current_token)):
    """Check GitHub for merged/closed PRs and update local DB state."""
    from app.temporal.activities import sync_pr_status_activity
    updated_count = await sync_pr_status_activity(token)
    return {"status": "synced", "updated_count": updated_count}


class CommitRequest(BaseModel):
    selected_files: list[str]
    edited_contents: dict[str, str] | None = None  # filename -> edited content


@router.post("/repos/{repo_id}/commit")
async def commit_docs(
    repo_id: int,
    body: CommitRequest,
    token: str = Depends(get_current_token),
    idem_key: str | None = Depends(get_idempotency_key),
):
    """Approve selected draft files and push them to GitHub as a PR.

    E5: pass an ``Idempotency-Key`` header to dedup within 24h. The cached
    value is the previously-returned ``pr_url`` (which serves the same
    side-effect-identifier role as ``workflow_id`` does on other endpoints).
    """
    if idem_key:
        with get_session() as session:
            cached_pr = lookup_idempotency_key(
                session, key=idem_key, token=token, endpoint=_COMMIT_ENDPOINT,
            )
            if cached_pr:
                return {"status": "committed", "pr_url": cached_pr, "idempotent": True}

    # 1. Fetch draft proposal from DB
    with get_session() as session:
        draft = get_draft_proposal(session, github_repo_id=repo_id)
    if not draft:
        raise HTTPException(status_code=404, detail="No draft proposal found for this repo")

    # 2. Filter to only selected files, apply edits if provided
    files = {k: v for k, v in draft.items() if k in body.selected_files}
    if not files:
        raise HTTPException(status_code=400, detail="No valid files selected")
    if body.edited_contents:
        for filename, content in body.edited_contents.items():
            if filename in files:
                files[filename] = content

    # 3. Get repo full_name for the PR
    try:
        details = await github_service.get_repo_details(token, repo_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Repo with id {repo_id} not found")

    # 4. Create the PR via the existing activity function (called directly, not via Temporal)
    files_json = json.dumps(files)
    pr_url = await create_docs_pull_request_activity(
        details["full_name"], files_json, token
    )

    # 5. Clear draft from DB and reset status to idle
    with get_session() as session:
        save_draft_proposal(session, github_repo_id=repo_id, draft_proposal=None)
        set_repo_status(session, github_repo_id=repo_id, status="idle")
        session.commit()

    # 6. Record idempotency key → pr_url so repeat calls return the same PR
    if idem_key:
        with get_session() as session:
            record_idempotency_key(
                session, key=idem_key, token=token,
                endpoint=_COMMIT_ENDPOINT, workflow_id=pr_url,
            )
            session.commit()

    return {"status": "committed", "pr_url": pr_url}
