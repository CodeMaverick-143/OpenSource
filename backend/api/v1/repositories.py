"""
Repository management API endpoints.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prisma.models import User

from backend.core.dependencies import get_current_active_user
from backend.core.permissions import check_project_maintainer
from backend.db.prisma_client import get_db
from backend.schemas.repository import (
    RepositoryListResponse,
    RepositoryRegister,
    RepositoryResponse,
    RepositorySync,
)
from backend.services.repository_service import RepositoryService
from prisma import Prisma

router = APIRouter(tags=["repositories"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def register_repository(
    data: RepositoryRegister,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> RepositoryResponse:
    """Register a GitHub repository under a project."""
    # Get project
    project = await db.project.find_unique(where={"slug": data.project_slug})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check permission
    is_maintainer = await check_project_maintainer(db, data.project_slug, current_user)
    if not is_maintainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project maintainers can register repositories",
        )

    service = RepositoryService(db)
    repository = await service.register_repository(project.id, data.github_repo_url, current_user)

    return RepositoryResponse.model_validate(repository)


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    project_slug: str = Query(None),
    active_only: bool = Query(True),
    db: Prisma = Depends(get_db),
) -> RepositoryListResponse:
    """List repositories."""
    project_id = None

    if project_slug:
        project = await db.project.find_unique(where={"slug": project_slug})
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        project_id = project.id

    service = RepositoryService(db)
    repositories = await service.list_repositories(project_id, active_only)

    return RepositoryListResponse(
        repositories=[RepositoryResponse.model_validate(r) for r in repositories],
        total=len(repositories),
    )


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: str, db: Prisma = Depends(get_db)) -> RepositoryResponse:
    """Get repository by ID."""
    service = RepositoryService(db)
    repository = await service.get_repository(repository_id)

    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    return RepositoryResponse.model_validate(repository)


@router.post("/{repository_id}/sync", response_model=RepositorySync)
async def sync_repository(
    repository_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> RepositorySync:
    """Manually sync repository metadata from GitHub."""
    service = RepositoryService(db)
    repository = await service.sync_repository_metadata(repository_id, current_user)

    return RepositorySync(
        repository_id=repository.id, status="success", message="Repository synced successfully"
    )


@router.post("/{repository_id}/disable", response_model=RepositoryResponse)
async def disable_repository(
    repository_id: str,
    reason: str = Query(..., description="Reason for disabling"),
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> RepositoryResponse:
    """Disable repository (maintainer only)."""
    # Get repository and check permissions
    repository = await db.repository.find_unique(
        where={"id": repository_id}, include={"project": True}
    )

    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    # Check permission
    is_maintainer = await check_project_maintainer(db, repository.project.slug, current_user)
    if not is_maintainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project maintainers can disable repositories",
        )

    service = RepositoryService(db)
    disabled_repo = await service.disable_repository(repository_id, reason, current_user)

    return RepositoryResponse.model_validate(disabled_repo)


@router.post("/{repository_id}/enable", response_model=RepositoryResponse)
async def enable_repository(
    repository_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Prisma = Depends(get_db),
) -> RepositoryResponse:
    """Re-enable repository (maintainer only)."""
    # Get repository and check permissions
    repository = await db.repository.find_unique(
        where={"id": repository_id}, include={"project": True}
    )

    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    # Check permission
    is_maintainer = await check_project_maintainer(db, repository.project.slug, current_user)
    if not is_maintainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project maintainers can enable repositories",
        )

    service = RepositoryService(db)
    enabled_repo = await service.enable_repository(repository_id, current_user)

    return RepositoryResponse.model_validate(enabled_repo)
