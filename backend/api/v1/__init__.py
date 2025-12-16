"""API v1 router initialization."""

from fastapi import APIRouter

from backend.api.v1 import auth, health

api_router = APIRouter()

# Include health check routes
api_router.include_router(health.router, prefix="", tags=["health"])

# Include authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Future routes will be added here
# api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
