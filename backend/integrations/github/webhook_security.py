"""
GitHub webhook signature verification and payload validation.
"""

import hashlib
import hmac
from typing import Optional

import structlog

from backend.core.config import settings

logger = structlog.get_logger(__name__)


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""

    pass


def verify_webhook_signature(payload: bytes, signature_header: str) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256.
    Uses constant-time comparison to prevent timing attacks.

    Args:
        payload: Raw request body
        signature_header: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid

    Raises:
        WebhookVerificationError: If signature is invalid or missing
    """
    if not signature_header:
        logger.warning("webhook_signature_missing")
        raise WebhookVerificationError("Missing signature header")

    if not signature_header.startswith("sha256="):
        logger.warning("webhook_signature_invalid_format")
        raise WebhookVerificationError("Invalid signature format")

    # Extract signature from header
    provided_signature = signature_header.split("=", 1)[1]

    # Calculate expected signature
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    expected_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    # Constant-time comparison
    is_valid = hmac.compare_digest(provided_signature, expected_signature)

    if not is_valid:
        logger.warning("webhook_signature_mismatch")
        raise WebhookVerificationError("Signature verification failed")

    logger.debug("webhook_signature_verified")
    return True


def parse_webhook_event(headers: dict) -> tuple[str, Optional[str]]:
    """
    Parse webhook event type and action from headers.

    Args:
        headers: Request headers

    Returns:
        Tuple of (event_type, action)
    """
    event_type = headers.get("x-github-event", "")
    # Action is in the payload, not headers
    return event_type, None


def get_delivery_id(headers: dict) -> str:
    """
    Extract webhook delivery ID from headers.

    Args:
        headers: Request headers

    Returns:
        Delivery ID

    Raises:
        ValueError: If delivery ID is missing
    """
    delivery_id = headers.get("x-github-delivery")
    if not delivery_id:
        raise ValueError("Missing X-GitHub-Delivery header")

    return delivery_id
