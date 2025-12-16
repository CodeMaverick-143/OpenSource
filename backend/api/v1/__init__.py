"""API v1 router."""

from fastapi import APIRouter

from backend.api.v1 import auth, health, projects, repositories, reviews, webhooks

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])

# Future routes will be added here
# router.include_router(projects.router, prefix="/projects", tags=["projects"])
