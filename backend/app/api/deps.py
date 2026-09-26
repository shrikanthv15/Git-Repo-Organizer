# Shared dependencies for API routes
from fastapi import HTTPException, Request
from temporalio.client import Client

from app.core.config import settings


async def get_temporal_client() -> Client:
    return await Client.connect(settings.TEMPORAL_ADDRESS)


def get_current_token(request: Request) -> str:
    """Extract Bearer token from Authorization header or session cookie."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        if token:
            return token
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    from app.db import session as db_session
    from app.db import models as db_models
    from sqlmodel import select
    import os
    from cryptography.fernet import Fernet
    with db_session.get_session() as sess:
        result = sess.exec(select(db_models.UserSession).where(db_models.UserSession.id == session_id)).first()
        if not result or result.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Invalid or revoked session")
        enc_key = os.getenv("SESSION_ENC_KEY")
        if not enc_key:
            raise HTTPException(status_code=500, detail="SESSION_ENC_KEY not set")
        f = Fernet(enc_key)
        token = f.decrypt(result.encrypted_github_token.encode()).decode()
        return token
