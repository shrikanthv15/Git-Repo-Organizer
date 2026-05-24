import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services import github_service
from app.services.idempotency import (
    get_idempotency_key,
    lookup_idempotency_key,
    record_idempotency_key,
)
from app.db.session import get_session
from app.temporal.workflows import PortfolioInput, PortfolioWorkflow
from app.temporal.activities import create_or_update_profile_repo_activity
from app.api.deps import get_current_token, get_temporal_client

router = APIRouter()

_ENDPOINT = "/portfolio/generate"


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
    idem_key: str | None = Depends(get_idempotency_key),
):
    """Trigger the Portfolio Studio workflow with user-selected repos.

    E5: pass an ``Idempotency-Key`` header to dedup within 24h.
    """
    if not body.repo_ids or len(body.repo_ids) > 6:
        raise HTTPException(status_code=400, detail="Select between 1 and 6 repositories")

    if idem_key:
        with get_session() as session:
            cached = lookup_idempotency_key(
                session, key=idem_key, token=token, endpoint=_ENDPOINT,
            )
            if cached:
                return {"workflow_id": cached, "idempotent": True}

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

    if idem_key:
        with get_session() as session:
            record_idempotency_key(
                session, key=idem_key, token=token,
                endpoint=_ENDPOINT, workflow_id=workflow_id,
            )
            session.commit()

    return {"workflow_id": workflow_id}


@router.get("/portfolio/status/{workflow_id}")
async def portfolio_status(workflow_id: str, token: str = Depends(get_current_token)):
    """Poll the Portfolio workflow status."""
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
