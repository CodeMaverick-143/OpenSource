"""Worker module initialization."""

from backend.worker.celery_app import celery_app
from backend.worker.tasks import example_task, sync_github_webhooks

__all__ = ["celery_app", "example_task", "sync_github_webhooks"]
