"""
FastAPI application entry point.
"""

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1 import api_router
from backend.core.config import settings
from backend.core.exceptions import (
    ContriVerseException,
    contriverse_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from backend.core.logging import configure_logging
from backend.core.middleware import RequestIDMiddleware

# Configure logging
configure_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)

# Register exception handlers
app.add_exception_handler(ContriVerseException, contriverse_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup event."""
    from backend.db.prisma_client import initialize_prisma

    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Initialize Prisma client
    await initialize_prisma()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Application shutdown event."""
    from backend.db.prisma_client import disconnect_prisma

    logger.info("application_shutdown")

    # Disconnect Prisma client
    await disconnect_prisma()


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled",
    }
