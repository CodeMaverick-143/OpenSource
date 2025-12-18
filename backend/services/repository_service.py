"""
Repository service for managing GitHub repositories.
"""

from datetime import datetime
from typing import List, Optional, Tuple

import structlog
from fastapi import HTTPException, status
from prisma.models import Repository, User

from backend.core.config import settings
from backend.integrations.github.repo_validator import GitHubRepoValidator
from backend.integrations.github.token_manager import TokenManager
from backend.integrations.github.webhook_manager import WebhookManager
from prisma import Prisma

logger = structlog.get_logger(__name__)


class RepositoryService:
    """Service for repository management."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def register_repository(
        self, project_id: str, github_repo_url: str, user: User
    ) -> Repository:
        """
        Register GitHub repository under project.

        Args:
            project_id: Project ID
            github_repo_url: GitHub repository URL (owner/repo)
            user: User registering repository

        Returns:
            Created repository

        Raises:
            HTTPException: If validation fails or repository already registered
        """
        # Parse owner/repo
        parts = github_repo_url.split("/")
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub repository format. Expected: owner/repo",
            )

        owner, repo = parts

        # Get user's GitHub token
        token_manager = TokenManager(self.db)
        github_token = await token_manager.get_token(user.id)

        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub token not found. Please re-authenticate.",
            )

        # Validate repository
        validator = GitHubRepoValidator(github_token.accessToken)
        repo_data = await validator.validate_for_registration(owner, repo)

        github_repo_id = repo_data.get("id")
        full_name = repo_data.get("full_name")
        default_branch = repo_data.get("default_branch", "main")

        # Check if repository already registered
        existing = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Repository {full_name} is already registered under another project",
            )

        # Create webhook
        webhook_url = f"{settings.API_BASE_URL}/api/v1/webhooks/github"
        webhook_manager = WebhookManager(github_token.accessToken)

        try:
            webhook_data = await webhook_manager.create_webhook(owner, repo, webhook_url)
            logger.info(
                "webhook_created_for_repo",
                owner=owner,
                repo=repo,
                webhook_id=webhook_data.get("id"),
            )
        except Exception as e:
            logger.error("webhook_creation_failed", owner=owner, repo=repo, error=str(e))
            # Continue with registration even if webhook fails
            # Webhook can be created manually later

        # Register repository
        repository = await self.db.repository.create(
            data={
                "projectId": project_id,
                "githubRepoId": github_repo_id,
                "name": repo,
                "fullName": full_name,
                "defaultBranch": default_branch,
                "syncStatus": "synced",
                "lastSyncedAt": datetime.utcnow(),
            }
        )

        logger.info(
            "repository_registered",
            repository_id=repository.id,
            github_repo_id=github_repo_id,
            project_id=project_id,
            user_id=user.id,
        )

        return repository

    async def get_repository(self, repository_id: str) -> Optional[Repository]:
        """
        Get repository by ID.

        Args:
            repository_id: Repository ID

        Returns:
            Repository or None
        """
        return await self.db.repository.find_unique(where={"id": repository_id})

    async def list_repositories(
        self, project_id: Optional[str] = None, active_only: bool = True
    ) -> List[Repository]:
        """
        List repositories.

        Args:
            project_id: Filter by project ID
            active_only: Only return active repositories

        Returns:
            List of repositories
        """
        where_clause = {}

        if project_id:
            where_clause["projectId"] = project_id

        if active_only:
            where_clause["isActive"] = True

        repositories = await self.db.repository.find_many(
            where=where_clause, order={"createdAt": "desc"}
        )

        return repositories

    async def sync_repository_metadata(self, repository_id: str, user: User) -> Repository:
        """
        Sync repository metadata from GitHub.

        Args:
            repository_id: Repository ID
            user: User performing sync

        Returns:
            Updated repository

        Raises:
            HTTPException: If repository not found or sync fails
        """
        repository = await self.get_repository(repository_id)
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        # Get user's GitHub token
        token_manager = TokenManager(self.db)
        github_token = await token_manager.get_token(user.id)

        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub token not found",
            )

        # Parse owner/repo
        parts = repository.fullName.split("/")
        owner, repo = parts

        # Get repository data from GitHub
        validator = GitHubRepoValidator(github_token.accessToken)

        try:
            repo_data = await validator.validate_and_get_repo(owner, repo)

            # Update repository
            updated_repository = await self.db.repository.update(
                where={"id": repository_id},
                data={
                    "name": repo_data.get("name"),
                    "fullName": repo_data.get("full_name"),
                    "defaultBranch": repo_data.get("default_branch", "main"),
                    "syncStatus": "synced",
                    "lastSyncedAt": datetime.utcnow(),
                },
            )

            logger.info("repository_synced", repository_id=repository_id)

            return updated_repository

        except Exception as e:
            # Mark sync as failed
            await self.db.repository.update(
                where={"id": repository_id},
                data={"syncStatus": "failed"},
            )

            logger.error("repository_sync_failed", repository_id=repository_id, error=str(e))

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync repository: {str(e)}",
            )

    async def disable_repository(self, repository_id: str, reason: str, user: User) -> Repository:
        """
        Disable repository.

        Args:
            repository_id: Repository ID
            reason: Reason for disabling
            user: User performing action

        Returns:
            Disabled repository

        Raises:
            HTTPException: If repository not found
        """
        repository = await self.get_repository(repository_id)
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        # Disable repository
        disabled_repository = await self.db.repository.update(
            where={"id": repository_id},
            data={"isActive": False, "disabledReason": reason},
        )

        logger.warning(
            "repository_disabled",
            repository_id=repository_id,
            reason=reason,
            user_id=user.id,
        )

        return disabled_repository

    async def enable_repository(self, repository_id: str, user: User) -> Repository:
        """
        Re-enable repository.

        Args:
            repository_id: Repository ID
            user: User performing action

        Returns:
            Enabled repository

        Raises:
            HTTPException: If repository not found
        """
        repository = await self.get_repository(repository_id)
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        # Enable repository
        enabled_repository = await self.db.repository.update(
            where={"id": repository_id},
            data={"isActive": True, "disabledReason": None},
        )

        logger.info("repository_enabled", repository_id=repository_id, user_id=user.id)

        return enabled_repository
