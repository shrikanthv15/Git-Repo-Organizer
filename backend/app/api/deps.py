# Shared dependencies for API routes
from fastapi import HTTPException, Request
from temporalio.client import Client

from app.core.config import settings


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
