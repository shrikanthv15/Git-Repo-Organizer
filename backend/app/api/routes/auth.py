from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import github_service

router = APIRouter()


class AuthExchangeRequest(BaseModel):
    code: str


@router.post("/auth/exchange")
async def auth_exchange(body: AuthExchangeRequest):
    """Exchange GitHub OAuth code for access token."""
    try:
        access_token = await github_service.exchange_code_for_token(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to exchange code with GitHub")
    return {"access_token": access_token}
