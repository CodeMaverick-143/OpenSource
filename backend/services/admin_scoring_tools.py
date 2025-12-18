"""
Admin scoring tools for overrides and manual interventions.
"""

from datetime import datetime
from typing import Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class AdminScoringTools:
    """
    Admin tools for score management with audit logging.

    All overrides:
    - Logged to AuditLog
    - Reversible
    - Never silently alter history
    """

    def __init__(self, db: Prisma):
        """Initialize admin tools."""
        self.db = db

    async def freeze_user_score(self, user_id: str, admin_id: str, reason: str) -> dict:
        """
        Freeze user's score (prevent new points).

        Args:
            user_id: User ID to freeze
            admin_id: Admin user ID
            reason: Reason for freeze

        Returns:
            Freeze result
        """
        # Update user to frozen state (using isBanned as proxy)
        user = await self.db.user.update(where={"id": user_id}, data={"isBanned": True})

        # Log to audit
        await self.db.auditlog.create(
            data={
                "userId": admin_id,
                "action": "FREEZE_USER_SCORE",
                "targetId": user_id,
                "metadata": {"reason": reason},
            }
        )

        logger.warning(
            "user_score_frozen",
            user_id=user_id,
            admin_id=admin_id,
            reason=reason,
        )

        return {"user_id": user_id, "frozen": True}

    async def unfreeze_user_score(self, user_id: str, admin_id: str, reason: str) -> dict:
        """
        Unfreeze user's score.

        Args:
            user_id: User ID to unfreeze
            admin_id: Admin user ID
            reason: Reason for unfreeze

        Returns:
            Unfreeze result
        """
        # Update user to unfrozen state
        user = await self.db.user.update(where={"id": user_id}, data={"isBanned": False})

        # Log to audit
        await self.db.auditlog.create(
            data={
                "userId": admin_id,
                "action": "UNFREEZE_USER_SCORE",
                "targetId": user_id,
                "metadata": {"reason": reason},
            }
        )

        logger.info(
            "user_score_unfrozen",
            user_id=user_id,
            admin_id=admin_id,
            reason=reason,
        )

        return {"user_id": user_id, "frozen": False}

    async def reverse_transaction(self, transaction_id: str, admin_id: str, reason: str) -> dict:
        """
        Reverse a point transaction (create reversal).

        Args:
            transaction_id: Transaction ID to reverse
            admin_id: Admin user ID
            reason: Reason for reversal

        Returns:
            Reversal result
        """
        # Get original transaction
        original = await self.db.pointtransaction.find_unique(where={"id": transaction_id})

        if not original:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Create reversal transaction
        async with self.db.tx() as transaction:
            reversal = await transaction.pointtransaction.create(
                data={
                    "userId": original.userId,
                    "pullRequestId": original.pullRequestId,
                    "points": -original.points,  # Negative of original
                    "reason": f"REVERSAL_{original.reason}",
                    "transactionType": "REVERSAL",
                    "metadata": {
                        "original_transaction_id": transaction_id,
                        "admin_id": admin_id,
                        "reason": reason,
                    },
                }
            )

            # Update user total points
            await transaction.user.update(
                where={"id": original.userId},
                data={"totalPoints": {"decrement": original.points}},
            )

            # Log to audit
            await transaction.auditlog.create(
                data={
                    "userId": admin_id,
                    "action": "REVERSE_TRANSACTION",
                    "targetId": transaction_id,
                    "metadata": {
                        "reason": reason,
                        "original_points": original.points,
                        "reversal_id": reversal.id,
                    },
                }
            )

        logger.warning(
            "transaction_reversed",
            transaction_id=transaction_id,
            reversal_id=reversal.id,
            admin_id=admin_id,
            reason=reason,
        )

        return {
            "original_transaction_id": transaction_id,
            "reversal_id": reversal.id,
            "points_reversed": original.points,
        }

    async def flag_suspicious_pr(self, pr_id: str, admin_id: str, reason: str) -> dict:
        """
        Flag PR as suspicious.

        Args:
            pr_id: PR ID
            admin_id: Admin user ID
            reason: Reason for flag

        Returns:
            Flag result
        """
        # Log to audit
        await self.db.auditlog.create(
            data={
                "userId": admin_id,
                "action": "FLAG_SUSPICIOUS_PR",
                "targetId": pr_id,
                "metadata": {"reason": reason},
            }
        )

        logger.warning(
            "pr_flagged_suspicious",
            pr_id=pr_id,
            admin_id=admin_id,
            reason=reason,
        )

        return {"pr_id": pr_id, "flagged": True}

    async def exclude_pr_from_scoring(self, pr_id: str, admin_id: str, reason: str) -> dict:
        """
        Exclude PR from scoring (mark as inactive).

        Args:
            pr_id: PR ID
            admin_id: Admin user ID
            reason: Reason for exclusion

        Returns:
            Exclusion result
        """
        # Update PR to inactive
        pr = await self.db.pullrequest.update(where={"id": pr_id}, data={"isActive": False})

        # Log to audit
        await self.db.auditlog.create(
            data={
                "userId": admin_id,
                "action": "EXCLUDE_PR_FROM_SCORING",
                "targetId": pr_id,
                "metadata": {"reason": reason},
            }
        )

        logger.warning(
            "pr_excluded_from_scoring",
            pr_id=pr_id,
            admin_id=admin_id,
            reason=reason,
        )

        return {"pr_id": pr_id, "excluded": True}

    async def get_audit_log(self, action: Optional[str] = None, limit: int = 100) -> list:
        """
        Get audit log of admin actions.

        Args:
            action: Filter by action type
            limit: Number of records to return

        Returns:
            Audit log records
        """
        where_clause = {}
        if action:
            where_clause["action"] = action

        logs = await self.db.auditlog.find_many(
            where=where_clause, order={"createdAt": "desc"}, take=limit
        )

        return logs
