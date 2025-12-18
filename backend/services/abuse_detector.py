"""
Reviewer abuse detection for preventing spam and manipulation.
"""

from datetime import datetime, timedelta
from typing import Dict, List

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class AbuseDetector:
    """
    Detect reviewer abuse patterns.
    """

    def __init__(self, db: Prisma):
        """Initialize detector."""
        self.db = db

    async def check_review_frequency(
        self, reviewer_id: str, max_per_day: int = 50
    ) -> Dict[str, any]:
        """
        Check if reviewer exceeds frequency limit.

        Args:
            reviewer_id: Reviewer user ID
            max_per_day: Maximum reviews per day

        Returns:
            Check result
        """
        # Get reviews in last 24 hours
        cutoff = datetime.utcnow() - timedelta(days=1)

        reviews = await self.db.prreview.find_many(
            where={"reviewerId": reviewer_id, "createdAt": {"gte": cutoff}}
        )

        count = len(reviews)
        exceeds_limit = count > max_per_day

        if exceeds_limit:
            logger.warning(
                "review_frequency_limit_exceeded",
                reviewer_id=reviewer_id,
                count=count,
                limit=max_per_day,
            )

        return {"exceeds_limit": exceeds_limit, "count": count, "limit": max_per_day}

    async def detect_spam_rejections(
        self, reviewer_id: str, threshold: float = 0.8
    ) -> Dict[str, any]:
        """
        Detect if reviewer has high rejection rate (spam).

        Args:
            reviewer_id: Reviewer user ID
            threshold: Rejection rate threshold (0.0-1.0)

        Returns:
            Detection result
        """
        # Get last 30 days of reviews
        cutoff = datetime.utcnow() - timedelta(days=30)

        reviews = await self.db.prreview.find_many(
            where={
                "reviewerId": reviewer_id,
                "createdAt": {"gte": cutoff},
                "action": {"in": ["APPROVED", "REQUESTED_CHANGES"]},
            }
        )

        if len(reviews) < 10:
            # Not enough data
            return {"is_spam": False, "rejection_rate": 0.0, "sample_size": len(reviews)}

        rejections = [r for r in reviews if r.action == "REQUESTED_CHANGES"]
        rejection_rate = len(rejections) / len(reviews)

        is_spam = rejection_rate > threshold

        if is_spam:
            logger.warning(
                "spam_rejections_detected",
                reviewer_id=reviewer_id,
                rejection_rate=rejection_rate,
                threshold=threshold,
            )

        return {
            "is_spam": is_spam,
            "rejection_rate": rejection_rate,
            "threshold": threshold,
            "sample_size": len(reviews),
        }

    async def detect_targeted_blocking(
        self, reviewer_id: str, contributor_id: str, threshold: int = 3
    ) -> Dict[str, any]:
        """
        Detect if reviewer repeatedly rejects same contributor.

        Args:
            reviewer_id: Reviewer user ID
            contributor_id: Contributor user ID
            threshold: Number of rejections to trigger

        Returns:
            Detection result
        """
        # Get reviews for this contributor
        reviews = await self.db.prreview.find_many(
            where={
                "reviewerId": reviewer_id,
                "pullRequest": {"authorId": contributor_id},
                "action": "REQUESTED_CHANGES",
            }
        )

        count = len(reviews)
        is_targeted = count >= threshold

        if is_targeted:
            logger.warning(
                "targeted_blocking_detected",
                reviewer_id=reviewer_id,
                contributor_id=contributor_id,
                rejection_count=count,
            )

        return {"is_targeted": is_targeted, "rejection_count": count, "threshold": threshold}

    async def detect_rating_manipulation(
        self, reviewer_id: str, threshold: float = 0.9
    ) -> Dict[str, any]:
        """
        Detect if reviewer always gives extreme ratings (1 or 5).

        Args:
            reviewer_id: Reviewer user ID
            threshold: Extreme rating threshold (0.0-1.0)

        Returns:
            Detection result
        """
        # Get reviews with ratings
        reviews = await self.db.prreview.find_many(
            where={"reviewerId": reviewer_id, "rating": {"not": None}}
        )

        if len(reviews) < 10:
            # Not enough data
            return {
                "is_manipulation": False,
                "extreme_rate": 0.0,
                "sample_size": len(reviews),
            }

        # Count extreme ratings (1 or 5)
        extreme_ratings = [r for r in reviews if r.rating in [1, 5]]
        extreme_rate = len(extreme_ratings) / len(reviews)

        is_manipulation = extreme_rate > threshold

        if is_manipulation:
            logger.warning(
                "rating_manipulation_detected",
                reviewer_id=reviewer_id,
                extreme_rate=extreme_rate,
                threshold=threshold,
            )

        return {
            "is_manipulation": is_manipulation,
            "extreme_rate": extreme_rate,
            "threshold": threshold,
            "sample_size": len(reviews),
        }

    async def run_abuse_checks(self, reviewer_id: str) -> Dict[str, any]:
        """
        Run all abuse checks for reviewer.

        Args:
            reviewer_id: Reviewer user ID

        Returns:
            Combined abuse check results
        """
        frequency_check = await self.check_review_frequency(reviewer_id)
        spam_check = await self.detect_spam_rejections(reviewer_id)
        rating_check = await self.detect_rating_manipulation(reviewer_id)

        has_abuse = (
            frequency_check["exceeds_limit"]
            or spam_check["is_spam"]
            or rating_check["is_manipulation"]
        )

        if has_abuse:
            logger.warning(
                "abuse_detected",
                reviewer_id=reviewer_id,
                frequency_exceeded=frequency_check["exceeds_limit"],
                is_spam=spam_check["is_spam"],
                rating_manipulation=rating_check["is_manipulation"],
            )

        return {
            "has_abuse": has_abuse,
            "frequency": frequency_check,
            "spam": spam_check,
            "rating_manipulation": rating_check,
        }
