"""
Authentication service for OAuth flow and session management.
Refactored to use Prisma ORM.
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from prisma.models import RefreshToken, User

from backend.core.config import settings
from backend.core.oauth import github_oauth_client
from backend.core.security import create_access_token, create_refresh_token, hash_token
from backend.services.user_service import UserService
from prisma import Prisma

logger = structlog.get_logger(__name__)


class AuthService:
    """Service for authentication and session management."""

    def __init__(self, db: Prisma):
        """Initialize auth service with Prisma client."""
        self.db = db
        self.user_service = UserService(db)

    async def authenticate_with_github(self, code: str) -> tuple[str, str, User]:
        """
        Authenticate user with GitHub OAuth code.

        Args:
            code: GitHub OAuth authorization code

        Returns:
            Tuple of (access_token, refresh_token, user)
        """
        # Exchange code for GitHub access token
        github_token = await github_oauth_client.exchange_code_for_token(code)

        # Fetch GitHub user profile
        github_data = await github_oauth_client.get_user_profile(github_token)

        # Get or create user
        user, created = await self.user_service.get_or_create_from_github(github_data)

        if created:
            logger.info("new_user_authenticated", user_id=user.id, github_id=user.githubId)
        else:
            logger.info("existing_user_authenticated", user_id=user.id, github_id=user.githubId)

        # Generate tokens
        access_token = create_access_token(user.id, user.githubId)
        refresh_token = await self.create_refresh_token(user.id)

        return access_token, refresh_token, user

    async def create_refresh_token(self, user_id: str) -> str:
        """
        Create and store a refresh token.

        Args:
            user_id: User ID (UUID string)

        Returns:
            Refresh token
        """
        # Generate token
        token = create_refresh_token()
        token_hash = hash_token(token)

        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Store in database
        await self.db.refreshtoken.create(
            data={"token": token_hash, "userId": user_id, "expiresAt": expires_at}
        )

        logger.debug("refresh_token_created", user_id=user_id, expires_at=expires_at.isoformat())

        return token

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Refresh access token using refresh token.
        Implements token rotation for security.

        Args:
            refresh_token: Current refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token)

        Raises:
            ValueError: If refresh token is invalid or expired
        """
        token_hash = hash_token(refresh_token)

        # Find refresh token
        token_record = await self.db.refreshtoken.find_unique(where={"token": token_hash})

        if not token_record:
            logger.warning("refresh_token_not_found")
            raise ValueError("Invalid refresh token")

        # Check expiry
        if token_record.expiresAt < datetime.utcnow():
            logger.warning("refresh_token_expired", user_id=token_record.userId)
            await self.db.refreshtoken.delete(where={"id": token_record.id})
            raise ValueError("Refresh token expired")

        # Get user
        user = await self.user_service.get_by_id(token_record.userId)
        if not user:
            logger.warning("refresh_token_user_not_found", user_id=token_record.userId)
            raise ValueError("User not found")

        # Check if user is active
        is_active = not user.isBanned and not user.isDeleted
        if not is_active:
            logger.warning("refresh_token_user_inactive", user_id=token_record.userId)
            raise ValueError("User is not active")

        # Rotate tokens: delete old, create new
        await self.db.refreshtoken.delete(where={"id": token_record.id})

        new_access_token = create_access_token(user.id, user.githubId)
        new_refresh_token = await self.create_refresh_token(user.id)

        logger.info("tokens_refreshed", user_id=user.id)

        return new_access_token, new_refresh_token

    async def logout(self, refresh_token: str) -> None:
        """
        Logout user by invalidating refresh token.

        Args:
            refresh_token: Refresh token to invalidate
        """
        token_hash = hash_token(refresh_token)

        # Delete refresh token
        try:
            await self.db.refreshtoken.delete(where={"token": token_hash})
            logger.info("user_logged_out")
        except Exception:
            logger.debug("logout_token_not_found")

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired refresh tokens.

        Returns:
            Number of tokens deleted
        """
        result = await self.db.refreshtoken.delete_many(
            where={"expiresAt": {"lt": datetime.utcnow()}}
        )

        count = result
        if count > 0:
            logger.info("expired_tokens_cleaned", count=count)

        return count
