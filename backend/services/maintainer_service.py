"""
Maintainer service for managing project maintainers.
"""

from typing import List

import structlog
from fastapi import HTTPException, status
from prisma import Prisma
from prisma.models import ProjectMaintainer, User

logger = structlog.get_logger(__name__)


class MaintainerService:
    """Service for maintainer management."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def add_maintainer(
        self, project_id: str, user_id: str, role: str = "maintainer"
    ) -> ProjectMaintainer:
        """
        Add maintainer to project.

        Args:
            project_id: Project ID
            user_id: User ID
            role: Role (owner or maintainer)

        Returns:
            Created maintainer record

        Raises:
            HTTPException: If user not found, banned, or already maintainer
        """
        # Check if user exists and is not banned/deleted
        user = await self.db.user.find_unique(where={"id": user_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.isBanned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add banned user as maintainer",
            )

        if user.isDeleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add deleted user as maintainer",
            )

        # Check if already maintainer
        existing = await self.db.projectmaintainer.find_unique(
            where={"projectId_userId": {"projectId": project_id, "userId": user_id}}
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a maintainer",
            )

        # Add maintainer
        maintainer = await self.db.projectmaintainer.create(
            data={"projectId": project_id, "userId": user_id, "role": role}
        )

        logger.info(
            "maintainer_added",
            project_id=project_id,
            user_id=user_id,
            role=role,
        )

        return maintainer

    async def remove_maintainer(
        self, project_id: str, user_id: str, requesting_user: User
    ) -> None:
        """
        Remove maintainer from project.

        Args:
            project_id: Project ID
            user_id: User ID to remove
            requesting_user: User requesting removal

        Raises:
            HTTPException: If trying to remove owner or maintainer not found
        """
        # Get project
        project = await self.db.project.find_unique(where={"id": project_id})
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Prevent removing owner (unless admin override)
        if project.ownerId == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove project owner. Transfer ownership first.",
            )

        # Get maintainer record
        maintainer = await self.db.projectmaintainer.find_unique(
            where={"projectId_userId": {"projectId": project_id, "userId": user_id}}
        )

        if not maintainer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Maintainer not found",
            )

        # Remove maintainer
        await self.db.projectmaintainer.delete(where={"id": maintainer.id})

        logger.info(
            "maintainer_removed",
            project_id=project_id,
            user_id=user_id,
            removed_by=requesting_user.id,
        )

    async def list_maintainers(self, project_id: str) -> List[ProjectMaintainer]:
        """
        List project maintainers.

        Args:
            project_id: Project ID

        Returns:
            List of maintainers
        """
        maintainers = await self.db.projectmaintainer.find_many(
            where={"projectId": project_id}, include={"user": True}, order={"createdAt": "asc"}
        )

        return maintainers

    async def is_maintainer(self, project_id: str, user_id: str) -> bool:
        """
        Check if user is maintainer.

        Args:
            project_id: Project ID
            user_id: User ID

        Returns:
            True if user is maintainer
        """
        maintainer = await self.db.projectmaintainer.find_unique(
            where={"projectId_userId": {"projectId": project_id, "userId": user_id}}
        )

        return maintainer is not None

    async def get_user_role(self, project_id: str, user_id: str) -> str:
        """
        Get user's role in project.

        Args:
            project_id: Project ID
            user_id: User ID

        Returns:
            Role: "owner", "maintainer", or "none"
        """
        # Check if owner
        project = await self.db.project.find_unique(where={"id": project_id})
        if project and project.ownerId == user_id:
            return "owner"

        # Check if maintainer
        maintainer = await self.db.projectmaintainer.find_unique(
            where={"projectId_userId": {"projectId": project_id, "userId": user_id}}
        )

        if maintainer:
            return maintainer.role

        return "none"
