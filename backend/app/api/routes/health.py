from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import socket
from ..core.config import settings
from ..core import get_db

router = APIRouter()

# Simple health check
def get_http_bearer():
    return HTTPBearer(auto_error=False)

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "GitHub Gardener"}

@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db), token: str = Depends(get_http_bearer())):
    """Readiness probe checks DB and Temporal connectivity."""
    # Check DB connectivity
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")
    # Check Temporal connectivity (socket)
    host, port_str = settings.TEMPORAL_ADDRESS.split(":")
    port = int(port_str)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((host, port))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Temporal not ready: {e}")
    finally:
        s.close()
    return {"status": "ready"}
