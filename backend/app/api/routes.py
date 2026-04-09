import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from temporalio.client import Client

logger = logging.getLogger(__name__)

MAX_BATCH_LIMIT = 100  # Cap batch analysis to prevent runaway workflows

from app.core.config import settings
from app.db.crud import get_draft_proposal, get_latest_analysis_for_repos, save_draft_proposal, set_repo_status
from app.db.session import get_session
from app.schemas.analysis import RepoHealth
from app.schemas.github import AuthExchangeRequest, Repo
from app.services import github_service
from app.temporal.activities import create_docs_pull_request_activity, create_or_update_profile_repo_activity, sync_pr_status_activity
from app.temporal.workflows import (
    AnalysisInput,
    AnalysisWorkflow,
    BatchGardeningInput,
    BatchGardeningWorkflow,
    GreetingWorkflow,
    JanitorInput,
    JanitorWorkflow,
    PortfolioInput,
    PortfolioWorkflow,
)

router = APIRouter()


async def get_temporal_client() -> Client:
    return await Client.connect(settings.TEMPORAL_ADDRESS)


def get_current_token(request: Request) -> str:
    """Extract and validate the Bearer token from the Authorization header."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")
    return token


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "GitHub Gardener"}


@router.post("/auth/exchange")
async def auth_exchange(body: AuthExchangeRequest):
    try:
        access_token = await github_service.exchange_code_for_token(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to exchange code with GitHub")
    return {"access_token": access_token}


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
        logger.exception("Failed to load analysis data for %d repos", len(repo_ids))
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


@router.post("/garden/start")
async def start_garden(
    token: str = Depends(get_current_token),
    limit: int = Query(default=0, ge=0, le=MAX_BATCH_LIMIT),
):
    client = await get_temporal_client()
    workflow_id = f"garden-{uuid.uuid4()}"
    await client.start_workflow(
        BatchGardeningWorkflow.run,
        BatchGardeningInput(access_token=token, limit=limit),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}


@router.get("/garden/status/{workflow_id}")
async def garden_status(workflow_id: str, token: str = Depends(get_current_token)):
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(BatchGardeningWorkflow.get_status)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found or not queryable")
    return status


@router.post("/fix/{repo_id}")
async def fix_repo(repo_id: int, token: str = Depends(get_current_token)):
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
    return {"workflow_id": workflow_id}


@router.post("/sync")
async def sync_pr_status(token: str = Depends(get_current_token)):
    """Check GitHub for merged/closed PRs and update local DB state."""
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
):
    """Approve selected draft files and push them to GitHub as a PR."""
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

    return {"status": "committed", "pr_url": pr_url}


# ---------------------------------------------------------------------------
# Phase 14 / 19: Portfolio Studio
# ---------------------------------------------------------------------------

class PortfolioGenerateRequest(BaseModel):
    repo_ids: list[int]
    bio: str = ""
    links: dict[str, str] | None = None


class PortfolioPublishRequest(BaseModel):
    readme_content: str


@router.post("/portfolio/generate")
async def generate_portfolio(
    body: PortfolioGenerateRequest,
    token: str = Depends(get_current_token),
):
    """Trigger the Portfolio Studio workflow with user-selected repos."""
    if not body.repo_ids or len(body.repo_ids) > 6:
        raise HTTPException(status_code=400, detail="Select between 1 and 6 repositories")

    username = await github_service.get_username(token)
    links_json = json.dumps(body.links) if body.links else "{}"

    client = await get_temporal_client()
    workflow_id = f"portfolio-{username}-{uuid.uuid4()}"
    await client.start_workflow(
        PortfolioWorkflow.run,
        PortfolioInput(
            access_token=token,
            username=username,
            repo_ids=body.repo_ids,
            bio=body.bio,
            links_json=links_json,
        ),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}


@router.get("/portfolio/status/{workflow_id}")
async def portfolio_status(workflow_id: str, token: str = Depends(get_current_token)):
    """Poll the Portfolio workflow status — now returns draft_readme."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(PortfolioWorkflow.get_status)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_id}' not found or not queryable",
        )
    return status


@router.post("/portfolio/publish")
async def publish_portfolio(
    body: PortfolioPublishRequest,
    token: str = Depends(get_current_token),
):
    """Publish the edited portfolio README to GitHub profile repo."""
    username = await github_service.get_username(token)
    result = await create_or_update_profile_repo_activity(
        username, body.readme_content, token
    )
    return {
        "status": "published",
        "profile_url": result["profile_url"],
        "pr_url": result.get("pr_url"),
    }
