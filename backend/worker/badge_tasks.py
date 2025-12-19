"""
Celery tasks for badge evaluation and auto-award.
Triggered on PR merge, score update, and monthly snapshots.
"""

import structlog

from backend.db.prisma_client import get_prisma_client
from backend.services.badge_evaluator import BadgeEvaluator
from backend.services.badge_service import BadgeService
from backend.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def evaluate_user_badges(self, user_id: str) -> dict:
    """
    Evaluate all badges for a user and auto-award qualifying badges.
    This task is idempotent and safe to re-run.

    Args:
        user_id: User ID to evaluate

    Returns:
        Dictionary with evaluation results
    """
    try:
        logger.info("badge_evaluation_started", user_id=user_id)

        # Get Prisma client
        db = get_prisma_client()

        # Initialize services
        evaluator = BadgeEvaluator(db)
        badge_service = BadgeService(db)

        # Evaluate all badges
        qualifying_badges = []
        awarded_badges = []

        # Get all qualifying badges
        qualifying = evaluator.evaluate_all_badges(user_id)

        for badge in qualifying:
            qualifying_badges.append(badge.name)

            # Award badge
            user_badge = badge_service.award_badge(
                user_id=user_id,
                badge_id=badge.id,
                awarded_by=None,  # Auto-award
                metadata={"trigger": "auto_evaluation"},
            )

            if user_badge:
                awarded_badges.append(badge.name)
                logger.info(
                    "badge_auto_awarded",
                    user_id=user_id,
                    badge_id=badge.id,
                    badge_name=badge.name,
                )

        logger.info(
            "badge_evaluation_completed",
            user_id=user_id,
            qualifying_count=len(qualifying_badges),
            awarded_count=len(awarded_badges),
        )

        return {
            "user_id": user_id,
            "qualifying_badges": qualifying_badges,
            "awarded_badges": awarded_badges,
            "success": True,
        }

    except Exception as e:
        logger.error(
            "badge_evaluation_error",
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )

        # Retry on failure
        raise self.retry(exc=e, countdown=60)


@celery_app.task
def evaluate_all_users_badges() -> dict:
    """
    Evaluate badges for all active users.
    Typically run as a monthly scheduled task.

    Returns:
        Dictionary with evaluation summary
    """
    try:
        logger.info("batch_badge_evaluation_started")

        # Get Prisma client
        db = get_prisma_client()

        # Get all active users
        users = db.user.find_many(
            where={"isBanned": False, "isDeleted": False},
            select={"id": True},
        )

        total_users = len(users)
        processed = 0

        # Queue evaluation for each user
        for user in users:
            evaluate_user_badges.delay(user.id)
            processed += 1

        logger.info(
            "batch_badge_evaluation_queued",
            total_users=total_users,
            processed=processed,
        )

        return {
            "total_users": total_users,
            "queued": processed,
            "success": True,
        }

    except Exception as e:
        logger.error(
            "batch_badge_evaluation_error",
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
def evaluate_badges_for_pr_merge(pr_id: str) -> dict:
    """
    Evaluate badges when a PR is merged.
    Triggered by PR merge webhook.

    Args:
        pr_id: Pull request ID

    Returns:
        Dictionary with evaluation results
    """
    try:
        logger.info("pr_merge_badge_evaluation_started", pr_id=pr_id)

        # Get Prisma client
        db = get_prisma_client()

        # Get PR to find author
        pr = db.pullrequest.find_unique(where={"id": pr_id})

        if not pr:
            logger.warning("pr_not_found_for_badge_evaluation", pr_id=pr_id)
            return {"success": False, "error": "PR not found"}

        # Evaluate badges for PR author
        evaluate_user_badges.delay(pr.authorId)

        logger.info(
            "pr_merge_badge_evaluation_queued",
            pr_id=pr_id,
            user_id=pr.authorId,
        )

        return {
            "pr_id": pr_id,
            "user_id": pr.authorId,
            "success": True,
        }

    except Exception as e:
        logger.error(
            "pr_merge_badge_evaluation_error",
            pr_id=pr_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }
