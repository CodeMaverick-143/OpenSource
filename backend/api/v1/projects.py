"""
Project management API endpoints.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prisma.models import User

from backend.core.dependencies import get_current_active_user
from backend.core.permissions import check_project_maintainer, check_project_owner
from backend.db.prisma_client import get_db
from backend.schemas.project import (
    ContributionRulesUpdate,
    MaintainerAdd,
    MaintainerListResponse,
    MaintainerResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from backend.services.maintainer_service import MaintainerService
from backend.services.project_service import ProjectService
from prisma import Prisma

router = APIRouter(tags=["projects"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> ProjectResponse:
    """Create a new project."""
    service = ProjectService(db)
    project = await service.create_project(data, current_user)

    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    active_only: bool = Query(True),
    db: Prisma = Depends(get_db),
) -> ProjectListResponse:
    """List all projects."""
    service = ProjectService(db)
    projects, total = await service.list_projects(skip, limit, active_only)

    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects], total=total
    )


@router.get("/{slug}", response_model=ProjectResponse)
async def get_project(slug: str, db: Prisma = Depends(get_db)) -> ProjectResponse:
    """Get project by slug."""
    service = ProjectService(db)
    project = await service.get_project(slug)

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return ProjectResponse.model_validate(project)


@router.patch("/{slug}", response_model=ProjectResponse)
async def update_project(
    slug: str,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> ProjectResponse:
    """Update project metadata (owner/maintainer only)."""
    # Check permission
    is_maintainer = await check_project_maintainer(db, slug, current_user)
    if not is_maintainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project maintainers can update the project",
        )

    service = ProjectService(db)
    project = await service.update_project(slug, data, current_user)

    return ProjectResponse.model_validate(project)


@router.post("/{slug}/archive", response_model=ProjectResponse)
async def archive_project(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> ProjectResponse:
    """Archive project (owner only)."""
    # Check permission
    is_owner = await check_project_owner(db, slug, current_user)
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can archive the project",
        )

    service = ProjectService(db)
    project = await service.archive_project(slug, current_user)

    return ProjectResponse.model_validate(project)


@router.put("/{slug}/rules", response_model=ProjectResponse)
async def update_contribution_rules(
    slug: str,
    rules: ContributionRulesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> ProjectResponse:
    """Update contribution rules (owner/maintainer only)."""
    # Check permission
    is_maintainer = await check_project_maintainer(db, slug, current_user)
    if not is_maintainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project maintainers can update contribution rules",
        )

    service = ProjectService(db)
    project = await service.update_contribution_rules(slug, rules, current_user)

    return ProjectResponse.model_validate(project)


# Maintainer management endpoints


@router.get("/{slug}/maintainers", response_model=MaintainerListResponse)
async def list_maintainers(slug: str, db: Prisma = Depends(get_db)) -> MaintainerListResponse:
    """List project maintainers."""
    # Get project
    project = await db.project.find_unique(where={"slug": slug})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    service = MaintainerService(db)
    maintainers = await service.list_maintainers(project.id)

    return MaintainerListResponse(
        maintainers=[MaintainerResponse.model_validate(m) for m in maintainers],
        total=len(maintainers),
    )


@router.post(
    "/{slug}/maintainers", response_model=MaintainerResponse, status_code=status.HTTP_201_CREATED
)
async def add_maintainer(
    slug: str,
    data: MaintainerAdd,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> MaintainerResponse:
    """Add maintainer to project (owner only)."""
    # Get project
    project = await db.project.find_unique(where={"slug": slug})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check permission
    is_owner = await check_project_owner(db, slug, current_user)
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can add maintainers",
        )

    service = MaintainerService(db)
    maintainer = await service.add_maintainer(project.id, data.user_id, data.role)

    return MaintainerResponse.model_validate(maintainer)


@router.delete("/{slug}/maintainers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_maintainer(
    slug: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> None:
    """Remove maintainer from project (owner only)."""
    # Get project
    project = await db.project.find_unique(where={"slug": slug})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check permission
    is_owner = await check_project_owner(db, slug, current_user)
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can remove maintainers",
        )

    service = MaintainerService(db)
    await service.remove_maintainer(project.id, user_id, current_user)
