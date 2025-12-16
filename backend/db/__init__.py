"""Database module initialization - Prisma client."""

from backend.db.prisma_client import (
    disconnect_prisma,
    get_db,
    get_prisma_client,
    health_check,
    initialize_prisma,
)

__all__ = [
    "get_prisma_client",
    "initialize_prisma",
    "disconnect_prisma",
    "get_db",
    "health_check",
]
