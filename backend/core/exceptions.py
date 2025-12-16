"""
Custom exception classes and global exception handlers.
"""

from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class ContriVerseException(Exception):
    """Base exception for ContriVerse application."""

    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseException(ContriVerseException):
    """Exception for database-related errors."""

    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotFoundException(ContriVerseException):
    """Exception for resource not found errors."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ValidationException(ContriVerseException):
    """Exception for validation errors."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


async def contriverse_exception_handler(
    request: Request, exc: ContriVerseException
) -> JSONResponse:
    """Handle custom ContriVerse exceptions."""
    logger.error(
        "contriverse_exception",
        exception=exc.__class__.__name__,
        message=exc.message,
        status_code=exc.status_code,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "type": exc.__class__.__name__},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions."""
    logger.exception(
        "unhandled_exception",
        exception=exc.__class__.__name__,
        message=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
