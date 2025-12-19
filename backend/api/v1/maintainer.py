"""
Maintainer dashboard API endpoints.
Provides maintainers with project management capabilities.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.dependencies import get_current_active_user
from backend.db.prisma_client import get_db
from backend.services.maintainer_dashboard_service import MaintainerDashboardService
from backend.services.maintainer_service import MaintainerService
from prisma import Prisma
from prisma.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/maintainer")


# ============================================================================
# Request/Response Models
# ============================================================================


class InternalCommentRequest(BaseModel):
    """Request to add internal comment."""

    comment: str


class PRListResponse(BaseModel):
    """Response for PR list."""

    prs: list
    total: int
    page: int
    page_size: int


# ============================================================================
# Dependencies
# ============================================================================


async def require_maintainer_access(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> User:
    """
    Verify user has maintainer access to project.

    Args:
        project_id: Project ID
        current_user: Current authenticated user
        db: Database client

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user is not maintainer
    """
    dashboard_service = MaintainerDashboardService(db)
    has_access = await dashboard_service.check_maintainer_access(
        current_user.id, project_id
    )

    if not has_access:
        logger.warning(
            "unauthorized_maintainer_access",
            user_id=current_user.id,
            project_id=project_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have maintainer access to this project",
        )

    return current_user


# ============================================================================
# Routes
# ============================================================================


@router.get("/projects")
async def list_maintainer_projects(
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    List projects where user is maintainer or owner.

    Returns:
        List of projects with basic info
    """
    maintainer_service = MaintainerService(db)
    project_ids = await maintainer_service.get_maintainer_projects(current_user.id)

    # Get project details
    projects = await db.project.find_many(
        where={"id": {"in": project_ids}},
        include={"repositories": True, "maintainers": True},
    )

    logger.info(
        "maintainer_projects_listed",
        user_id=current_user.id,
        project_count=len(projects),
    )

    return {"projects": projects}


@router.get("/projects/{project_id}/prs")
async def list_project_prs(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by PR status"),
    author_id: Optional[str] = Query(None, description="Filter by author"),
    sort_by: str = Query("newest", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    List PRs for a project with filtering and sorting.

    Args:
        project_id: Project ID
        status: Filter by status (OPEN, UNDER_REVIEW, etc.)
        author_id: Filter by author ID
        sort_by: Sort order (newest, oldest, review_age)
        page: Page number
        page_size: Items per page

    Returns:
        Paginated PR list
    """
    # Verify maintainer access
    await require_maintainer_access(project_id, current_user, db)

    dashboard_service = MaintainerDashboardService(db)
    skip = (page - 1) * page_size

    prs, total = await dashboard_service.get_project_prs(
        project_id=project_id,
        status=status,
        author_id=author_id,
        sort_by=sort_by,
        skip=skip,
        take=page_size,
    )

    logger.info(
        "project_prs_listed",
        project_id=project_id,
        user_id=current_user.id,
        total=total,
    )

    return {
        "prs": prs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/prs/{pr_id}")
async def get_pr_details(
    pr_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    Get detailed PR information.

    Args:
        pr_id: PR ID

    Returns:
        PR details with full context
    """
    dashboard_service = MaintainerDashboardService(db)
    pr = await dashboard_service.get_pr_details(pr_id, current_user.id)

    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PR not found or access denied",
        )

    logger.info(
        "pr_details_viewed",
        pr_id=pr_id,
        user_id=current_user.id,
    )

    return {"pr": pr}


@router.post("/prs/{pr_id}/comments")
async def add_internal_comment(
    pr_id: str,
    request: InternalCommentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    Add internal comment to PR.

    Args:
        pr_id: PR ID
        request: Comment request

    Returns:
        Success message
    """
    # Get PR to verify access
    dashboard_service = MaintainerDashboardService(db)
    pr = await dashboard_service.get_pr_details(pr_id, current_user.id)

    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PR not found or access denied",
        )

    # Add comment
    success = await dashboard_service.add_internal_comment(
        pr_id, current_user.id, request.comment
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add comment",
        )

    logger.info(
        "internal_comment_added",
        pr_id=pr_id,
        user_id=current_user.id,
    )

    return {"message": "Comment added successfully"}


@router.get("/projects/{project_id}/contributors")
async def list_project_contributors(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    List all contributors for a project.

    Args:
        project_id: Project ID

    Returns:
        List of contributors with basic stats
    """
    # Verify maintainer access
    await require_maintainer_access(project_id, current_user, db)

    dashboard_service = MaintainerDashboardService(db)
    contributors = await dashboard_service.get_all_contributors(project_id)

    logger.info(
        "project_contributors_listed",
        project_id=project_id,
        user_id=current_user.id,
        contributor_count=len(contributors),
    )

    return {"contributors": contributors}


@router.get("/projects/{project_id}/contributors/{contributor_id}/stats")
async def get_contributor_stats(
    project_id: str,
    contributor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    Get detailed stats for a contributor in a project.

    Args:
        project_id: Project ID
        contributor_id: Contributor user ID

    Returns:
        Contributor statistics
    """
    # Verify maintainer access
    await require_maintainer_access(project_id, current_user, db)

    dashboard_service = MaintainerDashboardService(db)
    stats = await dashboard_service.get_contributor_stats(project_id, contributor_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor not found or no contributions",
        )

    logger.info(
        "contributor_stats_viewed",
        project_id=project_id,
        contributor_id=contributor_id,
        user_id=current_user.id,
    )

    return {"stats": stats}


@router.get("/projects/{project_id}/analytics")
async def get_project_analytics(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
):
    """
    Get project analytics for specified time range.

    Args:
        project_id: Project ID
        days: Number of days to analyze

    Returns:
        Project analytics data
    """
    # Verify maintainer access
    await require_maintainer_access(project_id, current_user, db)

    dashboard_service = MaintainerDashboardService(db)
    analytics = await dashboard_service.get_project_analytics(project_id, days)

    logger.info(
        "project_analytics_viewed",
        project_id=project_id,
        user_id=current_user.id,
        days=days,
    )

    return {"analytics": analytics}
