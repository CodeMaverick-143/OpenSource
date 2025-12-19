"""
Badges API endpoints.
Provides badge management and viewing capabilities.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.dependencies import get_current_active_user, get_optional_current_user
from backend.db.prisma_client import get_db
from backend.services.badge_evaluator import BadgeEvaluator
from backend.services.badge_service import BadgeService
from prisma import Prisma
from prisma.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/badges")


# ============================================================================
# Request/Response Models
# ============================================================================


class ManualBadgeAwardRequest(BaseModel):
    """Request to manually award a badge."""

    user_id: str
    justification: str
    metadata: Optional[dict] = None


class BadgeRevokeRequest(BaseModel):
    """Request to revoke a badge."""

    user_id: str
    justification: str


# ============================================================================
# Dependencies
# ============================================================================


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Require admin privileges.
    Note: This is a placeholder. Implement proper admin check based on your auth system.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if admin

    Raises:
        HTTPException: If user is not admin
    """
    # TODO: Implement proper admin check
    # For now, we'll check if user has a specific role or permission
    # This should be replaced with your actual admin verification logic

    # Placeholder: Check if user email contains 'admin' or has admin flag
    # In production, use a proper role-based system
    logger.warning(
        "admin_check_placeholder",
        user_id=current_user.id,
        message="Using placeholder admin check - implement proper RBAC",
    )

    # For now, allow all authenticated users for testing
    # TODO: Replace with actual admin check
    return current_user


# ============================================================================
# Public Routes
# ============================================================================


@router.get("")
async def list_badges(
    category: Optional[str] = Query(None, description="Filter by category"),
    rarity: Optional[str] = Query(None, description="Filter by rarity"),
    db: Prisma = Depends(get_db),
):
    """
    List all active badges.

    Args:
        category: Filter by category (MILESTONE, QUALITY, STREAK, SPECIAL)
        rarity: Filter by rarity (COMMON, RARE, EPIC, LEGENDARY)

    Returns:
        List of badges
    """
    # Build where clause
    where = {"isActive": True}
    if category:
        where["category"] = category
    if rarity:
        where["rarity"] = rarity

    badges = await db.badge.find_many(where=where, order={"rarity": "desc"})

    logger.info("badges_listed", count=len(badges), category=category, rarity=rarity)

    return {"badges": badges}


@router.get("/{badge_id}")
async def get_badge(
    badge_id: str,
    db: Prisma = Depends(get_db),
):
    """
    Get badge details.

    Args:
        badge_id: Badge ID

    Returns:
        Badge details
    """
    badge = await db.badge.find_unique(where={"id": badge_id})

    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found",
        )

    # Get award count
    award_count = await db.userbadge.count(where={"badgeId": badge_id})

    logger.info("badge_viewed", badge_id=badge_id, badge_name=badge.name)

    return {"badge": badge, "award_count": award_count}


@router.get("/users/{user_id}")
async def get_user_badges(
    user_id: str,
    db: Prisma = Depends(get_db),
):
    """
    Get badges earned by a user.

    Args:
        user_id: User ID

    Returns:
        List of user badges
    """
    badge_service = BadgeService(db)
    user_badges = await badge_service.get_user_badges(user_id)

    logger.info("user_badges_listed", user_id=user_id, count=len(user_badges))

    return {"badges": user_badges}


@router.get("/{badge_id}/progress")
async def get_badge_progress(
    badge_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    Get user's progress towards a badge.

    Args:
        badge_id: Badge ID

    Returns:
        Progress information
    """
    badge_service = BadgeService(db)
    badge = await badge_service.get_badge_by_id(badge_id)

    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found",
        )

    # Check if already earned
    has_badge = await badge_service.has_badge(current_user.id, badge_id)
    if has_badge:
        return {"earned": True, "progress": None}

    # Get progress
    evaluator = BadgeEvaluator(db)
    progress = await evaluator.get_badge_progress(current_user.id, badge)

    logger.info(
        "badge_progress_viewed",
        user_id=current_user.id,
        badge_id=badge_id,
    )

    return {"earned": False, "progress": progress}


# ============================================================================
# Admin Routes
# ============================================================================


@router.post("/{badge_id}/award")
async def award_badge_manually(
    badge_id: str,
    request: ManualBadgeAwardRequest,
    current_user: User = Depends(require_admin),
    db: Prisma = Depends(get_db),
):
    """
    Manually award a badge to a user (admin only).

    Args:
        badge_id: Badge ID
        request: Award request

    Returns:
        Success message
    """
    badge_service = BadgeService(db)

    try:
        user_badge = await badge_service.award_badge(
            user_id=request.user_id,
            badge_id=badge_id,
            awarded_by=current_user.id,
            metadata=request.metadata,
            justification=request.justification,
        )

        if not user_badge:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has this badge",
            )

        logger.info(
            "badge_manually_awarded",
            badge_id=badge_id,
            user_id=request.user_id,
            awarded_by=current_user.id,
        )

        return {"message": "Badge awarded successfully", "user_badge": user_badge}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{badge_id}/revoke")
async def revoke_badge(
    badge_id: str,
    request: BadgeRevokeRequest,
    current_user: User = Depends(require_admin),
    db: Prisma = Depends(get_db),
):
    """
    Revoke a badge from a user (admin only).

    Args:
        badge_id: Badge ID
        request: Revoke request

    Returns:
        Success message
    """
    badge_service = BadgeService(db)

    success = await badge_service.revoke_badge(
        user_id=request.user_id,
        badge_id=badge_id,
        revoked_by=current_user.id,
        justification=request.justification,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have this badge",
        )

    logger.info(
        "badge_revoked",
        badge_id=badge_id,
        user_id=request.user_id,
        revoked_by=current_user.id,
    )

    return {"message": "Badge revoked successfully"}


@router.get("/admin/distribution")
async def get_badge_distribution(
    current_user: User = Depends(require_admin),
    db: Prisma = Depends(get_db),
):
    """
    Get badge distribution statistics (admin only).

    Returns:
        Badge statistics
    """
    badge_service = BadgeService(db)
    distribution = await badge_service.get_badge_distribution()

    logger.info(
        "badge_distribution_viewed",
        user_id=current_user.id,
    )

    return {"distribution": distribution}


@router.get("/admin/audit")
async def get_badge_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    badge_id: Optional[str] = Query(None, description="Filter by badge ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return"),
    current_user: User = Depends(require_admin),
    db: Prisma = Depends(get_db),
):
    """
    Get badge audit logs (admin only).

    Args:
        user_id: Filter by user ID
        badge_id: Filter by badge ID
        action: Filter by action (AWARDED, REVOKED)
        limit: Maximum logs to return

    Returns:
        Audit logs
    """
    badge_service = BadgeService(db)
    logs = await badge_service.get_badge_audit_logs(
        user_id=user_id,
        badge_id=badge_id,
        action=action,
        limit=limit,
    )

    logger.info(
        "badge_audit_logs_viewed",
        user_id=current_user.id,
        log_count=len(logs),
    )

    return {"logs": logs}
