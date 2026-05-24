from fastapi import APIRouter

from app.api.routes import health, auth, repos, garden, portfolio, logs

# Create main router and include sub-routers
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(repos.router, tags=["repos"])
api_router.include_router(garden.router, tags=["garden"])
api_router.include_router(portfolio.router, tags=["portfolio"])
api_router.include_router(logs.router, prefix="", tags=["logs"])

__all__ = ["api_router"]
