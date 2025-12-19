"""
Badge service for managing badge definitions, awards, and revocations.
Handles both automatic and manual badge operations with full audit logging.
"""

from datetime import datetime
from typing import Optional

import structlog
from prisma.models import Badge, BadgeAuditLog, UserBadge

from prisma import Prisma

logger = structlog.get_logger(__name__)


class BadgeService:
    """Service for badge-related operations."""

    def __init__(self, db: Prisma):
        """Initialize badge service with Prisma client."""
        self.db = db

    async def get_all_badges(
        self, include_inactive: bool = False
    ) -> list[Badge]:
        """
        Get all badge definitions.

        Args:
            include_inactive: Include inactive badges

        Returns:
            List of badges
        """
        where = {} if include_inactive else {"isActive": True}
        return await self.db.badge.find_many(where=where, order={"rarity": "desc"})

    async def get_badge_by_id(self, badge_id: str) -> Optional[Badge]:
        """
        Get badge by ID.

        Args:
            badge_id: Badge ID

        Returns:
            Badge if found, None otherwise
        """
        return await self.db.badge.find_unique(where={"id": badge_id})

    async def get_badge_by_name(self, name: str) -> Optional[Badge]:
        """
        Get badge by name.

        Args:
            name: Badge name

        Returns:
            Badge if found, None otherwise
        """
        return await self.db.badge.find_unique(where={"name": name})

    async def get_user_badges(self, user_id: str) -> list[UserBadge]:
        """
        Get all badges earned by a user.

        Args:
            user_id: User ID

        Returns:
            List of user badges with badge details
        """
        return await self.db.userbadge.find_many(
            where={"userId": user_id},
            include={"badge": True},
            order={"earnedAt": "desc"},
        )

    async def has_badge(self, user_id: str, badge_id: str) -> bool:
        """
        Check if user has earned a badge.

        Args:
            user_id: User ID
            badge_id: Badge ID

        Returns:
            True if user has badge, False otherwise
        """
        user_badge = await self.db.userbadge.find_unique(
            where={"userId_badgeId": {"userId": user_id, "badgeId": badge_id}}
        )
        return user_badge is not None

    async def award_badge(
        self,
        user_id: str,
        badge_id: str,
        awarded_by: Optional[str] = None,
        metadata: Optional[dict] = None,
        justification: Optional[str] = None,
    ) -> Optional[UserBadge]:
        """
        Award a badge to a user.
        Prevents duplicate awards and logs to audit trail.

        Args:
            user_id: User ID to award badge to
            badge_id: Badge ID to award
            awarded_by: User ID who awarded (None for auto-awards)
            metadata: Additional context (e.g., PR that triggered)
            justification: Reason for manual award

        Returns:
            UserBadge if awarded, None if already has badge
        """
        # Check if user already has badge
        if await self.has_badge(user_id, badge_id):
            logger.debug(
                "badge_already_earned",
                user_id=user_id,
                badge_id=badge_id,
            )
            return None

        # Check if badge exists and is active
        badge = await self.get_badge_by_id(badge_id)
        if not badge:
            logger.warning("badge_not_found", badge_id=badge_id)
            raise ValueError(f"Badge {badge_id} not found")

        if not badge.isActive:
            logger.warning("badge_inactive", badge_id=badge_id)
            raise ValueError(f"Badge {badge_id} is not active")

        is_manual = awarded_by is not None

        # Award badge
        user_badge = await self.db.userbadge.create(
            data={
                "userId": user_id,
                "badgeId": badge_id,
                "awardedBy": awarded_by,
                "isManual": is_manual,
                "metadata": metadata or {},
            }
        )

        # Log to audit trail
        await self.db.badgeauditlog.create(
            data={
                "userId": user_id,
                "badgeId": badge_id,
                "action": "AWARDED",
                "awardedBy": awarded_by,
                "isManual": is_manual,
                "justification": justification,
                "metadata": metadata or {},
            }
        )

        logger.info(
            "badge_awarded",
            user_id=user_id,
            badge_id=badge_id,
            badge_name=badge.name,
            is_manual=is_manual,
            awarded_by=awarded_by,
        )

        return user_badge

    async def revoke_badge(
        self,
        user_id: str,
        badge_id: str,
        revoked_by: str,
        justification: str,
    ) -> bool:
        """
        Revoke a badge from a user.
        Requires justification and logs to audit trail.

        Args:
            user_id: User ID to revoke badge from
            badge_id: Badge ID to revoke
            revoked_by: User ID who revoked
            justification: Reason for revocation

        Returns:
            True if revoked, False if user didn't have badge
        """
        # Check if user has badge
        user_badge = await self.db.userbadge.find_unique(
            where={"userId_badgeId": {"userId": user_id, "badgeId": badge_id}}
        )

        if not user_badge:
            logger.debug(
                "badge_not_earned",
                user_id=user_id,
                badge_id=badge_id,
            )
            return False

        # Delete user badge
        await self.db.userbadge.delete(
            where={"userId_badgeId": {"userId": user_id, "badgeId": badge_id}}
        )

        # Log to audit trail
        await self.db.badgeauditlog.create(
            data={
                "userId": user_id,
                "badgeId": badge_id,
                "action": "REVOKED",
                "awardedBy": revoked_by,
                "isManual": True,
                "justification": justification,
                "metadata": {},
            }
        )

        logger.warning(
            "badge_revoked",
            user_id=user_id,
            badge_id=badge_id,
            revoked_by=revoked_by,
            justification=justification,
        )

        return True

    async def get_badge_distribution(self) -> dict:
        """
        Get badge distribution statistics.

        Returns:
            Dictionary with badge statistics
        """
        # Get total badges
        total_badges = await self.db.badge.count(where={"isActive": True})

        # Get badges by rarity
        badges_by_rarity = {}
        for rarity in ["COMMON", "RARE", "EPIC", "LEGENDARY"]:
            count = await self.db.badge.count(
                where={"rarity": rarity, "isActive": True}
            )
            badges_by_rarity[rarity] = count

        # Get total awards
        total_awards = await self.db.userbadge.count()

        # Get manual vs auto awards
        manual_awards = await self.db.userbadge.count(where={"isManual": True})
        auto_awards = total_awards - manual_awards

        # Get most awarded badges
        # Note: This is a simplified version. For production, use raw SQL for better performance
        all_user_badges = await self.db.userbadge.find_many(include={"badge": True})
        badge_counts = {}
        for ub in all_user_badges:
            badge_name = ub.badge.name if ub.badge else "Unknown"
            badge_counts[badge_name] = badge_counts.get(badge_name, 0) + 1

        most_awarded = sorted(
            badge_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_badges": total_badges,
            "badges_by_rarity": badges_by_rarity,
            "total_awards": total_awards,
            "manual_awards": manual_awards,
            "auto_awards": auto_awards,
            "most_awarded": [
                {"badge_name": name, "count": count} for name, count in most_awarded
            ],
        }

    async def get_badge_audit_logs(
        self,
        user_id: Optional[str] = None,
        badge_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[BadgeAuditLog]:
        """
        Get badge audit logs with optional filtering.

        Args:
            user_id: Filter by user ID
            badge_id: Filter by badge ID
            action: Filter by action (AWARDED, REVOKED)
            limit: Maximum number of logs to return

        Returns:
            List of audit logs
        """
        where = {}
        if user_id:
            where["userId"] = user_id
        if badge_id:
            where["badgeId"] = badge_id
        if action:
            where["action"] = action

        return await self.db.badgeauditlog.find_many(
            where=where, order={"createdAt": "desc"}, take=limit
        )
