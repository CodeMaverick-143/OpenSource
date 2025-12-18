"""
GitHub webhook API endpoint.
"""

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from backend.db.prisma_client import get_db
from backend.integrations.github.webhook_processor import WebhookProcessor
from backend.integrations.github.webhook_security import (
    WebhookVerificationError,
    get_delivery_id,
    parse_webhook_event,
    verify_webhook_signature,
)
from prisma import Prisma

router = APIRouter(tags=["webhooks"])
logger = structlog.get_logger(__name__)


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    db: Prisma = Depends(get_db),
) -> dict:
    """
    GitHub webhook endpoint.

    Handles:
    - pull_request events
    - push events
    - repository events

    Security:
    - HMAC-SHA256 signature verification
    - Delivery ID tracking for idempotency

    Returns:
        202 Accepted with processing status
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    try:
        verify_webhook_signature(body, x_hub_signature_256)
    except WebhookVerificationError as e:
        logger.error("webhook_signature_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("webhook_payload_parse_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Validate event type
    supported_events = ["pull_request", "push", "repository"]
    if x_github_event not in supported_events:
        logger.warning("unsupported_webhook_event", event_type=x_github_event)
        return {
            "status": "ignored",
            "reason": "Unsupported event type",
            "event_type": x_github_event,
        }

    # Log webhook receipt
    logger.info(
        "webhook_received",
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        action=payload.get("action"),
        correlation_id=x_github_delivery,
    )

    # Process webhook (idempotent)
    processor = WebhookProcessor(db)
    try:
        result = await processor.process_webhook(x_github_delivery, x_github_event, payload)

        logger.info(
            "webhook_processing_completed",
            delivery_id=x_github_delivery,
            status=result.get("status"),
        )

        return result

    except Exception as e:
        logger.error(
            "webhook_processing_error",
            delivery_id=x_github_delivery,
            error=str(e),
            exc_info=True,
        )

        # Return 202 even on error (webhook will be retried by GitHub)
        return {
            "status": "error",
            "error": str(e),
            "delivery_id": x_github_delivery,
        }
