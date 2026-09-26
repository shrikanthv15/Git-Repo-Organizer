from fastapi import APIRouter, HTTPException
from sqlalchemy import text
import socket
from app.core.config import settings
from app.db.session import get_session

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "GitHub Gardener"}


@router.get("/ready")
async def readiness_check():
    """Readiness probe: checks DB and Temporal connectivity. 503 when not ready."""
    try:
        with get_session() as session:
            session.exec(text("SELECT 1")).one()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")
    host, _, port_str = settings.TEMPORAL_ADDRESS.partition(":")
    try:
        s = socket.create_connection((host, int(port_str)), timeout=2)
        s.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Temporal not ready: {e}")
    return {"status": "ready"}
