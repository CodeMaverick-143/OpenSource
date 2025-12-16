"""
Celery tasks for review management and timeout detection.
"""

from datetime import datetime, timedelta

import structlog
from celery import shared_task

from backend.db.prisma_client import get_prisma_client
from backend.services.abuse_detector import AbuseDetector
from backend.services.review_conflict_resolver import ReviewConflictResolver
from backend.services.review_notifications import ReviewNotifications

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def detect_review_timeouts(self, timeout_days: int = 7) -> dict:
    """
    Detect PRs stuck in UNDER_REVIEW for too long.

    Args:
        timeout_days: Days before review times out

    Returns:
        Detection result
    """
    logger.info("detecting_review_timeouts", timeout_days=timeout_days, task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def detect():
            cutoff_date = datetime.utcnow() - timedelta(days=timeout_days)

            # Find PRs in UNDER_REVIEW for too long
            stale_reviews = await db.pullrequest.find_many(
                where={
                    "status": "UNDER_REVIEW",
                    "reviewedAt": {"lt": cutoff_date},
                }
            )

            timeout_count = len(stale_reviews)

            # Notify about timeouts
            notifications = ReviewNotifications(db)

            for pr in stale_reviews:
                await notifications.notify_review_timeout(pr.id)

                logger.warning(
                    "review_timeout_detected",
                    pr_id=pr.id,
                    pr_number=pr.prNumber,
                    days_in_review=(datetime.utcnow() - pr.reviewedAt).days,
                )

            return {"timeout_count": timeout_count}

        result = asyncio.run(detect())

        logger.info("review_timeouts_detected", count=result["timeout_count"])

        return result

    except Exception as e:
        logger.error("review_timeout_detection_failed", error=str(e))
        raise


@shared_task(bind=True)
def auto_release_stale_reviews(self, timeout_days: int = 14) -> dict:
    """
    Auto-release PRs stuck in UNDER_REVIEW.

    Args:
        timeout_days: Days before auto-release

    Returns:
        Release result
    """
    logger.info(
        "auto_releasing_stale_reviews", timeout_days=timeout_days, task_id=self.request.id
    )

    try:
        import asyncio

        db = get_prisma_client()

        async def release():
            cutoff_date = datetime.utcnow() - timedelta(days=timeout_days)

            # Find PRs to release
            stale_reviews = await db.pullrequest.find_many(
                where={
                    "status": "UNDER_REVIEW",
                    "reviewedAt": {"lt": cutoff_date},
                }
            )

            released_count = 0

            for pr in stale_reviews:
                # Release back to OPEN
                await db.pullrequest.update(
                    where={"id": pr.id}, data={"status": "OPEN", "reviewedAt": None}
                )

                released_count += 1

                logger.info(
                    "stale_review_released",
                    pr_id=pr.id,
                    pr_number=pr.prNumber,
                )

            return {"released_count": released_count}

        result = asyncio.run(release())

        logger.info("stale_reviews_released", count=result["released_count"])

        return result

    except Exception as e:
        logger.error("stale_review_release_failed", error=str(e))
        raise


@shared_task(bind=True)
def aggregate_review_outcomes(self) -> dict:
    """
    Aggregate review outcomes for PRs with multiple reviews.

    Returns:
        Aggregation result
    """
    logger.info("aggregating_review_outcomes", task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def aggregate():
            # Find PRs with multiple reviews
            prs_with_reviews = await db.pullrequest.find_many(
                where={"status": {"in": ["UNDER_REVIEW", "APPROVED", "CHANGES_REQUESTED"]}},
                include={"reviews": True},
            )

            aggregated_count = 0
            conflict_count = 0

            resolver = ReviewConflictResolver(db)

            for pr in prs_with_reviews:
                if len(pr.reviews) < 2:
                    continue

                # Check for conflicts
                has_conflict = await resolver.detect_conflicts(pr.id)

                if has_conflict:
                    # Resolve conflict
                    await resolver.resolve_conflict(pr.id, resolution_method="MAJORITY")
                    conflict_count += 1

                aggregated_count += 1

            return {"aggregated_count": aggregated_count, "conflict_count": conflict_count}

        result = asyncio.run(aggregate())

        logger.info(
            "review_outcomes_aggregated",
            aggregated=result["aggregated_count"],
            conflicts=result["conflict_count"],
        )

        return result

    except Exception as e:
        logger.error("review_outcome_aggregation_failed", error=str(e))
        raise


@shared_task(bind=True)
def detect_reviewer_abuse(self) -> dict:
    """
    Detect reviewer abuse patterns.

    Returns:
        Detection result
    """
    logger.info("detecting_reviewer_abuse", task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def detect():
            # Get all active reviewers
            reviewers = await db.prreview.find_many(
                where={"createdAt": {"gte": datetime.utcnow() - timedelta(days=30)}},
                distinct=["reviewerId"],
            )

            reviewer_ids = list(set(r.reviewerId for r in reviewers))

            abuse_count = 0
            detector = AbuseDetector(db)

            for reviewer_id in reviewer_ids:
                result = await detector.run_abuse_checks(reviewer_id)

                if result["has_abuse"]:
                    abuse_count += 1

                    logger.warning(
                        "reviewer_abuse_detected",
                        reviewer_id=reviewer_id,
                        checks=result,
                    )

            return {"abuse_count": abuse_count, "reviewers_checked": len(reviewer_ids)}

        result = asyncio.run(detect())

        logger.info(
            "reviewer_abuse_detection_complete",
            abuse_count=result["abuse_count"],
            reviewers_checked=result["reviewers_checked"],
        )

        return result

    except Exception as e:
        logger.error("reviewer_abuse_detection_failed", error=str(e))
        raise
