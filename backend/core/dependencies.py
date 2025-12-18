"""
FastAPI dependencies for authentication.
"""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prisma.models import User

from backend.core.security import get_user_id_from_token
from backend.db.prisma_client import get_db
from backend.services.user_service import UserService
from prisma import Prisma

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Prisma = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Prisma client

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Decode token and extract user ID
    user_id = get_user_id_from_token(token)
    if not user_id:
        logger.warning("invalid_token_in_request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        logger.warning("user_not_found_for_token", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Bind user context to logs
    structlog.contextvars.bind_contextvars(user_id=user.id, github_id=user.githubId)

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (not banned or deleted).

    Args:
        current_user: Current authenticated user

    Returns:
        Active user

    Raises:
        HTTPException: If user is banned or deleted
    """
    if current_user.isBanned:
        logger.warning("banned_user_access_attempt", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned. Please contact support.",
        )

    if current_user.isDeleted:
        logger.warning("deleted_user_access_attempt", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deleted.",
        )

    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Prisma = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Prisma client

    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        user_id = get_user_id_from_token(token)

        if not user_id:
            return None

        user_service = UserService(db)
        user = await user_service.get_by_id(user_id)

        if user and not user.isBanned and not user.isDeleted:
            structlog.contextvars.bind_contextvars(user_id=user.id, github_id=user.githubId)
            return user

        return None

    except Exception:
        return None
