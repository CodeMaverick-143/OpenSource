"""
Health check endpoints for monitoring application status.
"""

import structlog
from fastapi import APIRouter, status

from backend.core.config import settings

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
async def database_health_check() -> dict:
    """Check database connectivity."""
    try:
        from backend.db.prisma_client import health_check

        is_healthy = await health_check()

        if is_healthy:
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "unhealthy", "database": "disconnected"}

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
