"""
PR state machine with valid transitions and lifecycle tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class PRState(str, Enum):
    """Valid PR states."""

    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


class PRStateMachine:
    """
    PR state machine with valid transitions.

    Valid transitions:
    - OPEN → UNDER_REVIEW
    - OPEN → CLOSED
    - UNDER_REVIEW → CHANGES_REQUESTED
    - UNDER_REVIEW → APPROVED
    - UNDER_REVIEW → CLOSED
    - CHANGES_REQUESTED → OPEN (after changes)
    - CHANGES_REQUESTED → CLOSED
    - APPROVED → MERGED
    - APPROVED → CLOSED
    - Any state → OPEN (re-opened)
    """

    # Define valid transitions
    VALID_TRANSITIONS = {
        PRState.OPEN: {PRState.UNDER_REVIEW, PRState.CLOSED},
        PRState.UNDER_REVIEW: {PRState.CHANGES_REQUESTED, PRState.APPROVED, PRState.CLOSED},
        PRState.CHANGES_REQUESTED: {PRState.OPEN, PRState.CLOSED},
        PRState.APPROVED: {PRState.MERGED, PRState.CLOSED},
        PRState.MERGED: set(),  # Terminal state
        PRState.CLOSED: {PRState.OPEN},  # Can be re-opened
    }

    @classmethod
    def is_valid_transition(cls, from_state: str, to_state: str) -> bool:
        """
        Check if state transition is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is valid
        """
        try:
            from_enum = PRState(from_state)
            to_enum = PRState(to_state)

            # Same state is always valid (idempotent)
            if from_enum == to_enum:
                return True

            # Check if transition is allowed
            return to_enum in cls.VALID_TRANSITIONS.get(from_enum, set())

        except ValueError:
            logger.error("invalid_pr_state", from_state=from_state, to_state=to_state)
            return False

    @classmethod
    def get_lifecycle_timestamp_field(cls, state: str) -> Optional[str]:
        """
        Get the lifecycle timestamp field for a state.

        Args:
            state: PR state

        Returns:
            Timestamp field name or None
        """
        timestamp_map = {
            PRState.OPEN: "openedAt",
            PRState.UNDER_REVIEW: "reviewedAt",
            PRState.APPROVED: "approvedAt",
            PRState.MERGED: "mergedAt",
            PRState.CLOSED: "closedAt",
        }

        try:
            state_enum = PRState(state)
            return timestamp_map.get(state_enum)
        except ValueError:
            return None

    @classmethod
    def validate_transition(
        cls, from_state: str, to_state: str, pr_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate state transition and return error message if invalid.

        Args:
            from_state: Current state
            to_state: Target state
            pr_id: PR ID for logging

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not cls.is_valid_transition(from_state, to_state):
            error_msg = f"Invalid state transition: {from_state} → {to_state}"
            logger.warning(
                "invalid_state_transition",
                pr_id=pr_id,
                from_state=from_state,
                to_state=to_state,
            )
            return False, error_msg

        logger.info(
            "valid_state_transition",
            pr_id=pr_id,
            from_state=from_state,
            to_state=to_state,
        )

        return True, None

    @classmethod
    def get_timestamp_updates(cls, to_state: str) -> dict:
        """
        Get timestamp updates for state transition.

        Args:
            to_state: Target state

        Returns:
            Dictionary of timestamp updates
        """
        updates = {}
        timestamp_field = cls.get_lifecycle_timestamp_field(to_state)

        if timestamp_field:
            updates[timestamp_field] = datetime.utcnow()

        return updates

    @classmethod
    def is_terminal_state(cls, state: str) -> bool:
        """
        Check if state is terminal (no further transitions).

        Args:
            state: PR state

        Returns:
            True if terminal state
        """
        try:
            state_enum = PRState(state)
            return state_enum == PRState.MERGED
        except ValueError:
            return False

    @classmethod
    def can_award_points(cls, state: str, event_action: str) -> bool:
        """
        Check if points should be awarded for this state/action.

        Args:
            state: PR state
            event_action: Webhook action (opened, closed, etc.)

        Returns:
            True if points should be awarded
        """
        # Award points on:
        # - PR opened (OPEN state, opened action)
        # - PR merged (MERGED state, closed action with merged=true)
        if state == PRState.OPEN and event_action == "opened":
            return True

        if state == PRState.MERGED and event_action == "closed":
            return True

        return False
