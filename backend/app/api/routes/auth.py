from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import os
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from sqlmodel import select

from app.services import github_service
from app.db import session as db_session
from app.db import models as db_models
from app.db import crud

router = APIRouter()


class AuthExchangeRequest(BaseModel):
    code: str


def _fernet() -> Fernet:
    enc_key = os.getenv("SESSION_ENC_KEY")
    if not enc_key:
        raise HTTPException(status_code=500, detail="SESSION_ENC_KEY not set")
    return Fernet(enc_key)


@router.post("/auth/exchange")
async def auth_exchange(body: AuthExchangeRequest, response: Response):
    """Exchange GitHub OAuth code for access token and set session cookie."""
    try:
        access_token = await github_service.exchange_code_for_token(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to exchange code with GitHub")
    # Get or create user keyed on the REAL GitHub id (keeps the unique constraint sound)
    username = await github_service.get_username(access_token)
    github_id = await github_service.get_user_id(access_token)
    f = _fernet()
    with db_session.get_session() as sess:
        user = crud.upsert_user(sess, github_id=github_id, username=username)
        encrypted = f.encrypt(access_token.encode()).decode()
        user_session = db_models.UserSession(
            user_id=user.id,
            encrypted_github_token=encrypted,
            created_at=datetime.now(timezone.utc),
        )
        sess.add(user_session)
        sess.flush()
        response.set_cookie(
            key="session_id",
            value=str(user_session.id),
            httponly=True,
            secure=False,
            samesite="lax",
        )
    return {"username": username}


@router.post("/auth/signout")
async def auth_signout(request: Request, response: Response):
    """Revoke the current session server-side and clear the session cookie."""
    session_id = request.cookies.get("session_id")
    if session_id:
        with db_session.get_session() as sess:
            user_session = sess.exec(
                select(db_models.UserSession).where(db_models.UserSession.id == session_id)
            ).first()
            if user_session and user_session.revoked_at is None:
                user_session.revoked_at = datetime.now(timezone.utc)
                sess.add(user_session)
    response.delete_cookie(key="session_id", samesite="lax")
    return {"ok": True}
