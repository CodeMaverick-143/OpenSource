"""Pydantic schemas for project management."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# PROJECT SCHEMAS
# ============================================================================


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=3, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=5000, description="Project description")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    difficulty: str = Field(..., description="Difficulty level: beginner, intermediate, advanced")

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        """Validate difficulty level."""
        allowed = ["beginner", "intermediate", "advanced"]
        if v not in allowed:
            raise ValueError(f"Difficulty must be one of: {', '.join(allowed)}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags."""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return v


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    difficulty: Optional[str] = None

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        """Validate difficulty level."""
        if v is not None:
            allowed = ["beginner", "intermediate", "advanced"]
            if v not in allowed:
                raise ValueError(f"Difficulty must be one of: {', '.join(allowed)}")
        return v


class ContributionRulesUpdate(BaseModel):
    """Schema for updating contribution rules."""

    allowed_pr_types: Optional[List[str]] = Field(None, description="Allowed PR types")
    min_diff_size: Optional[int] = Field(None, ge=0, description="Minimum diff size")
    max_prs_per_period: Optional[int] = Field(None, ge=1, description="Max PRs per period")
    disallowed_patterns: Optional[List[str]] = Field(None, description="Disallowed patterns")
    scoring_modifiers: Optional[dict] = Field(None, description="Scoring modifiers")

    @field_validator("min_diff_size")
    @classmethod
    def validate_min_diff_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate minimum diff size."""
        if v is not None and v < 0:
            raise ValueError("Minimum diff size must be non-negative")
        return v


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str
    slug: str
    name: str
    description: Optional[str]
    tags: List[str]
    difficulty: str
    rules: Optional[dict]
    rules_version: int
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for project list response."""

    projects: List[ProjectResponse]
    total: int


# ============================================================================
# MAINTAINER SCHEMAS
# ============================================================================


class MaintainerAdd(BaseModel):
    """Schema for adding a maintainer."""

    user_id: str = Field(..., description="User ID to add as maintainer")
    role: str = Field(default="maintainer", description="Role: owner or maintainer")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role."""
        allowed = ["owner", "maintainer"]
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v


class MaintainerResponse(BaseModel):
    """Schema for maintainer response."""

    id: str
    project_id: str
    user_id: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class MaintainerListResponse(BaseModel):
    """Schema for maintainer list response."""

    maintainers: List[MaintainerResponse]
    total: int
