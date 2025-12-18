"""
Point ledger with append-only transactions and atomic updates.
"""

from typing import Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class PointLedger:
    """
    Append-only point transaction ledger.

    Rules:
    - Every score award creates a PointTransaction
    - Transactions are never deleted or modified
    - User.totalPoints is updated atomically
    - Reversals create negative transactions
    """

    def __init__(self, db: Prisma):
        """Initialize ledger."""
        self.db = db

    async def award_points(
        self,
        user_id: str,
        pr_id: str,
        points: int,
        reason: str,
        transaction_type: str = "AWARD",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Award points to user (append-only).

        Args:
            user_id: User ID
            pr_id: PR ID
            points: Points to award
            reason: Reason for award
            transaction_type: Transaction type (AWARD, BONUS, PENALTY, REVERSAL)
            metadata: Additional metadata

        Returns:
            Created transaction
        """
        # Use database transaction for atomicity
        async with self.db.tx() as transaction:
            # Create point transaction (append-only)
            point_transaction = await transaction.pointtransaction.create(
                data={
                    "userId": user_id,
                    "pullRequestId": pr_id,
                    "points": points,
                    "reason": reason,
                    "transactionType": transaction_type,
                    "metadata": metadata or {},
                }
            )

            # Update user total points atomically
            await transaction.user.update(
                where={"id": user_id}, data={"totalPoints": {"increment": points}}
            )

            logger.info(
                "points_awarded",
                user_id=user_id,
                pr_id=pr_id,
                points=points,
                reason=reason,
                transaction_type=transaction_type,
                transaction_id=point_transaction.id,
            )

        return point_transaction

    async def create_reversal(
        self,
        user_id: str,
        pr_id: str,
        original_transaction_id: str,
        reason: str,
    ) -> dict:
        """
        Create reversal transaction (negative points).

        Args:
            user_id: User ID
            pr_id: PR ID
            original_transaction_id: ID of transaction to reverse
            reason: Reason for reversal

        Returns:
            Reversal transaction
        """
        # Get original transaction
        original = await self.db.pointtransaction.find_unique(where={"id": original_transaction_id})

        if not original:
            raise ValueError(f"Original transaction {original_transaction_id} not found")

        # Create reversal (negative points)
        reversal_points = -original.points

        reversal = await self.award_points(
            user_id=user_id,
            pr_id=pr_id,
            points=reversal_points,
            reason=reason,
            transaction_type="REVERSAL",
            metadata={
                "original_transaction_id": original_transaction_id,
                "original_points": original.points,
            },
        )

        logger.warning(
            "points_reversed",
            user_id=user_id,
            pr_id=pr_id,
            original_points=original.points,
            reversal_points=reversal_points,
            reason=reason,
        )

        return reversal

    async def get_user_balance(self, user_id: str) -> int:
        """
        Get user's current point balance.

        Args:
            user_id: User ID

        Returns:
            Total points
        """
        user = await self.db.user.find_unique(where={"id": user_id})

        if not user:
            return 0

        return user.totalPoints

    async def get_transaction_history(self, user_id: str, limit: int = 100) -> list:
        """
        Get user's transaction history.

        Args:
            user_id: User ID
            limit: Maximum transactions to return

        Returns:
            List of transactions
        """
        transactions = await self.db.pointtransaction.find_many(
            where={"userId": user_id},
            order={"createdAt": "desc"},
            take=limit,
            include={"pullRequest": True},
        )

        return transactions

    async def verify_ledger_integrity(self, user_id: str) -> bool:
        """
        Verify ledger integrity for user.

        Args:
            user_id: User ID

        Returns:
            True if ledger is consistent
        """
        # Get all transactions
        transactions = await self.db.pointtransaction.find_many(where={"userId": user_id})

        # Calculate sum
        calculated_total = sum(t.points for t in transactions)

        # Get user's total
        user = await self.db.user.find_unique(where={"id": user_id})

        if not user:
            return False

        # Verify consistency
        is_consistent = calculated_total == user.totalPoints

        if not is_consistent:
            logger.error(
                "ledger_integrity_error",
                user_id=user_id,
                calculated_total=calculated_total,
                stored_total=user.totalPoints,
            )

        return is_consistent
