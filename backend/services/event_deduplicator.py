"""
Event deduplicator for preventing double-scoring and handling retries.
"""

import hashlib
from typing import Optional

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class EventDeduplicator:
    """
    Deduplicate webhook events using fingerprints.

    Prevents:
    - Double-scoring on webhook retries
    - Out-of-order event processing issues
    - Duplicate event handling
    """

    def __init__(self, db: Prisma):
        """Initialize deduplicator."""
        self.db = db

    @staticmethod
    def generate_fingerprint(delivery_id: str, event_type: str, action: str, pr_id: int) -> str:
        """
        Generate unique event fingerprint.

        Args:
            delivery_id: GitHub delivery ID
            event_type: Event type (pull_request, etc.)
            action: Event action (opened, closed, etc.)
            pr_id: GitHub PR ID

        Returns:
            Unique fingerprint
        """
        # Create fingerprint from delivery_id + event_type + action + pr_id
        # This ensures uniqueness even if delivery_id is reused
        fingerprint_data = f"{delivery_id}:{event_type}:{action}:{pr_id}"
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:64]

        return fingerprint

    async def is_duplicate_event(
        self, delivery_id: str, event_type: str, action: str, pr_id: int
    ) -> bool:
        """
        Check if event has already been processed.

        Args:
            delivery_id: GitHub delivery ID
            event_type: Event type
            action: Event action
            pr_id: GitHub PR ID

        Returns:
            True if event is duplicate
        """
        fingerprint = self.generate_fingerprint(delivery_id, event_type, action, pr_id)

        # Check if fingerprint exists
        existing = await self.db.webhookdelivery.find_unique(where={"fingerprint": fingerprint})

        if existing:
            logger.info(
                "duplicate_event_detected",
                delivery_id=delivery_id,
                fingerprint=fingerprint,
                processed=existing.processed,
                scoring_applied=existing.scoringApplied,
            )
            return True

        return False

    async def should_apply_scoring(
        self, delivery_id: str, event_type: str, action: str, pr_id: int
    ) -> bool:
        """
        Check if scoring should be applied for this event.

        Args:
            delivery_id: GitHub delivery ID
            event_type: Event type
            action: Event action
            pr_id: GitHub PR ID

        Returns:
            True if scoring should be applied
        """
        fingerprint = self.generate_fingerprint(delivery_id, event_type, action, pr_id)

        # Check if scoring already applied
        existing = await self.db.webhookdelivery.find_unique(where={"fingerprint": fingerprint})

        if existing and existing.scoringApplied:
            logger.info(
                "scoring_already_applied",
                delivery_id=delivery_id,
                fingerprint=fingerprint,
            )
            return False

        return True

    async def mark_scoring_applied(
        self, delivery_id: str, event_type: str, action: str, pr_id: int
    ) -> None:
        """
        Mark scoring as applied for this event.

        Args:
            delivery_id: GitHub delivery ID
            event_type: Event type
            action: Event action
            pr_id: GitHub PR ID
        """
        fingerprint = self.generate_fingerprint(delivery_id, event_type, action, pr_id)

        # Update webhook delivery
        await self.db.webhookdelivery.update(
            where={"fingerprint": fingerprint},
            data={"scoringApplied": True},
        )

        logger.info(
            "scoring_marked_applied",
            delivery_id=delivery_id,
            fingerprint=fingerprint,
        )

    async def get_event_fingerprint(
        self, delivery_id: str, event_type: str, action: str, pr_id: int
    ) -> str:
        """
        Get or create event fingerprint.

        Args:
            delivery_id: GitHub delivery ID
            event_type: Event type
            action: Event action
            pr_id: GitHub PR ID

        Returns:
            Event fingerprint
        """
        return self.generate_fingerprint(delivery_id, event_type, action, pr_id)
