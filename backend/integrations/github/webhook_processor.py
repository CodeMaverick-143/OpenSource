"""
Webhook processor with idempotency and out-of-order event handling.
"""

from datetime import datetime
from typing import Optional

import structlog

from backend.integrations.github.webhook_handlers import get_handler
from prisma import Prisma

logger = structlog.get_logger(__name__)


class WebhookProcessor:
    """
    Process GitHub webhooks with idempotency guarantees.
    """

    def __init__(self, db: Prisma):
        """Initialize processor with database client."""
        self.db = db

    async def process_webhook(self, delivery_id: str, event_type: str, payload: dict) -> dict:
        """
        Process webhook with idempotency.

        Args:
            delivery_id: GitHub delivery ID
            event_type: Event type (pull_request, push, etc.)
            payload: Webhook payload

        Returns:
            Processing result
        """
        # Check if already processed (idempotency)
        existing = await self.db.webhookdelivery.find_unique(where={"deliveryId": delivery_id})

        if existing:
            if existing.processed:
                logger.info(
                    "webhook_already_processed",
                    delivery_id=delivery_id,
                    processed_at=existing.processedAt.isoformat() if existing.processedAt else None,
                )
                return {"status": "already_processed", "delivery_id": delivery_id}

            # Reprocessing failed delivery
            logger.info("reprocessing_failed_webhook", delivery_id=delivery_id)

        # Store webhook delivery
        action = payload.get("action")
        repo_data = payload.get("repository", {})
        github_repo_id = repo_data.get("id") if repo_data else None

        if not existing:
            await self.db.webhookdelivery.create(
                data={
                    "deliveryId": delivery_id,
                    "eventType": event_type,
                    "action": action,
                    "repositoryId": str(github_repo_id) if github_repo_id else None,
                    "payload": payload,
                    "processed": False,
                }
            )

        # Get handler
        handler = get_handler(event_type, self.db)
        if not handler:
            logger.warning("no_handler_for_event", event_type=event_type)
            await self._mark_processed(delivery_id, error="No handler for event type")
            return {"status": "no_handler", "event_type": event_type}

        # Process event
        try:
            await handler.handle(payload)

            # Mark as processed
            await self._mark_processed(delivery_id)

            logger.info("webhook_processed_successfully", delivery_id=delivery_id)

            return {"status": "processed", "delivery_id": delivery_id}

        except Exception as e:
            logger.error(
                "webhook_processing_failed",
                delivery_id=delivery_id,
                error=str(e),
                exc_info=True,
            )

            # Update failure count
            if existing:
                await self.db.webhookdelivery.update(
                    where={"deliveryId": delivery_id},
                    data={
                        "failureCount": {"increment": 1},
                        "lastError": str(e),
                    },
                )
            else:
                await self.db.webhookdelivery.update(
                    where={"deliveryId": delivery_id},
                    data={
                        "failureCount": 1,
                        "lastError": str(e),
                    },
                )

            return {"status": "failed", "error": str(e)}

    async def _mark_processed(self, delivery_id: str, error: Optional[str] = None) -> None:
        """Mark webhook as processed."""
        await self.db.webhookdelivery.update(
            where={"deliveryId": delivery_id},
            data={
                "processed": True,
                "processedAt": datetime.utcnow(),
                "lastError": error,
            },
        )
