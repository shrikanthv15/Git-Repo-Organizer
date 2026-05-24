import logging
import os
import structlog

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings
from app.middleware.logging import LoggingMiddleware
from app.services.llm_service import LLMCostExceededError

# Configure structlog
log_format = os.getenv("LOG_FORMAT", "human" if os.getenv("ENV") == "dev" else "json")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

if log_format == "json":
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
else:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

# Root logger
logging.basicConfig(level=getattr(logging, log_level))
logger = structlog.get_logger()
logger.info("app_startup", format=log_format, level=log_level)

app = FastAPI(title=settings.PROJECT_NAME)

# CORS — restrict to FRONTEND_URL in production; fall back to permissive in dev
_allowed_origins: list[str] = []
if settings.FRONTEND_URL:
    _allowed_origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]
else:
    _allowed_origins = ["*"]

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


# E5 — surface LLM cost-cap violations as 400 (not 500) so callers
# get a clear "you exceeded the budget" message rather than a generic
# server error.
@app.exception_handler(LLMCostExceededError)
async def llm_cost_exceeded_handler(request: Request, exc: LLMCostExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "error": "llm_cost_exceeded",
            "estimated_cost_usd": exc.estimated_cost,
            "max_cost_usd": exc.max_cost,
            "prompt_tokens": exc.prompt_tokens,
        },
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
