"""
User service for CRUD operations and business logic.
"""

from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession):
        """Initialize user service."""
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.

        Args:
            user_id: Internal user ID

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_github_id(self, github_id: int) -> Optional[User]:
        """
        Get user by GitHub ID.

        Args:
            github_id: GitHub user ID

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def create_from_github(self, github_data: dict) -> User:
        """
        Create a new user from GitHub profile data.

        Args:
            github_data: GitHub user profile data

        Returns:
            Created user
        """
        user = User(
            github_id=github_data["id"],
            github_username=github_data["login"],
            avatar_url=github_data.get("avatar_url"),
            profile_url=github_data.get("html_url"),
            email=github_data.get("email"),
            last_login_at=datetime.utcnow(),
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        logger.info(
            "user_created_from_github",
            user_id=user.id,
            github_id=user.github_id,
            username=user.github_username,
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
        old_username = user.github_username
        new_username = github_data["login"]

        # Detect username change
        if old_username != new_username:
            logger.info(
                "github_username_changed",
                user_id=user.id,
                github_id=user.github_id,
                old_username=old_username,
                new_username=new_username,
            )

        # Update mutable fields
        user.github_username = new_username
        user.avatar_url = github_data.get("avatar_url")
        user.profile_url = github_data.get("html_url")
        user.email = github_data.get("email")
        user.last_login_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(user)

        logger.debug("user_updated_from_github", user_id=user.id, github_id=user.github_id)

        return user

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
        user.is_deleted = True
        await self.db.flush()
        await self.db.refresh(user)

        logger.info("user_soft_deleted", user_id=user.id, github_id=user.github_id)

        return user

    async def ban(self, user: User) -> User:
        """
        Ban a user.

        Args:
            user: User to ban

        Returns:
            Updated user
        """
        user.is_banned = True
        await self.db.flush()
        await self.db.refresh(user)

        logger.warning("user_banned", user_id=user.id, github_id=user.github_id)

        return user

    async def unban(self, user: User) -> User:
        """
        Unban a user.

        Args:
            user: User to unban

        Returns:
            Updated user
        """
        user.is_banned = False
        await self.db.flush()
        await self.db.refresh(user)

        logger.info("user_unbanned", user_id=user.id, github_id=user.github_id)

        return user
