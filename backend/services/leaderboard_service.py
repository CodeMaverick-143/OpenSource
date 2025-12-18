"""
Leaderboard service with multiple types and Redis caching.
"""

from datetime import datetime
from typing import List, Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class LeaderboardService:
    """
    Leaderboard service with multiple types.

    Types:
    - Global (all-time)
    - Monthly (time-windowed)
    - Project-wise
    - Skill/tag-based
    """

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def get_global_leaderboard(self, limit: int = 100, offset: int = 0) -> dict:
        """
        Get global leaderboard (all-time).

        Args:
            limit: Number of users to return
            offset: Pagination offset

        Returns:
            Leaderboard data
        """
        # Get latest snapshot
        snapshot = await self.db.leaderboardsnapshot.find_first(
            where={"leaderboardType": "GLOBAL"},
            order={"snapshotAt": "desc"},
        )

        if snapshot:
            # Use snapshot
            top_users = snapshot.topUsers
            total = len(top_users)

            # Paginate
            paginated_users = top_users[offset : offset + limit]

            return {
                "leaderboard_type": "GLOBAL",
                "users": paginated_users,
                "total": total,
                "snapshot_at": snapshot.snapshotAt,
            }

        # Fallback to live query
        users = await self.db.user.find_many(
            where={"isDeleted": False, "isBanned": False},
            order=[{"totalPoints": "desc"}, {"createdAt": "asc"}],
            skip=offset,
            take=limit,
        )

        total = await self.db.user.count(where={"isDeleted": False, "isBanned": False})

        return {
            "leaderboard_type": "GLOBAL",
            "users": [
                {
                    "user_id": u.id,
                    "username": u.githubUsername,
                    "points": u.totalPoints,
                    "rank": offset + i + 1,
                }
                for i, u in enumerate(users)
            ],
            "total": total,
            "snapshot_at": None,
        }

    async def get_monthly_leaderboard(
        self, year: int, month: int, limit: int = 100, offset: int = 0
    ) -> dict:
        """
        Get monthly leaderboard.

        Args:
            year: Year
            month: Month (1-12)
            limit: Number of users to return
            offset: Pagination offset

        Returns:
            Leaderboard data
        """
        period = f"{year}-{month:02d}"

        # Get latest snapshot for period
        snapshot = await self.db.leaderboardsnapshot.find_first(
            where={"leaderboardType": "MONTHLY", "period": period},
            order={"snapshotAt": "desc"},
        )

        if snapshot:
            # Use snapshot
            top_users = snapshot.topUsers
            total = len(top_users)

            # Paginate
            paginated_users = top_users[offset : offset + limit]

            return {
                "leaderboard_type": "MONTHLY",
                "period": period,
                "users": paginated_users,
                "total": total,
                "snapshot_at": snapshot.snapshotAt,
            }

        # Fallback to live query
        from datetime import datetime

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Get transactions in period
        transactions = await self.db.pointtransaction.find_many(
            where={"createdAt": {"gte": start_date, "lt": end_date}},
            include={"user": True},
        )

        # Aggregate by user
        user_points = {}
        for t in transactions:
            if t.userId not in user_points:
                user_points[t.userId] = {"points": 0, "user": t.user}
            user_points[t.userId]["points"] += t.points

        # Sort
        sorted_users = sorted(
            user_points.items(),
            key=lambda x: (-x[1]["points"], x[1]["user"].createdAt),
        )

        # Paginate
        paginated = sorted_users[offset : offset + limit]

        return {
            "leaderboard_type": "MONTHLY",
            "period": period,
            "users": [
                {
                    "user_id": user_id,
                    "username": data["user"].githubUsername,
                    "points": data["points"],
                    "rank": offset + i + 1,
                }
                for i, (user_id, data) in enumerate(paginated)
            ],
            "total": len(sorted_users),
            "snapshot_at": None,
        }

    async def get_project_leaderboard(
        self, project_id: str, limit: int = 50, offset: int = 0
    ) -> dict:
        """
        Get project-wise leaderboard.

        Args:
            project_id: Project ID
            limit: Number of users to return
            offset: Pagination offset

        Returns:
            Leaderboard data
        """
        # Get latest snapshot
        snapshot = await self.db.leaderboardsnapshot.find_first(
            where={"leaderboardType": "PROJECT", "period": project_id},
            order={"snapshotAt": "desc"},
        )

        if snapshot:
            # Use snapshot
            top_users = snapshot.topUsers
            total = len(top_users)

            # Paginate
            paginated_users = top_users[offset : offset + limit]

            return {
                "leaderboard_type": "PROJECT",
                "project_id": project_id,
                "users": paginated_users,
                "total": total,
                "snapshot_at": snapshot.snapshotAt,
            }

        # Fallback to live query
        transactions = await self.db.pointtransaction.find_many(
            where={"pullRequest": {"repository": {"projectId": project_id}}},
            include={"user": True},
        )

        # Aggregate by user
        user_points = {}
        for t in transactions:
            if t.userId not in user_points:
                user_points[t.userId] = {"points": 0, "user": t.user}
            user_points[t.userId]["points"] += t.points

        # Sort
        sorted_users = sorted(
            user_points.items(),
            key=lambda x: (-x[1]["points"], x[1]["user"].createdAt),
        )

        # Paginate
        paginated = sorted_users[offset : offset + limit]

        return {
            "leaderboard_type": "PROJECT",
            "project_id": project_id,
            "users": [
                {
                    "user_id": user_id,
                    "username": data["user"].githubUsername,
                    "points": data["points"],
                    "rank": offset + i + 1,
                }
                for i, (user_id, data) in enumerate(paginated)
            ],
            "total": len(sorted_users),
            "snapshot_at": None,
        }

    async def save_leaderboard_snapshot(
        self,
        leaderboard_type: str,
        top_users: List[dict],
        period: Optional[str] = None,
    ) -> None:
        """
        Save leaderboard snapshot.

        Args:
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            top_users: List of {user_id, rank, points}
            period: Period identifier
        """
        await self.db.leaderboardsnapshot.create(
            data={
                "leaderboardType": leaderboard_type,
                "period": period,
                "topUsers": top_users,
                "snapshotAt": datetime.utcnow(),
            }
        )

        logger.info(
            "leaderboard_snapshot_saved",
            leaderboard_type=leaderboard_type,
            period=period,
            total_users=len(top_users),
        )

    async def get_user_rank_position(
        self, user_id: str, leaderboard_type: str, period: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get user's rank position.

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
