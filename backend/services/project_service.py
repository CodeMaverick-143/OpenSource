"""
Project service for business logic.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import HTTPException, status
from prisma import Prisma
from prisma.models import Project, User

from backend.schemas.project import (
    ContributionRulesUpdate,
    ProjectCreate,
    ProjectUpdate,
)
from backend.utils.slug import generate_unique_project_slug

logger = structlog.get_logger(__name__)


class ProjectService:
    """Service for project management."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def create_project(self, data: ProjectCreate, owner: User) -> Project:
        """
        Create a new project.

        Args:
            data: Project creation data
            owner: Project owner

        Returns:
            Created project

        Raises:
            HTTPException: If project name already exists
        """
        # Check if project name exists
        existing = await self.db.project.find_first(where={"name": data.name})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{data.name}' already exists",
            )

        # Generate unique slug
        slug = await generate_unique_project_slug(data.name, self.db)

        # Create project
        project = await self.db.project.create(
            data={
                "slug": slug,
                "name": data.name,
                "description": data.description,
                "tags": data.tags,
                "difficulty": data.difficulty,
                "ownerId": owner.id,
                "rulesVersion": 1,
            }
        )

        # Add owner as maintainer with "owner" role
        await self.db.projectmaintainer.create(
            data={"projectId": project.id, "userId": owner.id, "role": "owner"}
        )

        logger.info(
            "project_created",
            project_id=project.id,
            slug=slug,
            owner_id=owner.id,
        )

        return project

    async def get_project(self, slug: str) -> Optional[Project]:
        """
        Get project by slug.

        Args:
            slug: Project slug

        Returns:
            Project or None
        """
        return await self.db.project.find_unique(where={"slug": slug})

    async def list_projects(
        self, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> tuple[List[Project], int]:
        """
        List projects.

        Args:
            skip: Number of projects to skip
            limit: Maximum number of projects to return
            active_only: Only return active projects

        Returns:
            Tuple of (projects, total_count)
        """
        where_clause = {"isActive": True} if active_only else {}

        projects = await self.db.project.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            order={"createdAt": "desc"},
        )

        total = await self.db.project.count(where=where_clause)

        return projects, total

    async def update_project(
        self, slug: str, data: ProjectUpdate, user: User
    ) -> Project:
        """
        Update project metadata.

        Args:
            slug: Project slug
            data: Update data
            user: User performing update

        Returns:
            Updated project

        Raises:
            HTTPException: If project not found or permission denied
        """
        project = await self.get_project(slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Build update data
        update_data = {}
        if data.name is not None:
            # Check name uniqueness
            existing = await self.db.project.find_first(
                where={"name": data.name, "id": {"not": project.id}}
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Project with name '{data.name}' already exists",
                )
            update_data["name"] = data.name

            # Regenerate slug if name changed
            new_slug = await generate_unique_project_slug(data.name, self.db)
            update_data["slug"] = new_slug

        if data.description is not None:
            update_data["description"] = data.description
        if data.tags is not None:
            update_data["tags"] = data.tags
        if data.difficulty is not None:
            update_data["difficulty"] = data.difficulty

        # Update project
        updated_project = await self.db.project.update(
            where={"id": project.id}, data=update_data
        )

        logger.info("project_updated", project_id=project.id, user_id=user.id)

        return updated_project

    async def archive_project(self, slug: str, user: User) -> Project:
        """
        Archive project (soft delete).

        Args:
            slug: Project slug
            user: User performing archive

        Returns:
            Archived project

        Raises:
            HTTPException: If project not found
        """
        project = await self.get_project(slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Archive project
        archived_project = await self.db.project.update(
            where={"id": project.id}, data={"isActive": False}
        )

        logger.warning("project_archived", project_id=project.id, user_id=user.id)

        return archived_project

    async def unarchive_project(self, slug: str, user: User) -> Project:
        """
        Unarchive project.

        Args:
            slug: Project slug
            user: User performing unarchive

        Returns:
            Unarchived project

        Raises:
            HTTPException: If project not found
        """
        project = await self.db.project.find_unique(where={"slug": slug})
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Unarchive project
        unarchived_project = await self.db.project.update(
            where={"id": project.id}, data={"isActive": True}
        )

        logger.info("project_unarchived", project_id=project.id, user_id=user.id)

        return unarchived_project

    async def update_contribution_rules(
        self, slug: str, rules: ContributionRulesUpdate, user: User
    ) -> Project:
        """
        Update contribution rules (versioned).

        Args:
            slug: Project slug
            rules: New rules
            user: User performing update

        Returns:
            Updated project

        Raises:
            HTTPException: If project not found
        """
        project = await self.get_project(slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Increment rules version (never retroactive)
        new_version = project.rulesVersion + 1

        # Update rules
        updated_project = await self.db.project.update(
            where={"id": project.id},
            data={"rules": rules.model_dump(exclude_none=True), "rulesVersion": new_version},
        )

        logger.info(
            "contribution_rules_updated",
            project_id=project.id,
            new_version=new_version,
            user_id=user.id,
        )

        return updated_project
