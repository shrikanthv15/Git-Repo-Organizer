from fastapi import APIRouter
from pydantic import BaseModel
import structlog

router = APIRouter()


class FrontendLogRequest(BaseModel):
    level: str
    message: str
    route: str | None = None
    timestamp: str | None = None
    digest: str | None = None


@router.post("/log")
async def log_frontend_error(body: FrontendLogRequest):
    """Receive structured logs from frontend error boundaries."""
    logger = structlog.get_logger()
    logger.info("frontend_log", level=body.level, message=body.message, route=body.route, digest=body.digest)
    return {"status": "logged"}
