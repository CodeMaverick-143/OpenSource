"""API v1 router."""

from fastapi import APIRouter

from backend.api.v1 import (
    auth,
    badges,
    dashboard,
    health,
    maintainer,
    projects,
    repositories,
    reviews,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(
dashboard.router, tags=["dashboard"]
)  # Dashboard already has /dashboard prefix
api_router.include_router(maintainer.router, tags=["maintainer"])
api_router.include_router(badges.router, tags=["badges"])
