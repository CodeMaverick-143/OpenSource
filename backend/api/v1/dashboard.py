"""
Dashboard API endpoints for contributors.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prisma.models import User

from backend.core.dependencies import get_current_active_user
from backend.db.prisma_client import get_db
from backend.schemas.dashboard_schemas import (
    BadgesResponse,
    ContributionGraphResponse,
    DashboardStatsResponse,
    PointsHistoryResponse,
    PRListResponse,
    RankInfoResponse,
    SkillsResponse,
)
from backend.services.contribution_graph_service import ContributionGraphService
from backend.services.dashboard_service import DashboardService
from backend.services.skill_tagger import SkillTagger
from prisma import Prisma

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = structlog.get_logger(__name__)


@router.get("/prs", response_model=PRListResponse)
async def get_user_prs(
    status: str | None = Query(None, description="Filter by PR status"),
    project_id: str | None = Query(None, description="Filter by project ID"),
    repository_id: str | None = Query(None, description="Filter by repository ID"),
    sort_by: str = Query("recent", description="Sort order: recent, score, oldest"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> PRListResponse:
    """
    Get contributor's PRs with filtering, sorting, and pagination.

    Args:
        status: Filter by PR status (OPEN, MERGED, CLOSED, etc.)
        project_id: Filter by project ID
        repository_id: Filter by repository ID
        sort_by: Sort order (recent, score, oldest)
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Paginated PR list
    """
    logger.info(
        "dashboard_prs_requested",
        user_id=current_user.id,
        status=status,
        project_id=project_id,
        repository_id=repository_id,
        sort_by=sort_by,
        page=page,
        limit=limit,
    )

    try:
        service = DashboardService(db)
        result = await service.get_user_prs(
            user_id=current_user.id,
            status=status,
            project_id=project_id,
            repository_id=repository_id,
            sort_by=sort_by,
            page=page,
            limit=limit,
        )

        return PRListResponse(**result)

    except Exception as e:
        logger.exception("dashboard_prs_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch PRs",
        )


@router.get("/points", response_model=PointsHistoryResponse)
async def get_points_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> PointsHistoryResponse:
    """
    Get contributor's points transaction history.

    Args:
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Paginated points history
    """
    logger.info(
        "dashboard_points_requested",
        user_id=current_user.id,
        page=page,
        limit=limit,
    )

    try:
        service = DashboardService(db)
        result = await service.get_points_history(
            user_id=current_user.id,
            page=page,
            limit=limit,
        )

        return PointsHistoryResponse(**result)

    except Exception as e:
        logger.exception("dashboard_points_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch points history",
        )


@router.get("/badges", response_model=BadgesResponse)
async def get_user_badges(
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> BadgesResponse:
    """
    Get contributor's earned and available badges.

    Args:
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Badges response with earned and available badges
    """
    logger.info("dashboard_badges_requested", user_id=current_user.id)

    try:
        service = DashboardService(db)
        result = await service.get_user_badges(user_id=current_user.id)

        return BadgesResponse(**result)

    except Exception as e:
        logger.exception("dashboard_badges_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch badges",
        )


@router.get("/rank", response_model=RankInfoResponse | None)
async def get_user_rank(
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> RankInfoResponse | None:
    """
    Get contributor's rank information.

    Args:
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Rank information or None if rank unavailable
    """
    logger.info("dashboard_rank_requested", user_id=current_user.id)

    try:
        service = DashboardService(db)
        result = await service.get_user_rank_info(user_id=current_user.id)

        if result is None:
            logger.info("rank_unavailable", user_id=current_user.id)
            return None

        return RankInfoResponse(**result)

    except Exception as e:
        logger.exception("dashboard_rank_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch rank information",
        )


@router.get("/contributions", response_model=ContributionGraphResponse)
async def get_contribution_graph(
    range: str = Query("30d", description="Time range: 30d, 90d, all"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> ContributionGraphResponse:
    """
    Get contributor's contribution graph data.

    Args:
        range: Time range (30d, 90d, all)
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Contribution graph with daily counts and statistics
    """
    logger.info("dashboard_contributions_requested", user_id=current_user.id, range=range)

    # Validate range parameter
    if range not in ["30d", "90d", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range parameter. Must be one of: 30d, 90d, all",
        )

    try:
        service = ContributionGraphService(db)
        result = await service.generate_contribution_graph(
            user_id=current_user.id,
            range_type=range,
        )

        return ContributionGraphResponse(**result)

    except Exception as e:
        logger.exception("dashboard_contributions_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch contribution graph",
        )


@router.get("/skills", response_model=SkillsResponse)
async def get_user_skills(
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> SkillsResponse:
    """
    Get contributor's computed skill tags.

    Args:
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Top skill tags weighted by contribution impact
    """
    logger.info("dashboard_skills_requested", user_id=current_user.id)

    try:
        service = SkillTagger(db)
        result = await service.get_top_skills(user_id=current_user.id, limit=10)

        return SkillsResponse(**result)

    except Exception as e:
        logger.exception("dashboard_skills_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch skills",
        )


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> DashboardStatsResponse:
    """
    Get dashboard summary statistics.

    Args:
        current_user: Current authenticated user
        db: Prisma client

    Returns:
        Summary statistics
    """
    logger.info("dashboard_stats_requested", user_id=current_user.id)

    try:
        service = DashboardService(db)
        result = await service.get_dashboard_stats(user_id=current_user.id)

        return DashboardStatsResponse(**result)

    except ValueError as e:
        logger.error("user_not_found", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except Exception as e:
        logger.exception("dashboard_stats_error", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard statistics",
        )
