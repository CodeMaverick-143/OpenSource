"""
Authentication service for OAuth flow and session management.
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.oauth import github_oauth_client
from backend.core.security import create_access_token, create_refresh_token, hash_token
from backend.models.refresh_token import RefreshToken
from backend.models.user import User
from backend.services.user_service import UserService

logger = structlog.get_logger(__name__)


class AuthService:
    """Service for authentication and session management."""

    def __init__(self, db: AsyncSession):
        """Initialize auth service."""
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
            logger.info("new_user_authenticated", user_id=user.id, github_id=user.github_id)
        else:
            logger.info("existing_user_authenticated", user_id=user.id, github_id=user.github_id)

        # Generate tokens
        access_token = create_access_token(user.id, user.github_id)
        refresh_token = await self.create_refresh_token(user.id)

        return access_token, refresh_token, user

    async def create_refresh_token(self, user_id: int) -> str:
        """
        Create and store a refresh token.

        Args:
            user_id: User ID

        Returns:
            Refresh token
        """
        # Generate token
        token = create_refresh_token()
        token_hash = hash_token(token)

        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Store in database
        refresh_token_record = RefreshToken(
            token=token_hash, user_id=user_id, expires_at=expires_at
        )

        self.db.add(refresh_token_record)
        await self.db.flush()

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
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token_hash)
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            logger.warning("refresh_token_not_found")
            raise ValueError("Invalid refresh token")

        # Check expiry
        if token_record.is_expired:
            logger.warning("refresh_token_expired", user_id=token_record.user_id)
            await self.db.delete(token_record)
            await self.db.flush()
            raise ValueError("Refresh token expired")

        # Get user
        user = await self.user_service.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            logger.warning("refresh_token_user_inactive", user_id=token_record.user_id)
            raise ValueError("User is not active")

        # Rotate tokens: delete old, create new
        await self.db.delete(token_record)
        await self.db.flush()

        new_access_token = create_access_token(user.id, user.github_id)
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
        result = await self.db.execute(
            delete(RefreshToken).where(RefreshToken.token == token_hash)
        )

        if result.rowcount > 0:
            logger.info("user_logged_out")
        else:
            logger.debug("logout_token_not_found")

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired refresh tokens.

        Returns:
            Number of tokens deleted
        """
        result = await self.db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )

        count = result.rowcount
        if count > 0:
            logger.info("expired_tokens_cleaned", count=count)

        return count
