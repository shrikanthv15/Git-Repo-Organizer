import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from temporalio.client import Client

from app.schemas.github import AuthExchangeRequest, Repo
from app.services import github_service
from app.temporal.workflows import (
    AnalysisInput,
    AnalysisWorkflow,
    BatchGardeningInput,
    BatchGardeningWorkflow,
    GreetingWorkflow,
    JanitorInput,
    JanitorWorkflow,
)

router = APIRouter()


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
    return {"status": "healthy", "service": "Gardener Backend"}


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
async def test_workflow():
    client = await Client.connect("localhost:7233")
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
        return await github_service.list_user_repos(token)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch repos from GitHub")


@router.post("/analyze/{repo_id}")
async def analyze_repo(repo_id: int, token: str = Depends(get_current_token)):
    try:
        full_name = await github_service.get_repo_full_name(token, repo_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Repo with id {repo_id} not found")

    client = await Client.connect("localhost:7233")
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
    limit: int = 3,
):
    client = await Client.connect("localhost:7233")
    workflow_id = f"garden-{uuid.uuid4()}"
    await client.start_workflow(
        BatchGardeningWorkflow.run,
        BatchGardeningInput(access_token=token, limit=limit),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}


@router.get("/garden/status/{workflow_id}")
async def garden_status(workflow_id: str):
    client = await Client.connect("localhost:7233")
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

    client = await Client.connect("localhost:7233")
    workflow_id = f"janitor-{repo_id}-{uuid.uuid4()}"
    await client.start_workflow(
        JanitorWorkflow.run,
        JanitorInput(
            repo_full_name=details["full_name"],
            access_token=token,
            description=details["description"],
        ),
        id=workflow_id,
        task_queue="gardener-queue",
    )
    return {"workflow_id": workflow_id}
