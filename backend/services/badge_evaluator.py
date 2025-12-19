"""
Badge evaluator for checking if users meet badge criteria.
Implements the auto-award engine logic for all badge types.
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from prisma.models import Badge

from prisma import Prisma

logger = structlog.get_logger(__name__)


class BadgeEvaluator:
    """Service for evaluating badge criteria."""

    def __init__(self, db: Prisma):
        """Initialize badge evaluator with Prisma client."""
        self.db = db

    async def evaluate_pr_count(self, user_id: str, threshold: int) -> bool:
        """
        Check if user has merged at least threshold PRs.

        Args:
            user_id: User ID
            threshold: Minimum number of merged PRs

        Returns:
            True if user meets criteria
        """
        merged_count = await self.db.pullrequest.count(
            where={"authorId": user_id, "status": "MERGED"}
        )
        return merged_count >= threshold

    async def evaluate_quality_rating(
        self, user_id: str, min_rating: float, min_prs: int
    ) -> bool:
        """
        Check if user has high average rating with minimum PR count.

        Args:
            user_id: User ID
            min_rating: Minimum average rating (1-5)
            min_prs: Minimum number of PRs to qualify

        Returns:
            True if user meets criteria
        """
        # Get all merged PRs with reviews
        prs = await self.db.pullrequest.find_many(
            where={"authorId": user_id, "status": "MERGED"},
            include={"reviews": True},
        )

        if len(prs) < min_prs:
            return False

        # Calculate average rating
        total_rating = 0
        rated_reviews = 0

        for pr in prs:
            for review in pr.reviews:
                if review.rating is not None:
                    total_rating += review.rating
                    rated_reviews += 1

        if rated_reviews == 0:
            return False

        avg_rating = total_rating / rated_reviews
        return avg_rating >= min_rating

    async def evaluate_streak(self, user_id: str, months: int) -> bool:
        """
        Check if user has contributed for consecutive months.

        Args:
            user_id: User ID
            months: Number of consecutive months required

        Returns:
            True if user meets criteria
        """
        # Get all merged PRs ordered by merge date
        prs = await self.db.pullrequest.find_many(
            where={"authorId": user_id, "status": "MERGED"},
            order={"mergedAt": "desc"},
        )

        if not prs:
            return False

        # Track months with contributions
        contribution_months = set()
        for pr in prs:
            if pr.mergedAt:
                month_key = pr.mergedAt.strftime("%Y-%m")
                contribution_months.add(month_key)

        # Check for consecutive months
        if len(contribution_months) < months:
            return False

        # Sort months and check for consecutive streak
        sorted_months = sorted(contribution_months, reverse=True)
        current_streak = 1

        for i in range(len(sorted_months) - 1):
            current = datetime.strptime(sorted_months[i], "%Y-%m")
            next_month = datetime.strptime(sorted_months[i + 1], "%Y-%m")

            # Check if next month is exactly one month before current
            expected_next = current.replace(day=1) - timedelta(days=1)
            expected_next = expected_next.replace(day=1)

            if next_month.replace(day=1) == expected_next:
                current_streak += 1
                if current_streak >= months:
                    return True
            else:
                current_streak = 1

        return current_streak >= months

    async def evaluate_project_champion(
        self, user_id: str, project_id: str, min_percentage: float = 0.3
    ) -> bool:
        """
        Check if user is a top contributor in a project.
        User must have contributed at least min_percentage of project's PRs.

        Args:
            user_id: User ID
            project_id: Project ID
            min_percentage: Minimum percentage of project PRs (0.0-1.0)

        Returns:
            True if user meets criteria
        """
        # Get all repositories for the project
        repositories = await self.db.repository.find_many(
            where={"projectId": project_id}
        )

        if not repositories:
            return False

        repo_ids = [repo.id for repo in repositories]

        # Get total merged PRs for project
        total_prs = await self.db.pullrequest.count(
            where={"repositoryId": {"in": repo_ids}, "status": "MERGED"}
        )

        if total_prs == 0:
            return False

        # Get user's merged PRs for project
        user_prs = await self.db.pullrequest.count(
            where={
                "repositoryId": {"in": repo_ids},
                "authorId": user_id,
                "status": "MERGED",
            }
        )

        percentage = user_prs / total_prs
        return percentage >= min_percentage

    async def evaluate_first_pr(self, user_id: str) -> bool:
        """
        Check if user has at least one merged PR.

        Args:
            user_id: User ID

        Returns:
            True if user has merged at least one PR
        """
        return await self.evaluate_pr_count(user_id, 1)

    async def evaluate_badge_criteria(
        self, user_id: str, badge: Badge
    ) -> bool:
        """
        Evaluate if user meets badge criteria.

        Args:
            user_id: User ID
            badge: Badge definition with criteria

        Returns:
            True if user meets all criteria
        """
        criteria = badge.criteria

        if not isinstance(criteria, dict):
            logger.warning(
                "invalid_badge_criteria",
                badge_id=badge.id,
                badge_name=badge.name,
            )
            return False

        criteria_type = criteria.get("type")

        try:
            if criteria_type == "pr_count":
                threshold = criteria.get("threshold", 0)
                return await self.evaluate_pr_count(user_id, threshold)

            elif criteria_type == "quality_rating":
                min_rating = criteria.get("min_rating", 4.0)
                min_prs = criteria.get("min_prs", 10)
                return await self.evaluate_quality_rating(
                    user_id, min_rating, min_prs
                )

            elif criteria_type == "streak":
                months = criteria.get("months", 3)
                return await self.evaluate_streak(user_id, months)

            elif criteria_type == "project_champion":
                project_id = criteria.get("project_id")
                min_percentage = criteria.get("min_percentage", 0.3)
                if not project_id:
                    return False
                return await self.evaluate_project_champion(
                    user_id, project_id, min_percentage
                )

            elif criteria_type == "first_pr":
                return await self.evaluate_first_pr(user_id)

            else:
                logger.warning(
                    "unknown_criteria_type",
                    badge_id=badge.id,
                    criteria_type=criteria_type,
                )
                return False

        except Exception as e:
            logger.error(
                "badge_evaluation_error",
                badge_id=badge.id,
                user_id=user_id,
                error=str(e),
            )
            return False

    async def evaluate_all_badges(self, user_id: str) -> list[Badge]:
        """
        Evaluate all active badges for a user.
        Returns list of badges user qualifies for but hasn't earned yet.

        Args:
            user_id: User ID

        Returns:
            List of badges user qualifies for
        """
        # Get all active badges
        all_badges = await self.db.badge.find_many(where={"isActive": True})

        # Get user's current badges
        user_badges = await self.db.userbadge.find_many(where={"userId": user_id})
        earned_badge_ids = {ub.badgeId for ub in user_badges}

        # Evaluate each badge
        qualifying_badges = []
        for badge in all_badges:
            # Skip if already earned
            if badge.id in earned_badge_ids:
                continue

            # Evaluate criteria
            if await self.evaluate_badge_criteria(user_id, badge):
                qualifying_badges.append(badge)
                logger.debug(
                    "user_qualifies_for_badge",
                    user_id=user_id,
                    badge_id=badge.id,
                    badge_name=badge.name,
                )

        return qualifying_badges

    async def get_badge_progress(
        self, user_id: str, badge: Badge
    ) -> Optional[dict]:
        """
        Get user's progress towards a badge.
        Returns progress information if applicable.

        Args:
            user_id: User ID
            badge: Badge definition

        Returns:
            Progress dictionary or None
        """
        criteria = badge.criteria
        if not isinstance(criteria, dict):
            return None

        criteria_type = criteria.get("type")

        try:
            if criteria_type == "pr_count":
                threshold = criteria.get("threshold", 0)
                current = await self.db.pullrequest.count(
                    where={"authorId": user_id, "status": "MERGED"}
                )
                return {
                    "current": current,
                    "required": threshold,
                    "percentage": min(100, (current / threshold * 100) if threshold > 0 else 0),
                }

            elif criteria_type == "quality_rating":
                min_rating = criteria.get("min_rating", 4.0)
                min_prs = criteria.get("min_prs", 10)

                prs = await self.db.pullrequest.find_many(
                    where={"authorId": user_id, "status": "MERGED"},
                    include={"reviews": True},
                )

                total_rating = 0
                rated_reviews = 0
                for pr in prs:
                    for review in pr.reviews:
                        if review.rating is not None:
                            total_rating += review.rating
                            rated_reviews += 1

                avg_rating = (
                    total_rating / rated_reviews if rated_reviews > 0 else 0
                )

                return {
                    "current_prs": len(prs),
                    "required_prs": min_prs,
                    "current_rating": round(avg_rating, 2),
                    "required_rating": min_rating,
                }

            elif criteria_type == "streak":
                months = criteria.get("months", 3)
                # Calculate current streak (simplified)
                prs = await self.db.pullrequest.find_many(
                    where={"authorId": user_id, "status": "MERGED"},
                    order={"mergedAt": "desc"},
                )

                contribution_months = set()
                for pr in prs:
                    if pr.mergedAt:
                        month_key = pr.mergedAt.strftime("%Y-%m")
                        contribution_months.add(month_key)

                return {
                    "current_months": len(contribution_months),
                    "required_months": months,
                }

            return None

        except Exception as e:
            logger.error(
                "badge_progress_error",
                badge_id=badge.id,
                user_id=user_id,
                error=str(e),
            )
            return None
