"""
Review conflict resolver for handling multiple maintainer reviews.
"""

from typing import List, Optional

import structlog
from prisma import Prisma
from prisma.models import PRReview

logger = structlog.get_logger(__name__)


class ReviewConflictResolver:
    """
    Resolve conflicts when multiple maintainers review the same PR.
    """

    def __init__(self, db: Prisma):
        """Initialize resolver."""
        self.db = db

    async def detect_conflicts(self, pr_id: str) -> bool:
        """
        Detect if PR has conflicting reviews.

        Args:
            pr_id: PR ID

        Returns:
            True if conflicts detected
        """
        reviews = await self.db.prreview.find_many(
            where={"pullRequestId": pr_id, "action": {"in": ["APPROVED", "REQUESTED_CHANGES"]}}
        )

        if len(reviews) < 2:
            return False

        # Check for conflicts (both APPROVED and REQUESTED_CHANGES)
        has_approval = any(r.action == "APPROVED" for r in reviews)
        has_changes_requested = any(r.action == "REQUESTED_CHANGES" for r in reviews)

        return has_approval and has_changes_requested

    async def resolve_conflict(
        self,
        pr_id: str,
        resolution_method: str = "MAJORITY",
        resolver_id: Optional[str] = None,
    ) -> dict:
        """
        Resolve review conflict.

        Args:
            pr_id: PR ID
            resolution_method: Resolution method (MAJORITY, OWNER_OVERRIDE, MANUAL)
            resolver_id: User ID who resolved (for OWNER_OVERRIDE/MANUAL)

        Returns:
            Resolution result
        """
        # Get all reviews
        reviews = await self.db.prreview.find_many(
            where={"pullRequestId": pr_id, "action": {"in": ["APPROVED", "REQUESTED_CHANGES"]}},
            include={"reviewer": True},
        )

        if len(reviews) < 2:
            return {"has_conflict": False, "final_outcome": None}

        # Count votes
        approvals = [r for r in reviews if r.action == "APPROVED"]
        changes_requested = [r for r in reviews if r.action == "REQUESTED_CHANGES"]

        final_outcome = None

        if resolution_method == "MAJORITY":
            # Majority-based resolution
            if len(approvals) > len(changes_requested):
                final_outcome = "APPROVED"
            elif len(changes_requested) > len(approvals):
                final_outcome = "CHANGES_REQUESTED"
            else:
                # Tie - default to CHANGES_REQUESTED (conservative)
                final_outcome = "CHANGES_REQUESTED"

        elif resolution_method == "OWNER_OVERRIDE":
            # Owner's decision wins
            if not resolver_id:
                raise ValueError("resolver_id required for OWNER_OVERRIDE")

            # Get PR to find project owner
            pr = await self.db.pullrequest.find_unique(
                where={"id": pr_id}, include={"repository": {"include": {"project": True}}}
            )

            if pr and pr.repository.project.ownerId == resolver_id:
                # Find owner's review
                owner_review = next(
                    (r for r in reviews if r.reviewerId == resolver_id), None
                )

                if owner_review:
                    final_outcome = (
                        "APPROVED"
                        if owner_review.action == "APPROVED"
                        else "CHANGES_REQUESTED"
                    )

        # Create conflict record
        conflict = await self.db.reviewconflict.create(
            data={
                "pullRequestId": pr_id,
                "conflictingReviews": [r.id for r in reviews],
                "resolutionMethod": resolution_method,
                "finalOutcome": final_outcome,
                "resolvedBy": resolver_id,
                "resolvedAt": None if not final_outcome else None,
                "isResolved": final_outcome is not None,
            }
        )

        # Mark conflicting reviews
        for review in reviews:
            await self.db.prreview.update(
                where={"id": review.id}, data={"isConflicting": True}
            )

        logger.info(
            "conflict_resolved",
            pr_id=pr_id,
            resolution_method=resolution_method,
            final_outcome=final_outcome,
            approvals=len(approvals),
            changes_requested=len(changes_requested),
        )

        return {
            "has_conflict": True,
            "final_outcome": final_outcome,
            "approvals": len(approvals),
            "changes_requested": len(changes_requested),
            "resolution_method": resolution_method,
        }

    async def get_conflict_status(self, pr_id: str) -> Optional[dict]:
        """
        Get conflict status for PR.

        Args:
            pr_id: PR ID

        Returns:
            Conflict status or None
        """
        conflict = await self.db.reviewconflict.find_first(
            where={"pullRequestId": pr_id}, order={"createdAt": "desc"}
        )

        if not conflict:
            return None

        return {
            "is_resolved": conflict.isResolved,
            "resolution_method": conflict.resolutionMethod,
            "final_outcome": conflict.finalOutcome,
            "resolved_by": conflict.resolvedBy,
            "resolved_at": conflict.resolvedAt,
        }

    async def aggregate_review_outcome(self, pr_id: str) -> str:
        """
        Aggregate reviews to determine final outcome.

        Args:
            pr_id: PR ID

        Returns:
            Final outcome (APPROVED, CHANGES_REQUESTED, PENDING)
        """
        # Check for existing conflict resolution
        conflict_status = await self.get_conflict_status(pr_id)

        if conflict_status and conflict_status["is_resolved"]:
            return conflict_status["final_outcome"]

        # Get all reviews
        reviews = await self.db.prreview.find_many(
            where={"pullRequestId": pr_id, "action": {"in": ["APPROVED", "REQUESTED_CHANGES"]}}
        )

        if not reviews:
            return "PENDING"

        # Check for conflicts
        has_conflict = await self.detect_conflicts(pr_id)

        if has_conflict:
            # Auto-resolve using majority
            result = await self.resolve_conflict(pr_id, resolution_method="MAJORITY")
            return result["final_outcome"]

        # No conflict - use unanimous decision
        if all(r.action == "APPROVED" for r in reviews):
            return "APPROVED"
        elif all(r.action == "REQUESTED_CHANGES" for r in reviews):
            return "CHANGES_REQUESTED"

        return "PENDING"
