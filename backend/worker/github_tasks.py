"""
Celery tasks for GitHub integration.
"""

import structlog
from celery import shared_task

from backend.db.prisma_client import get_prisma_client
from backend.integrations.github.webhook_processor import WebhookProcessor

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def process_webhook_async(self, delivery_id: str, event_type: str, payload: dict) -> dict:
    """
    Process GitHub webhook asynchronously.

    Args:
        delivery_id: GitHub delivery ID
        event_type: Event type
        payload: Webhook payload

    Returns:
        Processing result
    """
    logger.info(
        "processing_webhook_async",
        delivery_id=delivery_id,
        event_type=event_type,
        task_id=self.request.id,
    )

    try:
        # Note: Prisma client needs to be initialized in async context
        # This is a simplified version - in production, use async Celery or
        # run Prisma operations in an async event loop
        db = get_prisma_client()
        processor = WebhookProcessor(db)

        # Process webhook
        import asyncio

        result = asyncio.run(processor.process_webhook(delivery_id, event_type, payload))

        logger.info("webhook_async_processing_completed", delivery_id=delivery_id)

        return result

    except Exception as e:
        logger.error(
            "webhook_async_processing_failed",
            delivery_id=delivery_id,
            error=str(e),
            exc_info=True,
        )
        raise


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3)
def sync_repository_prs(self, repository_id: str, owner: str, repo: str) -> dict:
    """
    Sync all PRs for a repository from GitHub.

    Args:
        repository_id: Internal repository ID
        owner: Repository owner
        repo: Repository name

    Returns:
        Sync result
    """
    logger.info(
        "syncing_repository_prs",
        repository_id=repository_id,
        repo=f"{owner}/{repo}",
        task_id=self.request.id,
    )

    # TODO: Implement PR sync logic
    # 1. Get GitHub token for repository
    # 2. Fetch all PRs from GitHub
    # 3. Reconcile with database
    # 4. Update missing/stale PRs

    return {"status": "not_implemented"}


@shared_task(bind=True)
def cleanup_old_webhook_deliveries(self, days: int = 30) -> dict:
    """
    Clean up old processed webhook deliveries.

    Args:
        days: Delete deliveries older than this many days

    Returns:
        Cleanup result
    """
    from datetime import datetime, timedelta

    logger.info("cleaning_up_old_webhooks", days=days, task_id=self.request.id)

    try:
        db = get_prisma_client()
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        import asyncio

        async def cleanup():
            result = await db.webhookdelivery.delete_many(
                where={"processed": True, "receivedAt": {"lt": cutoff_date}}
            )
            return result

        deleted_count = asyncio.run(cleanup())

        logger.info("webhook_cleanup_completed", deleted_count=deleted_count)

        return {"status": "success", "deleted_count": deleted_count}

    except Exception as e:
        logger.error("webhook_cleanup_failed", error=str(e), exc_info=True)
        raise
