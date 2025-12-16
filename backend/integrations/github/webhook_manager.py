"""
GitHub webhook manager for creating and managing webhooks.
"""

from typing import Optional

import structlog

from backend.core.config import settings
from backend.integrations.github.rest_client import GitHubAPIError, GitHubRESTClient

logger = structlog.get_logger(__name__)


class WebhookManager:
    """Manager for GitHub webhooks."""

    def __init__(self, access_token: str):
        """
        Initialize webhook manager.

        Args:
            access_token: GitHub access token
        """
        self.access_token = access_token

    async def create_webhook(self, owner: str, repo: str, webhook_url: str) -> dict:
        """
        Create webhook for repository.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_url: Webhook URL

        Returns:
            Webhook data

        Raises:
            GitHubAPIError: If webhook creation fails
        """
        async with GitHubRESTClient(self.access_token) as client:
            # Webhook configuration
            webhook_config = {
                "name": "web",
                "active": True,
                "events": ["pull_request", "push", "repository"],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": settings.GITHUB_WEBHOOK_SECRET,
                    "insecure_ssl": "0",
                },
            }

            try:
                webhook_data, _ = await client.post(
                    f"/repos/{owner}/{repo}/hooks", json=webhook_config
                )

                logger.info(
                    "webhook_created",
                    owner=owner,
                    repo=repo,
                    webhook_id=webhook_data.get("id"),
                )

                return webhook_data

            except GitHubAPIError as e:
                logger.error(
                    "webhook_creation_failed",
                    owner=owner,
                    repo=repo,
                    error=e.message,
                )
                raise

    async def get_webhook(self, owner: str, repo: str, webhook_id: int) -> Optional[dict]:
        """
        Get webhook by ID.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_id: Webhook ID

        Returns:
            Webhook data or None
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                webhook_data, _ = await client.get(f"/repos/{owner}/{repo}/hooks/{webhook_id}")
                return webhook_data

            except GitHubAPIError as e:
                if e.status_code == 404:
                    return None
                raise

    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> bool:
        """
        Delete webhook.

        Args:
            owner: Repository owner
            repo: Repository name
            webhook_id: Webhook ID

        Returns:
            True if deleted successfully
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                await client._request("DELETE", f"/repos/{owner}/{repo}/hooks/{webhook_id}")

                logger.info(
                    "webhook_deleted",
                    owner=owner,
                    repo=repo,
                    webhook_id=webhook_id,
                )

                return True

            except GitHubAPIError as e:
                logger.error(
                    "webhook_deletion_failed",
                    owner=owner,
                    repo=repo,
                    webhook_id=webhook_id,
                    error=e.message,
                )
                return False

    async def list_webhooks(self, owner: str, repo: str) -> list[dict]:
        """
        List all webhooks for repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of webhooks
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                webhooks, _ = await client.get(f"/repos/{owner}/{repo}/hooks")
                return webhooks if isinstance(webhooks, list) else []

            except GitHubAPIError as e:
                logger.error(
                    "webhook_list_failed",
                    owner=owner,
                    repo=repo,
                    error=e.message,
                )
                return []
