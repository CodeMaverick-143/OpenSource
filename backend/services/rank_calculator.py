"""
Rank calculator for deterministic rank calculation with snapshots.
"""

from datetime import datetime
from typing import List, Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class RankCalculator:
    """
    Calculate user ranks deterministically.

    Ordering:
    - Points DESC
    - Earliest contribution wins tie (created_at ASC)
    """

    def __init__(self, db: Prisma):
        """Initialize calculator."""
        self.db = db

    async def calculate_global_ranks(self) -> List[dict]:
        """
        Calculate global ranks for all users.

        Returns:
            List of {user_id, rank, points}
        """
        # Get all users ordered by points DESC, created_at ASC
        users = await self.db.user.find_many(
            where={"isDeleted": False, "isBanned": False},
            order=[{"totalPoints": "desc"}, {"createdAt": "asc"}],
        )

        ranks = []
        current_rank = 1

        for user in users:
            ranks.append(
                {
                    "user_id": user.id,
                    "rank": current_rank,
                    "points": user.totalPoints,
                }
            )
            current_rank += 1

        logger.info("global_ranks_calculated", total_users=len(ranks))

        return ranks

    async def calculate_monthly_ranks(self, year: int, month: int) -> List[dict]:
        """
        Calculate monthly ranks based on points earned in period.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            List of {user_id, rank, points}
        """
        from datetime import datetime

        # Get start and end of month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Get all transactions in period
        transactions = await self.db.pointtransaction.find_many(
            where={"createdAt": {"gte": start_date, "lt": end_date}},
            include={"user": True},
        )

        # Aggregate points by user
        user_points = {}
        user_created_at = {}

        for transaction in transactions:
            user_id = transaction.userId
            if user_id not in user_points:
                user_points[user_id] = 0
                user_created_at[user_id] = transaction.user.createdAt

            user_points[user_id] += transaction.points

        # Sort by points DESC, created_at ASC
        sorted_users = sorted(
            user_points.items(),
            key=lambda x: (-x[1], user_created_at[x[0]]),
        )

        ranks = []
        current_rank = 1

        for user_id, points in sorted_users:
            ranks.append({"user_id": user_id, "rank": current_rank, "points": points})
            current_rank += 1

        logger.info(
            "monthly_ranks_calculated",
            year=year,
            month=month,
            total_users=len(ranks),
        )

        return ranks

    async def calculate_project_ranks(self, project_id: str) -> List[dict]:
        """
        Calculate ranks for project contributors.

        Args:
            project_id: Project ID

        Returns:
            List of {user_id, rank, points}
        """
        # Get all transactions for project's PRs
        transactions = await self.db.pointtransaction.find_many(
            where={"pullRequest": {"repository": {"projectId": project_id}}},
            include={"user": True},
        )

        # Aggregate points by user
        user_points = {}
        user_created_at = {}

        for transaction in transactions:
            user_id = transaction.userId
            if user_id not in user_points:
                user_points[user_id] = 0
                user_created_at[user_id] = transaction.user.createdAt

            user_points[user_id] += transaction.points

        # Sort by points DESC, created_at ASC
        sorted_users = sorted(
            user_points.items(),
            key=lambda x: (-x[1], user_created_at[x[0]]),
        )

        ranks = []
        current_rank = 1

        for user_id, points in sorted_users:
            ranks.append({"user_id": user_id, "rank": current_rank, "points": points})
            current_rank += 1

        logger.info(
            "project_ranks_calculated",
            project_id=project_id,
            total_users=len(ranks),
        )

        return ranks

    async def save_rank_snapshot(
        self,
        leaderboard_type: str,
        ranks: List[dict],
        period: Optional[str] = None,
    ) -> None:
        """
        Save rank snapshot to database.

        Args:
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            ranks: List of {user_id, rank, points}
            period: Period identifier (e.g., "2025-01" for monthly)
        """
        snapshot_at = datetime.utcnow()

        # Create rank snapshots
        for rank_data in ranks:
            await self.db.ranksnapshot.create(
                data={
                    "userId": rank_data["user_id"],
                    "leaderboardType": leaderboard_type,
                    "rank": rank_data["rank"],
                    "totalPoints": rank_data["points"],
                    "period": period,
                    "snapshotAt": snapshot_at,
                }
            )

        logger.info(
            "rank_snapshot_saved",
            leaderboard_type=leaderboard_type,
            period=period,
            total_ranks=len(ranks),
        )

    async def get_user_rank(
        self, user_id: str, leaderboard_type: str, period: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get user's rank from latest snapshot.

        Args:
            user_id: User ID
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            period: Period identifier

        Returns:
            Rank data or None
        """
        snapshot = await self.db.ranksnapshot.find_first(
            where={
                "userId": user_id,
                "leaderboardType": leaderboard_type,
                "period": period,
            },
            order={"snapshotAt": "desc"},
        )

        if not snapshot:
            return None

        return {
            "rank": snapshot.rank,
            "points": snapshot.totalPoints,
            "snapshot_at": snapshot.snapshotAt,
        }
