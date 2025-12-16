"""
Health check endpoints for monitoring application status.
"""

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.session import get_db

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def database_health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Check database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/health/redis", status_code=status.HTTP_200_OK)
async def redis_health_check() -> dict:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis

        client = redis.from_url(str(settings.REDIS_URL))
        await client.ping()
        await client.close()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}
