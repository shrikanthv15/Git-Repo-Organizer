import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services import github_service
from app.temporal.workflows import BatchGardeningInput, BatchGardeningWorkflow
from app.api.deps import get_current_token, get_temporal_client

router = APIRouter()


class GardenRequest(BaseModel):
    repo_ids: list[int]


@router.post("/garden")
async def garden_repos(
    body: GardenRequest,
    token: str = Depends(get_current_token),
):
    """Analyze and generate docs for multiple repos in batch."""
    repo_ids = body.repo_ids[:50]  # Cap at 50 repos per batch
    
    client = await get_temporal_client()
    workflow_id = f"batch-gardening-{uuid.uuid4()}"
    await client.start_workflow(
        BatchGardeningWorkflow.run,
        BatchGardeningInput(access_token=token, repo_ids=repo_ids),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}


@router.get("/garden/status/{workflow_id}")
async def garden_status(workflow_id: str, token: str = Depends(get_current_token)):
    """Poll the batch gardening workflow status."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(BatchGardeningWorkflow.get_status)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_id}' not found or not queryable",
        )
    return status
