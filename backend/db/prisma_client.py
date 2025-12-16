"""
Prisma client singleton for database access.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from prisma import Prisma

logger = structlog.get_logger(__name__)

# Global Prisma client instance
_prisma_client: Optional[Prisma] = None


def get_prisma_client() -> Prisma:
    """
    Get the global Prisma client instance.

    Returns:
        Prisma client

    Raises:
        RuntimeError: If client is not initialized
    """
    global _prisma_client

    if _prisma_client is None:
        raise RuntimeError(
            "Prisma client not initialized. "
            "Call initialize_prisma() during application startup."
        )

    return _prisma_client


async def initialize_prisma() -> None:
    """
    Initialize Prisma client and connect to database.
    Should be called during FastAPI startup.
    """
    global _prisma_client

    if _prisma_client is not None:
        logger.warning("prisma_already_initialized")
        return

    logger.info("initializing_prisma_client")

    _prisma_client = Prisma(
        auto_register=True,
        log_queries=False,  # Set to True for debugging
    )

    await _prisma_client.connect()

    logger.info("prisma_client_connected")


async def disconnect_prisma() -> None:
    """
    Disconnect Prisma client.
    Should be called during FastAPI shutdown.
    """
    global _prisma_client

    if _prisma_client is None:
        logger.warning("prisma_not_initialized")
        return

    logger.info("disconnecting_prisma_client")

    await _prisma_client.disconnect()
    _prisma_client = None

    logger.info("prisma_client_disconnected")


@asynccontextmanager
async def get_db() -> AsyncGenerator[Prisma, None]:
    """
    Dependency to get Prisma client for FastAPI routes.

    Usage:
        @router.get("/users")
        async def get_users(db: Prisma = Depends(get_db)):
            users = await db.user.find_many()
            return users

    Yields:
        Prisma client
    """
    client = get_prisma_client()
    try:
        yield client
    except Exception as e:
        logger.error("database_operation_error", error=str(e))
        raise


async def health_check() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if healthy, False otherwise
    """
    try:
        client = get_prisma_client()
        # Simple query to check connection
        await client.query_raw("SELECT 1")
        return True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return False
