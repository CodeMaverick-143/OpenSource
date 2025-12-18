"""
Permission decorators and utilities for RBAC.
"""

from functools import wraps
from typing import Callable

import structlog
from fastapi import HTTPException, status
from prisma.models import User

from prisma import Prisma

logger = structlog.get_logger(__name__)


class PermissionError(HTTPException):
    """Permission denied error."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def check_project_owner(db: Prisma, project_slug: str, user: User) -> bool:
    """
    Check if user is project owner.

    Args:
        db: Prisma client
        project_slug: Project slug
        user: Current user

    Returns:
        True if user is owner
    """
    project = await db.project.find_unique(where={"slug": project_slug})

    if not project:
        return False

    return project.ownerId == user.id


async def check_project_maintainer(db: Prisma, project_slug: str, user: User) -> bool:
    """
    Check if user is project maintainer (owner or maintainer).

    Args:
        db: Prisma client
        project_slug: Project slug
        user: Current user

    Returns:
        True if user is maintainer or owner
    """
    project = await db.project.find_unique(
        where={"slug": project_slug}, include={"maintainers": True}
    )

    if not project:
        return False

    # Check if owner
    if project.ownerId == user.id:
        return True

    # Check if maintainer
    for maintainer in project.maintainers:
        if maintainer.userId == user.id:
            return True

    return False


async def check_project_member(db: Prisma, project_slug: str, user: User) -> bool:
    """
    Check if user is project member (owner, maintainer, or contributor).

    Args:
        db: Prisma client
        project_slug: Project slug
        user: Current user

    Returns:
        True if user is member
    """
    # For now, same as maintainer check
    # Can be extended to include contributors
    return await check_project_maintainer(db, project_slug, user)


async def get_user_role(db: Prisma, project_slug: str, user: User) -> str:
    """
    Get user's role in project.

    Args:
        db: Prisma client
        project_slug: Project slug
        user: Current user

    Returns:
        Role: "owner", "maintainer", "contributor", or "none"
    """
    project = await db.project.find_unique(
        where={"slug": project_slug}, include={"maintainers": True}
    )

    if not project:
        return "none"

    # Check if owner
    if project.ownerId == user.id:
        return "owner"

    # Check if maintainer
    for maintainer in project.maintainers:
        if maintainer.userId == user.id:
            return maintainer.role

    return "none"


def require_project_owner(func: Callable) -> Callable:
    """
    Decorator to require project owner permission.

    Usage:
        @require_project_owner
        async def update_project(project_slug: str, current_user: User, db: Prisma):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract parameters
        project_slug = kwargs.get("project_slug") or kwargs.get("slug")
        current_user = kwargs.get("current_user")
        db = kwargs.get("db")

        if not all([project_slug, current_user, db]):
            raise ValueError("Missing required parameters for permission check")

        # Check permission
        is_owner = await check_project_owner(db, project_slug, current_user)

        if not is_owner:
            logger.warning(
                "permission_denied_owner",
                user_id=current_user.id,
                project_slug=project_slug,
            )
            raise PermissionError("Only project owner can perform this action")

        return await func(*args, **kwargs)

    return wrapper


def require_project_maintainer(func: Callable) -> Callable:
    """
    Decorator to require project maintainer permission.

    Usage:
        @require_project_maintainer
        async def add_repository(project_slug: str, current_user: User, db: Prisma):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract parameters
        project_slug = kwargs.get("project_slug") or kwargs.get("slug")
        current_user = kwargs.get("current_user")
        db = kwargs.get("db")

        if not all([project_slug, current_user, db]):
            raise ValueError("Missing required parameters for permission check")

        # Check permission
        is_maintainer = await check_project_maintainer(db, project_slug, current_user)

        if not is_maintainer:
            logger.warning(
                "permission_denied_maintainer",
                user_id=current_user.id,
                project_slug=project_slug,
            )
            raise PermissionError("Only project maintainers can perform this action")

        return await func(*args, **kwargs)

    return wrapper


def require_project_member(func: Callable) -> Callable:
    """
    Decorator to require project member permission.

    Usage:
        @require_project_member
        async def view_project_details(project_slug: str, current_user: User, db: Prisma):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract parameters
        project_slug = kwargs.get("project_slug") or kwargs.get("slug")
        current_user = kwargs.get("current_user")
        db = kwargs.get("db")

        if not all([project_slug, current_user, db]):
            raise ValueError("Missing required parameters for permission check")

        # Check permission
        is_member = await check_project_member(db, project_slug, current_user)

        if not is_member:
            logger.warning(
                "permission_denied_member",
                user_id=current_user.id,
                project_slug=project_slug,
            )
            raise PermissionError("Only project members can perform this action")

        return await func(*args, **kwargs)

    return wrapper
