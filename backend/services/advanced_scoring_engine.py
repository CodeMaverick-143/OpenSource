"""
Advanced scoring engine with versioned rules, multipliers, and penalties.
"""

from datetime import datetime
from typing import Dict, Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class AdvancedScoringEngine:
    """
    Advanced scoring engine with project-specific rules.

    Scoring Formula:
    base_score = rules.base_points[event]
    multipliers = review_rating_multiplier * test_coverage_multiplier * docs_multiplier
    penalties = spam_penalty + low_value_penalty + violation_penalty
    final_score = max(0, (base_score * multipliers) - penalties)
    """

    def __init__(self, db: Prisma):
        """Initialize scoring engine."""
        self.db = db

    async def calculate_score(
        self,
        pr_id: str,
        event: str,
        scoring_rules: Optional[Dict] = None,
    ) -> Dict[str, any]:
        """
        Calculate score for PR based on versioned rules.

        Args:
            pr_id: PR ID
            event: Event type (opened, merged, closed)
            scoring_rules: Project-specific scoring rules

        Returns:
            Score breakdown
        """
        # Get PR with metadata
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id},
            include={
                "repository": {"include": {"project": True}},
                "reviews": True,
            },
        )

        if not pr:
            raise ValueError(f"PR {pr_id} not found")

        # Get scoring rules (project-specific or default)
        rules = scoring_rules or self._get_default_rules()

        # Calculate base score
        base_score = self._get_base_score(event, rules)

        # Calculate multipliers
        multipliers = await self._calculate_multipliers(pr, rules)

        # Calculate penalties
        penalties = await self._calculate_penalties(pr, rules)

        # Calculate final score
        multiplier_product = 1.0
        for multiplier_value in multipliers.values():
            multiplier_product *= multiplier_value

        penalty_sum = sum(penalties.values())
        final_score = max(0, int((base_score * multiplier_product) - penalty_sum))

        # Generate breakdown
        breakdown = {
            "base_score": base_score,
            "multipliers": multipliers,
            "penalties": penalties,
            "final_score": final_score,
            "event": event,
            "rules_version": rules.get("version", 1),
        }

        logger.info(
            "score_calculated",
            pr_id=pr_id,
            event=event,
            base_score=base_score,
            final_score=final_score,
        )

        return breakdown

    def _get_base_score(self, event: str, rules: Dict) -> int:
        """Get base score from rules."""
        base_points = rules.get("base_points", {})

        default_points = {"opened": 10, "merged": 50, "closed": 0}

        return base_points.get(event, default_points.get(event, 0))

    async def _calculate_multipliers(self, pr, rules: Dict) -> Dict[str, float]:
        """Calculate score multipliers."""
        multipliers = {}

        # Review rating multiplier
        if pr.reviews:
            avg_rating = sum(r.rating for r in pr.reviews if r.rating) / len(
                [r for r in pr.reviews if r.rating]
            )
            multipliers["review_rating"] = self._get_review_rating_multiplier(avg_rating, rules)
        else:
            multipliers["review_rating"] = 1.0

        # Test coverage multiplier (heuristic: check if diff includes test files)
        # This would require analyzing the PR diff, for now use placeholder
        multipliers["test_coverage"] = 1.0

        # Documentation multiplier (heuristic: check if diff includes docs)
        multipliers["documentation"] = 1.0

        return multipliers

    def _get_review_rating_multiplier(self, avg_rating: float, rules: Dict) -> float:
        """Get review rating multiplier."""
        rating_multipliers = rules.get("multipliers", {}).get(
            "review_rating",
            {
                5: 1.5,
                4: 1.2,
                3: 1.0,
                2: 0.8,
                1: 0.5,
            },
        )

        # Find closest rating
        closest_rating = min(rating_multipliers.keys(), key=lambda x: abs(x - avg_rating))

        return rating_multipliers[closest_rating]

    async def _calculate_penalties(self, pr, rules: Dict) -> Dict[str, int]:
        """Calculate score penalties."""
        penalties = {}

        # Spam penalty (very small diff)
        if pr.diffSize and pr.diffSize < 10:
            penalties["spam"] = rules.get("penalties", {}).get("spam", 20)
        else:
            penalties["spam"] = 0

        # Low-value penalty (whitespace-only, typo-only)
        # This would require analyzing the PR diff
        penalties["low_value"] = 0

        # Violation penalty
        penalties["violation"] = 0

        return penalties

    def _get_default_rules(self) -> Dict:
        """Get default scoring rules."""
        return {
            "version": 1,
            "base_points": {"opened": 10, "merged": 50, "closed": 0},
            "multipliers": {
                "review_rating": {5: 1.5, 4: 1.2, 3: 1.0, 2: 0.8, 1: 0.5},
                "test_coverage": {True: 1.2, False: 1.0},
                "documentation": {True: 1.1, False: 1.0},
            },
            "penalties": {"spam": 20, "low_value": 10, "violation": 50},
        }

    async def should_score_pr(self, pr_id: str, event: str) -> bool:
        """
        Check if PR should be scored for this event.

        Args:
            pr_id: PR ID
            event: Event type

        Returns:
            True if should score
        """
        # Score only on merge or final close
        if event not in ["merged", "closed"]:
            return False

        # Check if already scored
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id}, include={"transactions": True}
        )

        if not pr:
            return False

        # Check if already has scoring transaction for this event
        has_transaction = any(t.reason == f"PR_{event.upper()}" for t in pr.transactions)

        return not has_transaction
