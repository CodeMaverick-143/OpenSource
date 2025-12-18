"""
Contribution graph service for generating contribution heatmaps.
"""

from datetime import datetime, timedelta
from typing import Dict, List

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class ContributionGraphService:
    """Service for generating contribution graphs and statistics."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def generate_contribution_graph(self, user_id: str, range_type: str = "30d") -> Dict:
        """
        Generate contribution graph data for a user.

        Args:
            user_id: User ID
            range_type: Time range (30d, 90d, all)

        Returns:
            Dictionary with contribution data and stats
        """
        logger.info("generating_contribution_graph", user_id=user_id, range_type=range_type)

        # Calculate date range
        end_date = datetime.utcnow()
        if range_type == "30d":
            start_date = end_date - timedelta(days=30)
        elif range_type == "90d":
            start_date = end_date - timedelta(days=90)
        else:  # all
            start_date = None

        # Build where clause
        where_clause = {
            "authorId": user_id,
            "status": "MERGED",  # Only count merged PRs
        }

        if start_date:
            where_clause["mergedAt"] = {"gte": start_date}

        # Fetch merged PRs
        merged_prs = await self.db.pullrequest.find_many(
            where=where_clause,
            order=[{"mergedAt": "asc"}],
        )

        # Group by date
        contributions_by_date: Dict[str, int] = {}
        for pr in merged_prs:
            if pr.mergedAt:
                date_str = pr.mergedAt.date().isoformat()
                contributions_by_date[date_str] = contributions_by_date.get(date_str, 0) + 1

        # Generate complete date range with zeros for missing dates
        data = []
        if start_date:
            current_date = start_date.date()
            end = end_date.date()
            while current_date <= end:
                date_str = current_date.isoformat()
                data.append({"date": date_str, "count": contributions_by_date.get(date_str, 0)})
                current_date += timedelta(days=1)
        else:
            # For "all" range, only include dates with contributions
            for date_str in sorted(contributions_by_date.keys()):
                data.append({"date": date_str, "count": contributions_by_date[date_str]})

        # Calculate statistics
        stats = await self._calculate_contribution_stats(contributions_by_date, merged_prs)

        logger.info(
            "contribution_graph_generated",
            user_id=user_id,
            range_type=range_type,
            total_contributions=stats["total_contributions"],
        )

        return {"range": range_type, "data": data, "stats": stats}

    async def _calculate_contribution_stats(
        self, contributions_by_date: Dict[str, int], merged_prs: List
    ) -> Dict:
        """
        Calculate contribution statistics.

        Args:
            contributions_by_date: Dictionary of date -> count
            merged_prs: List of merged PRs

        Returns:
            Statistics dictionary
        """
        total_contributions = len(merged_prs)

        # Calculate current streak
        current_streak = 0
        today = datetime.utcnow().date()
        check_date = today
        while True:
            date_str = check_date.isoformat()
            if contributions_by_date.get(date_str, 0) > 0:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        # Calculate longest streak
        longest_streak = 0
        current_run = 0
        if contributions_by_date:
            sorted_dates = sorted(contributions_by_date.keys())
            if sorted_dates:
                prev_date = None
                for date_str in sorted_dates:
                    current_date = datetime.fromisoformat(date_str).date()
                    if prev_date is None or (current_date - prev_date).days == 1:
                        current_run += 1
                        longest_streak = max(longest_streak, current_run)
                    else:
                        current_run = 1
                    prev_date = current_date

        # Find best day
        best_day = None
        if contributions_by_date:
            max_count = max(contributions_by_date.values())
            for date_str, count in contributions_by_date.items():
                if count == max_count:
                    best_day = {"date": date_str, "count": count}
                    break

        return {
            "total_contributions": total_contributions,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "best_day": best_day,
        }

    async def get_contribution_stats(self, user_id: str) -> Dict:
        """
        Get contribution statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Statistics dictionary
        """
        logger.info("fetching_contribution_stats", user_id=user_id)

        # Fetch all merged PRs
        merged_prs = await self.db.pullrequest.find_many(
            where={"authorId": user_id, "status": "MERGED"},
            order=[{"mergedAt": "asc"}],
        )

        # Group by date
        contributions_by_date: Dict[str, int] = {}
        for pr in merged_prs:
            if pr.mergedAt:
                date_str = pr.mergedAt.date().isoformat()
                contributions_by_date[date_str] = contributions_by_date.get(date_str, 0) + 1

        # Calculate statistics
        stats = await self._calculate_contribution_stats(contributions_by_date, merged_prs)

        logger.info(
            "contribution_stats_fetched",
            user_id=user_id,
            total_contributions=stats["total_contributions"],
        )

        return stats
