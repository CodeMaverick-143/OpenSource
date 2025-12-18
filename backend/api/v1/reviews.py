"""
Review management API endpoints.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prisma.models import User
from pydantic import BaseModel, Field

from backend.core.dependencies import get_current_active_user
from backend.db.prisma_client import get_db
from backend.services.abuse_detector import AbuseDetector
from backend.services.review_conflict_resolver import ReviewConflictResolver
from backend.services.review_notifications import ReviewNotifications
from backend.services.review_service import ReviewService
from prisma import Prisma

router = APIRouter(tags=["reviews"])
logger = structlog.get_logger(__name__)


# Pydantic schemas
class PRStateTransition(BaseModel):
    """PR state transition request."""

    new_state: str = Field(..., description="Target state")
    internal_comment: str | None = Field(None, description="Internal comment")


class ReviewComment(BaseModel):
    """Review comment request."""

    comment: str = Field(..., description="Comment text")
    is_internal: bool = Field(True, description="Whether comment is internal")


class QualityRating(BaseModel):
    """Quality rating request."""

    rating: int = Field(..., ge=1, le=5, description="Quality rating (1-5)")
    internal_comment: str | None = Field(None, description="Internal comment")


class PRListResponse(BaseModel):
    """PR list response."""

    prs: list
    total: int


@router.get("/prs", response_model=PRListResponse)
async def list_prs_for_review(
    state: str | None = Query(None, description="Filter by state"),
    project_id: str | None = Query(None, description="Filter by project"),
    repository_id: str | None = Query(None, description="Filter by repository"),
    sort_by: str = Query("age", description="Sort by (age, activity, last_updated)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> PRListResponse:
    """List PRs for maintainer's projects."""
    service = ReviewService(db)

    prs, total = await service.list_prs_for_maintainer(
        maintainer_id=current_user.id,
        state_filter=state,
        project_id=project_id,
        repository_id=repository_id,
        sort_by=sort_by,
        skip=skip,
        limit=limit,
    )

    return PRListResponse(prs=prs, total=total)


@router.post("/{pr_id}/transition")
async def transition_pr_state(
    pr_id: str,
    data: PRStateTransition,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """Transition PR to new state."""
    service = ReviewService(db)
    notifications = ReviewNotifications(db)

    pr = await service.transition_pr_state(
        pr_id=pr_id,
        new_state=data.new_state,
        reviewer_id=current_user.id,
        internal_comment=data.internal_comment,
    )

    # Trigger notifications
    if data.new_state == "UNDER_REVIEW":
        await notifications.notify_review_started(pr_id, current_user.id)
    elif data.new_state == "CHANGES_REQUESTED":
        await notifications.notify_changes_requested(pr_id, current_user.id, data.internal_comment)
    elif data.new_state == "APPROVED":
        await notifications.notify_approved(pr_id, current_user.id)

    # Check for conflicts
    resolver = ReviewConflictResolver(db)
    has_conflict = await resolver.detect_conflicts(pr_id)

    if has_conflict:
        await notifications.notify_conflict_detected(pr_id)

    return {"pr": pr, "has_conflict": has_conflict}


@router.post("/{pr_id}/comment")
async def add_review_comment(
    pr_id: str,
    data: ReviewComment,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """Add review comment to PR."""
    service = ReviewService(db)

    comment = await service.add_review_comment(
        pr_id=pr_id,
        reviewer_id=current_user.id,
        comment=data.comment,
        is_internal=data.is_internal,
    )

    return comment


@router.post("/{pr_id}/rate")
async def add_quality_rating(
    pr_id: str,
    data: QualityRating,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """Add quality rating to PR."""
    service = ReviewService(db)

    # Check for abuse before allowing rating
    abuse_detector = AbuseDetector(db)
    abuse_check = await abuse_detector.run_abuse_checks(current_user.id)

    if abuse_check["has_abuse"]:
        logger.warning(
            "rating_blocked_abuse_detected",
            reviewer_id=current_user.id,
            pr_id=pr_id,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rating temporarily blocked due to abuse detection",
        )

    review = await service.add_quality_rating(
        pr_id=pr_id,
        reviewer_id=current_user.id,
        rating=data.rating,
        internal_comment=data.internal_comment,
    )

    return review


@router.get("/{pr_id}/history")
async def get_review_history(
    pr_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """Get review history for PR."""
    service = ReviewService(db)

    history = await service.get_review_history(pr_id=pr_id, requester_id=current_user.id)

    return {"reviews": history}


@router.get("/{pr_id}/conflict")
async def get_conflict_status(
    pr_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """Get conflict status for PR."""
    resolver = ReviewConflictResolver(db)

    conflict_status = await resolver.get_conflict_status(pr_id)

    return {"conflict": conflict_status}


@router.post("/{pr_id}/resolve-conflict")
async def resolve_conflict(
    pr_id: str,
    resolution_method: str = Query("MAJORITY", description="Resolution method"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """Resolve review conflict (owner only for OWNER_OVERRIDE)."""
    resolver = ReviewConflictResolver(db)

    # Check if user is project owner for OWNER_OVERRIDE
    if resolution_method == "OWNER_OVERRIDE":
        pr = await db.pullrequest.find_unique(
            where={"id": pr_id}, include={"repository": {"include": {"project": True}}}
        )

        if not pr or pr.repository.project.ownerId != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owner can use OWNER_OVERRIDE",
            )

    result = await resolver.resolve_conflict(
        pr_id=pr_id,
        resolution_method=resolution_method,
        resolver_id=current_user.id,
    )

    return result
