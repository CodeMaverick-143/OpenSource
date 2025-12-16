"""Pydantic schemas for repository management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RepositoryRegister(BaseModel):
    """Schema for registering a repository."""

    project_slug: str = Field(..., description="Project slug")
    github_repo_url: str = Field(..., description="GitHub repository URL (owner/repo)")

    @field_validator("github_repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate GitHub repository URL format."""
        # Remove https://github.com/ if present
        if v.startswith("https://github.com/"):
            v = v.replace("https://github.com/", "")

        # Validate format: owner/repo
        parts = v.split("/")
        if len(parts) != 2:
            raise ValueError("Invalid GitHub repository format. Expected: owner/repo")

        owner, repo = parts
        if not owner or not repo:
            raise ValueError("Owner and repository name cannot be empty")

        return v


class RepositoryResponse(BaseModel):
    """Schema for repository response."""

    id: str
    project_id: str
    github_repo_id: int
    name: str
    full_name: str
    default_branch: str
    is_active: bool
    sync_status: str
    last_synced_at: Optional[datetime]
    disabled_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    """Schema for repository list response."""

    repositories: list[RepositoryResponse]
    total: int


class RepositorySync(BaseModel):
    """Schema for repository sync response."""

    repository_id: str
    status: str
    message: str
