import logging
import os
import structlog

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.middleware.logging import LoggingMiddleware

# Configure structlog
log_format = os.getenv("LOG_FORMAT", "human" if os.getenv("ENV") == "dev" else "json")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

if log_format == "json":
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
else:
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer()
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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
