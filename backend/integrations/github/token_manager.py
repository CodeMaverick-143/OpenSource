"""
GitHub token management with secure storage and validation.
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from prisma.models import GitHubToken, User

from backend.integrations.github.rest_client import GitHubRESTClient
from prisma import Prisma

logger = structlog.get_logger(__name__)


class TokenManager:
    """Manage GitHub OAuth tokens with encryption and validation."""

    def __init__(self, db: Prisma):
        """Initialize token manager."""
        self.db = db

    async def store_token(
        self,
        user_id: str,
        access_token: str,
        token_type: str = "oauth",
        scope: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> GitHubToken:
        """
        Store GitHub token securely.

        Args:
            user_id: User ID
            access_token: GitHub access token (will be encrypted)
            token_type: "oauth" or "app"
            scope: OAuth scopes
            expires_at: Token expiration (for GitHub Apps)

        Returns:
            Created token record
        """
        # TODO: Encrypt token before storing
        # For now, storing as-is (should use Fernet or similar)
        encrypted_token = access_token

        # Upsert token
        token = await self.db.githubtoken.upsert(
            where={"userId_tokenType": {"userId": user_id, "tokenType": token_type}},
            data={
                "create": {
                    "userId": user_id,
                    "accessToken": encrypted_token,
                    "tokenType": token_type,
                    "scope": scope,
                    "expiresAt": expires_at,
                    "lastUsedAt": datetime.utcnow(),
                    "lastVerified": datetime.utcnow(),
                },
                "update": {
                    "accessToken": encrypted_token,
                    "scope": scope,
                    "expiresAt": expires_at,
                    "isRevoked": False,
                    "lastUsedAt": datetime.utcnow(),
                    "lastVerified": datetime.utcnow(),
                },
            },
        )

        logger.info("github_token_stored", user_id=user_id, token_type=token_type)

        return token

    async def get_token(self, user_id: str, token_type: str = "oauth") -> Optional[GitHubToken]:
        """
        Get user's GitHub token.

        Args:
            user_id: User ID
            token_type: "oauth" or "app"

        Returns:
            Token record or None
        """
        token = await self.db.githubtoken.find_unique(
            where={"userId_tokenType": {"userId": user_id, "tokenType": token_type}}
        )

        if not token:
            return None

        # Check if revoked
        if token.isRevoked:
            logger.warning("token_is_revoked", user_id=user_id)
            return None

        # Check if expired (for GitHub Apps)
        if token.expiresAt and token.expiresAt < datetime.utcnow():
            logger.warning("token_expired", user_id=user_id)
            await self.mark_revoked(user_id, token_type)
            return None

        # Update last used
        await self.db.githubtoken.update(
            where={"id": token.id}, data={"lastUsedAt": datetime.utcnow()}
        )

        return token

    async def verify_token(self, user_id: str, token_type: str = "oauth") -> bool:
        """
        Verify token is still valid with GitHub.

        Args:
            user_id: User ID
            token_type: "oauth" or "app"

        Returns:
            True if token is valid
        """
        token = await self.get_token(user_id, token_type)
        if not token:
            return False

        # TODO: Decrypt token
        decrypted_token = token.accessToken

        # Verify with GitHub
        try:
            async with GitHubRESTClient(decrypted_token, token_type) as client:
                is_valid = await client.verify_token()

                if is_valid:
                    # Update last verified
                    await self.db.githubtoken.update(
                        where={"id": token.id}, data={"lastVerified": datetime.utcnow()}
                    )
                    logger.info("token_verified", user_id=user_id)
                else:
                    # Mark as revoked
                    await self.mark_revoked(user_id, token_type)
                    logger.warning("token_verification_failed", user_id=user_id)

                return is_valid

        except Exception as e:
            logger.error("token_verification_error", user_id=user_id, error=str(e))
            return False

    async def mark_revoked(self, user_id: str, token_type: str = "oauth") -> None:
        """
        Mark token as revoked.

        Args:
            user_id: User ID
            token_type: "oauth" or "app"
        """
        await self.db.githubtoken.update(
            where={"userId_tokenType": {"userId": user_id, "tokenType": token_type}},
            data={"isRevoked": True},
        )

        logger.warning("token_marked_revoked", user_id=user_id, token_type=token_type)

    async def delete_token(self, user_id: str, token_type: str = "oauth") -> None:
        """
        Delete user's GitHub token.

        Args:
            user_id: User ID
            token_type: "oauth" or "app"
        """
        await self.db.githubtoken.delete(
            where={"userId_tokenType": {"userId": user_id, "tokenType": token_type}}
        )

        logger.info("token_deleted", user_id=user_id, token_type=token_type)

    async def cleanup_expired_tokens(self, days: int = 90) -> int:
        """
        Clean up old revoked tokens.

        Args:
            days: Delete tokens older than this many days

        Returns:
            Number of tokens deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.githubtoken.delete_many(
            where={"isRevoked": True, "updatedAt": {"lt": cutoff_date}}
        )

        logger.info("expired_tokens_cleaned", count=result)

        return result
