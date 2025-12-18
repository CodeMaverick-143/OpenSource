"""
User service for CRUD operations and business logic.
Refactored to use Prisma ORM.
"""

from datetime import datetime
from typing import Optional

import structlog
from prisma.models import User

from prisma import Prisma

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: Prisma):
        """Initialize user service with Prisma client."""
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by internal ID (UUID).

        Args:
            user_id: Internal user ID (UUID string)

        Returns:
            User if found, None otherwise
        """
        return await self.db.user.find_unique(where={"id": user_id})

    async def get_by_github_id(self, github_id: int) -> Optional[User]:
        """
        Get user by GitHub ID.

        Args:
            github_id: GitHub user ID

        Returns:
            User if found, None otherwise
        """
        return await self.db.user.find_unique(where={"githubId": github_id})

    async def create_from_github(self, github_data: dict) -> User:
        """
        Create a new user from GitHub profile data.

        Args:
            github_data: GitHub user profile data

        Returns:
            Created user
        """
        user = await self.db.user.create(
            data={
                "githubId": github_data["id"],
                "githubUsername": github_data["login"],
                "avatarUrl": github_data.get("avatar_url"),
                "profileUrl": github_data.get("html_url"),
                "email": github_data.get("email"),
                "lastLoginAt": datetime.utcnow(),
            }
        )

        logger.info(
            "user_created_from_github",
            user_id=user.id,
            github_id=user.githubId,
            username=user.githubUsername,
        )

        return user

    async def update_from_github(self, user: User, github_data: dict) -> User:
        """
        Update user profile from GitHub data.
        Detects and logs username changes.

        Args:
            user: Existing user
            github_data: GitHub user profile data

        Returns:
            Updated user
        """
        old_username = user.githubUsername
        new_username = github_data["login"]

        # Detect username change
        if old_username != new_username:
            logger.info(
                "github_username_changed",
                user_id=user.id,
                github_id=user.githubId,
                old_username=old_username,
                new_username=new_username,
            )

        # Update mutable fields
        updated_user = await self.db.user.update(
            where={"id": user.id},
            data={
                "githubUsername": new_username,
                "avatarUrl": github_data.get("avatar_url"),
                "profileUrl": github_data.get("html_url"),
                "email": github_data.get("email"),
                "lastLoginAt": datetime.utcnow(),
            },
        )

        logger.debug("user_updated_from_github", user_id=user.id, github_id=user.githubId)

        return updated_user

    async def get_or_create_from_github(self, github_data: dict) -> tuple[User, bool]:
        """
        Get existing user or create new one from GitHub data.

        Args:
            github_data: GitHub user profile data

        Returns:
            Tuple of (user, created) where created is True if user was created
        """
        github_id = github_data["id"]

        # Try to find existing user
        user = await self.get_by_github_id(github_id)

        if user:
            # Update existing user
            user = await self.update_from_github(user, github_data)
            return user, False
        else:
            # Create new user
            user = await self.create_from_github(github_data)
            return user, True

    async def soft_delete(self, user: User) -> User:
        """
        Soft delete a user (mark as deleted).

        Args:
            user: User to delete

        Returns:
            Updated user
        """
        updated_user = await self.db.user.update(where={"id": user.id}, data={"isDeleted": True})

        logger.info("user_soft_deleted", user_id=user.id, github_id=user.githubId)

        return updated_user

    async def ban(self, user: User) -> User:
        """
        Ban a user.

        Args:
            user: User to ban

        Returns:
            Updated user
        """
        updated_user = await self.db.user.update(where={"id": user.id}, data={"isBanned": True})

        logger.warning("user_banned", user_id=user.id, github_id=user.githubId)

        return updated_user

    async def unban(self, user: User) -> User:
        """
        Unban a user.

        Args:
            user: User to unban

        Returns:
            Updated user
        """
        updated_user = await self.db.user.update(where={"id": user.id}, data={"isBanned": False})

        logger.info("user_unbanned", user_id=user.id, github_id=user.githubId)

        return updated_user
