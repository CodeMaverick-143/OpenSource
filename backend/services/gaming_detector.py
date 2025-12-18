"""
Gaming detection for preventing abuse and farming.
"""

from datetime import datetime, timedelta
from typing import Dict

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class GamingDetector:
    """
    Detect and prevent gaming patterns.

    Detection Rules:
    - Spam: diff_size < 10 AND no test changes
    - Frequency: > 10 PRs in 24 hours to same repo
    - Farming: > 500 points from same repo in 30 days
    - Low-Value: Only whitespace or single-char changes
    """

    def __init__(self, db: Prisma):
        """Initialize detector."""
        self.db = db

    async def detect_spam_pr(self, pr_id: str) -> Dict[str, any]:
        """
        Detect if PR is spam (very small diff, whitespace-only).

        Args:
            pr_id: PR ID

        Returns:
            Detection result
        """
        pr = await self.db.pullrequest.find_unique(where={"id": pr_id})

        if not pr:
            return {"is_spam": False, "reason": None}

        # Check diff size
        if pr.diffSize and pr.diffSize < 10:
            logger.warning(
                "spam_pr_detected_small_diff",
                pr_id=pr_id,
                diff_size=pr.diffSize,
            )
            return {"is_spam": True, "reason": "Very small diff size"}

        return {"is_spam": False, "reason": None}

    async def detect_frequency_abuse(
        self, user_id: str, repo_id: str, threshold: int = 10
    ) -> Dict[str, any]:
        """
        Detect if user is submitting too many PRs to same repo.

        Args:
            user_id: User ID
            repo_id: Repository ID
            threshold: Max PRs per 24 hours

        Returns:
            Detection result
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)

        prs = await self.db.pullrequest.find_many(
            where={
                "authorId": user_id,
                "repositoryId": repo_id,
                "createdAt": {"gte": cutoff},
            }
        )

        count = len(prs)
        exceeds_limit = count > threshold

        if exceeds_limit:
            logger.warning(
                "frequency_abuse_detected",
                user_id=user_id,
                repo_id=repo_id,
                count=count,
                threshold=threshold,
            )

        return {
            "exceeds_limit": exceeds_limit,
            "count": count,
            "threshold": threshold,
        }

    async def detect_repo_farming(
        self, user_id: str, repo_id: str, max_points: int = 500
    ) -> Dict[str, any]:
        """
        Detect if user is farming points from same repo.

        Args:
            user_id: User ID
            repo_id: Repository ID
            max_points: Max points per repo per month

        Returns:
            Detection result
        """
        cutoff = datetime.utcnow() - timedelta(days=30)

        # Get points from this repo in last 30 days
        transactions = await self.db.pointtransaction.find_many(
            where={
                "userId": user_id,
                "createdAt": {"gte": cutoff},
                "pullRequest": {"repositoryId": repo_id},
            }
        )

        total_points = sum(t.points for t in transactions)
        exceeds_cap = total_points >= max_points

        if exceeds_cap:
            logger.warning(
                "repo_farming_detected",
                user_id=user_id,
                repo_id=repo_id,
                total_points=total_points,
                cap=max_points,
            )

        return {
            "exceeds_cap": exceeds_cap,
            "total_points": total_points,
            "cap": max_points,
            "remaining": max(0, max_points - total_points),
        }

    async def detect_low_value_pr(self, pr_id: str) -> Dict[str, any]:
        """
        Detect if PR is low-value (typo-only, whitespace-only).

        Args:
            pr_id: PR ID

        Returns:
            Detection result
        """
        # This would require analyzing the PR diff
        # For now, use heuristic based on diff size and title
        pr = await self.db.pullrequest.find_unique(where={"id": pr_id})

        if not pr:
            return {"is_low_value": False, "reason": None}

        # Check for common low-value patterns in title
        low_value_keywords = ["typo", "whitespace", "formatting", "fix typo"]

        title_lower = pr.title.lower()
        has_low_value_keyword = any(kw in title_lower for kw in low_value_keywords)

        if has_low_value_keyword and pr.diffSize and pr.diffSize < 20:
            logger.info(
                "low_value_pr_detected",
                pr_id=pr_id,
                title=pr.title,
                diff_size=pr.diffSize,
            )
            return {"is_low_value": True, "reason": "Low-value change (typo/formatting)"}

        return {"is_low_value": False, "reason": None}

    async def run_all_checks(self, pr_id: str, user_id: str, repo_id: str) -> Dict[str, any]:
        """
        Run all gaming detection checks.

        Args:
            pr_id: PR ID
            user_id: User ID
            repo_id: Repository ID

        Returns:
            Combined detection results
        """
        spam_check = await self.detect_spam_pr(pr_id)
        frequency_check = await self.detect_frequency_abuse(user_id, repo_id)
        farming_check = await self.detect_repo_farming(user_id, repo_id)
        low_value_check = await self.detect_low_value_pr(pr_id)

        has_gaming = (
            spam_check["is_spam"]
            or frequency_check["exceeds_limit"]
            or farming_check["exceeds_cap"]
            or low_value_check["is_low_value"]
        )

        if has_gaming:
            logger.warning(
                "gaming_detected",
                pr_id=pr_id,
                user_id=user_id,
                repo_id=repo_id,
                spam=spam_check["is_spam"],
                frequency_abuse=frequency_check["exceeds_limit"],
                repo_farming=farming_check["exceeds_cap"],
                low_value=low_value_check["is_low_value"],
            )

        return {
            "has_gaming": has_gaming,
            "spam": spam_check,
            "frequency": frequency_check,
            "farming": farming_check,
            "low_value": low_value_check,
        }

    async def calculate_penalty(self, gaming_result: Dict) -> int:
        """
        Calculate penalty based on gaming detection.

        Args:
            gaming_result: Result from run_all_checks

        Returns:
            Penalty points
        """
        penalty = 0

        if gaming_result["spam"]["is_spam"]:
            penalty += 20

        if gaming_result["frequency"]["exceeds_limit"]:
            penalty += 30

        if gaming_result["farming"]["exceeds_cap"]:
            # Cap score to remaining allowance
            penalty += 1000  # Effectively zero out the score

        if gaming_result["low_value"]["is_low_value"]:
            penalty += 15

        return penalty
