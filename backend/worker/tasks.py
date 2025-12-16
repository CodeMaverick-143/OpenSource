"""
Celery tasks for background job processing.
"""

import structlog

from backend.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="tasks.example_task")
def example_task(message: str) -> dict:
    """
    Example Celery task demonstrating structured logging.

    Args:
        message: Message to log

    Returns:
        Task result dictionary
    """
    logger.info("example_task_started", message=message)

    # Simulate some work
    result = {"status": "completed", "message": message, "processed": True}

    logger.info("example_task_completed", result=result)

    return result


@celery_app.task(name="tasks.sync_github_webhooks")
def sync_github_webhooks(repo_id: int) -> dict:
    """
    Placeholder task for syncing GitHub webhooks.

    Args:
        repo_id: Repository ID to sync

    Returns:
        Sync result
    """
    logger.info("sync_github_webhooks_started", repo_id=repo_id)

    # TODO: Implement GitHub webhook sync logic

    logger.info("sync_github_webhooks_completed", repo_id=repo_id)

    return {"status": "completed", "repo_id": repo_id}
