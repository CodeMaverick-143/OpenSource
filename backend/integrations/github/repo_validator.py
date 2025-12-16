"""
GitHub repository validator for ownership and access verification.
"""

from typing import Optional, Tuple

import structlog
from fastapi import HTTPException, status

from backend.integrations.github.rest_client import GitHubAPIError, GitHubRESTClient

logger = structlog.get_logger(__name__)


class RepoValidationError(HTTPException):
    """Repository validation error."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class GitHubRepoValidator:
    """Validator for GitHub repository registration."""

    def __init__(self, access_token: str):
        """
        Initialize validator.

        Args:
            access_token: GitHub access token
        """
        self.access_token = access_token

    async def validate_and_get_repo(self, owner: str, repo: str) -> dict:
        """
        Validate repository exists and get metadata.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository data from GitHub

        Raises:
            RepoValidationError: If validation fails
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                repo_data = await client.get_repo(owner, repo)

                logger.info(
                    "repo_validated",
                    owner=owner,
                    repo=repo,
                    repo_id=repo_data.get("id"),
                )

                return repo_data

            except GitHubAPIError as e:
                if e.status_code == 404:
                    raise RepoValidationError(f"Repository {owner}/{repo} not found on GitHub")
                elif e.status_code == 403:
                    raise RepoValidationError(
                        f"Access denied to repository {owner}/{repo}. "
                        "You may not have permission to access this repository."
                    )
                else:
                    raise RepoValidationError(f"Failed to validate repository: {e.message}")

    async def check_user_permissions(self, owner: str, repo: str) -> Tuple[bool, str]:
        """
        Check if user has admin/maintainer access to repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Tuple of (has_permission, permission_level)

        Raises:
            RepoValidationError: If check fails
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                # Get repository with permissions
                repo_data = await client.get_repo(owner, repo)

                permissions = repo_data.get("permissions", {})
                is_admin = permissions.get("admin", False)
                is_maintainer = permissions.get("maintain", False)
                is_push = permissions.get("push", False)

                if is_admin:
                    return True, "admin"
                elif is_maintainer:
                    return True, "maintain"
                elif is_push:
                    return True, "push"
                else:
                    return False, "read"

            except GitHubAPIError as e:
                raise RepoValidationError(f"Failed to check permissions: {e.message}")

    async def is_fork(self, owner: str, repo: str) -> bool:
        """
        Check if repository is a fork.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            True if repository is a fork
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                repo_data = await client.get_repo(owner, repo)
                return repo_data.get("fork", False)

            except GitHubAPIError as e:
                raise RepoValidationError(f"Failed to check fork status: {e.message}")

    async def is_private(self, owner: str, repo: str) -> bool:
        """
        Check if repository is private.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            True if repository is private
        """
        async with GitHubRESTClient(self.access_token) as client:
            try:
                repo_data = await client.get_repo(owner, repo)
                return repo_data.get("private", False)

            except GitHubAPIError as e:
                raise RepoValidationError(f"Failed to check privacy status: {e.message}")

    async def validate_for_registration(
        self, owner: str, repo: str, allow_forks: bool = False, allow_private: bool = False
    ) -> dict:
        """
        Comprehensive validation for repository registration.

        Args:
            owner: Repository owner
            repo: Repository name
            allow_forks: Allow fork repositories
            allow_private: Allow private repositories

        Returns:
            Repository data if valid

        Raises:
            RepoValidationError: If validation fails
        """
        # Get repository data
        repo_data = await self.validate_and_get_repo(owner, repo)

        # Check if fork
        if repo_data.get("fork", False) and not allow_forks:
            raise RepoValidationError(
                f"Repository {owner}/{repo} is a fork. Forks are not allowed."
            )

        # Check if private
        if repo_data.get("private", False) and not allow_private:
            raise RepoValidationError(
                f"Repository {owner}/{repo} is private. "
                "Private repositories require a premium plan."
            )

        # Check user permissions
        has_permission, permission_level = await self.check_user_permissions(owner, repo)

        if not has_permission or permission_level not in ["admin", "maintain"]:
            raise RepoValidationError(
                f"You must have admin or maintainer access to register {owner}/{repo}. "
                f"Current permission: {permission_level}"
            )

        logger.info(
            "repo_validation_passed",
            owner=owner,
            repo=repo,
            permission=permission_level,
            is_fork=repo_data.get("fork", False),
            is_private=repo_data.get("private", False),
        )

        return repo_data
