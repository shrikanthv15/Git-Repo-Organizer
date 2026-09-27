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
from app.temporal.workflows import BatchGardeningInput, BatchGardeningWorkflow
from app.api.deps import get_current_token, get_temporal_client

router = APIRouter()

_ENDPOINT = "/garden"


class GardenRequest(BaseModel):
    repo_ids: list[int]


@router.post("/garden")
async def garden_repos(
    body: GardenRequest,
    token: str = Depends(get_current_token),
    idem_key: str | None = Depends(get_idempotency_key),
):
    """Analyze and generate docs for multiple repos in batch.

    E5: pass an ``Idempotency-Key`` header to dedup within 24h —
    repeated calls with the same key + same Bearer token return the
    previously-issued workflow_id instead of starting a new batch.
    """
    if idem_key:
        with get_session() as session:
            cached = lookup_idempotency_key(
                session, key=idem_key, token=token, endpoint=_ENDPOINT,
            )
            if cached:
                return {"workflow_id": cached, "idempotent": True}

    repo_ids = body.repo_ids[:50]  # Cap at 50 repos per batch

    client = await get_temporal_client()
    workflow_id = f"batch-gardening-{uuid.uuid4()}"
    await client.start_workflow(
        BatchGardeningWorkflow.run,
        BatchGardeningInput(access_token=token, repo_ids=repo_ids),
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


@router.post("/garden/start")
async def garden_start(limit: int = 0, token: str = Depends(get_current_token)):
    """Start a batch analysis over the user's repos.

    Matches the frontend contract: POST /api/garden/start?limit=N (0 = all).
    Returns immediately with a workflow_id; poll GET /api/garden/status/{workflow_id}.
    """
    effective_limit = min(limit, 50) if limit > 0 else 50  # cap: 50 repos per batch
    client = await get_temporal_client()
    workflow_id = f"batch-gardening-{uuid.uuid4()}"
    await client.start_workflow(
        BatchGardeningWorkflow.run,
        BatchGardeningInput(access_token=token, limit=effective_limit),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}


@router.get("/garden/status/{workflow_id}")
async def garden_status(workflow_id: str, token: str = Depends(get_current_token)):
    """Poll a gardening workflow's status — batch or single-repo analysis."""
    from temporalio.client import WorkflowExecutionStatus

    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        desc = await handle.describe()
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_id}' not found",
        )
    if desc.workflow_type == "BatchGardeningWorkflow":
        try:
            return await handle.query(BatchGardeningWorkflow.get_status)
        except Exception:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{workflow_id}' not queryable",
            )
    # Single-repo AnalysisWorkflow has no query handler — derive status from execution state
    if desc.status == WorkflowExecutionStatus.COMPLETED:
        result = await handle.result()
        return {"total": 1, "completed": 1, "results": [result] if result else []}
    if desc.status in (
        WorkflowExecutionStatus.FAILED,
        WorkflowExecutionStatus.TERMINATED,
        WorkflowExecutionStatus.CANCELED,
    ):
        return {"total": 1, "completed": 1, "results": [], "status": "failed"}
    return {"total": 1, "completed": 0, "results": [], "status": "running"}
