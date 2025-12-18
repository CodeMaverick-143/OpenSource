"""
Advanced scoring engine with rule-based scoring and gaming prevention.
"""

from typing import Dict, Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class ScoringEngine:
    """
    Advanced scoring engine with contribution rules and gaming prevention.
    """

    def __init__(self, db: Prisma):
        """Initialize scoring engine."""
        self.db = db

    async def calculate_pr_score(
        self,
        pr_id: str,
        event_action: str,
        diff_size: Optional[int],
        project_rules: Optional[dict],
    ) -> Dict[str, any]:
        """
        Calculate PR score based on contribution rules.

        Args:
            pr_id: PR ID
            event_action: Webhook action (opened, closed, etc.)
            diff_size: Lines changed
            project_rules: Project contribution rules

        Returns:
            Dictionary with score and metadata
        """
        base_score = 0
        quality_bonus = 0
        metadata = {"event_action": event_action, "diff_size": diff_size}

        # Get base score from rules or use defaults
        if project_rules:
            base_score = self._get_base_score_from_rules(event_action, project_rules)
        else:
            base_score = self._get_default_base_score(event_action)

        # Calculate quality bonus
        if diff_size:
            quality_bonus = self._calculate_quality_bonus(diff_size, project_rules)

        total_score = base_score + quality_bonus

        metadata.update(
            {
                "base_score": base_score,
                "quality_bonus": quality_bonus,
                "total_score": total_score,
            }
        )

        logger.info(
            "pr_score_calculated",
            pr_id=pr_id,
            event_action=event_action,
            base_score=base_score,
            quality_bonus=quality_bonus,
            total_score=total_score,
        )

        return {"score": total_score, "metadata": metadata}

    def _get_base_score_from_rules(self, event_action: str, rules: dict) -> int:
        """Get base score from project contribution rules."""
        # Default scores if not in rules
        default_scores = {"opened": 10, "closed": 50}

        # Check if rules define custom scores
        if "base_points" in rules:
            return rules["base_points"].get(event_action, default_scores.get(event_action, 0))

        return default_scores.get(event_action, 0)

    def _get_default_base_score(self, event_action: str) -> int:
        """Get default base score."""
        default_scores = {"opened": 10, "closed": 50}  # closed = merged
        return default_scores.get(event_action, 0)

    def _calculate_quality_bonus(self, diff_size: int, rules: Optional[dict]) -> int:
        """
        Calculate quality bonus based on diff size.

        Args:
            diff_size: Lines changed
            rules: Project contribution rules

        Returns:
            Quality bonus points
        """
        # Default quality bonus thresholds
        thresholds = {
            100: 20,  # 100+ lines: +20 points
            500: 50,  # 500+ lines: +50 points
            1000: 100,  # 1000+ lines: +100 points
        }

        # Override with rules if provided
        if rules and "quality_bonus_thresholds" in rules:
            thresholds = rules["quality_bonus_thresholds"]

        # Calculate bonus
        bonus = 0
        for threshold, points in sorted(thresholds.items(), reverse=True):
            if diff_size >= threshold:
                bonus = points
                break

        return bonus

    async def apply_gaming_prevention(
        self, user_id: str, repo_id: str, score: int, period_days: int = 30
    ) -> int:
        """
        Apply gaming prevention caps.

        Args:
            user_id: User ID
            repo_id: Repository ID
            score: Calculated score
            period_days: Period for cap calculation

        Returns:
            Capped score
        """
        # Get user's recent points from this repo
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        # Get total points from this repo in period
        transactions = await self.db.pointtransaction.find_many(
            where={
                "userId": user_id,
                "createdAt": {"gte": cutoff_date},
                "pullRequest": {"repositoryId": repo_id},
            }
        )

        total_points_in_period = sum(t.points for t in transactions)

        # Apply diminishing returns if farming detected
        max_points_per_repo_per_month = 1000  # Configurable cap

        if total_points_in_period >= max_points_per_repo_per_month:
            logger.warning(
                "gaming_prevention_cap_reached",
                user_id=user_id,
                repo_id=repo_id,
                total_points=total_points_in_period,
                cap=max_points_per_repo_per_month,
            )
            return 0  # No more points

        # Apply diminishing returns
        remaining_cap = max_points_per_repo_per_month - total_points_in_period
        capped_score = min(score, remaining_cap)

        if capped_score < score:
            logger.info(
                "score_capped_gaming_prevention",
                user_id=user_id,
                repo_id=repo_id,
                original_score=score,
                capped_score=capped_score,
            )

        return capped_score

    async def should_award_points(self, pr_id: str, event_action: str, pr_status: str) -> bool:
        """
        Check if points should be awarded for this event.

        Args:
            pr_id: PR ID
            event_action: Webhook action
            pr_status: PR status

        Returns:
            True if points should be awarded
        """
        # Award points on:
        # 1. PR opened (action=opened, status=OPEN)
        # 2. PR merged (action=closed, status=MERGED)

        if event_action == "opened" and pr_status == "OPEN":
            return True

        if event_action == "closed" and pr_status == "MERGED":
            return True

        return False
