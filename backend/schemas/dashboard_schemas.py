"""
Pydantic schemas for dashboard API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# REQUEST MODELS
# ============================================================================


class PRFilterParams(BaseModel):
    """Query parameters for PR filtering."""

    status: Optional[str] = Field(None, description="Filter by PR status")
    project_id: Optional[str] = Field(None, description="Filter by project ID")
    repository_id: Optional[str] = Field(None, description="Filter by repository ID")
    sort_by: str = Field("recent", description="Sort order: recent, score, oldest")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(20, ge=1, le=100, description="Items per page")


class ContributionGraphParams(BaseModel):
    """Query parameters for contribution graph."""

    range: str = Field("30d", description="Time range: 30d, 90d, all")


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class PRItemResponse(BaseModel):
    """Individual PR item in dashboard."""

    id: str
    title: str
    pr_number: int
    github_url: str
    status: str
    score: int
    project_name: Optional[str]
    project_slug: Optional[str]
    project_is_active: Optional[bool]
    repository_name: Optional[str]
    repository_is_active: Optional[bool]
    opened_at: str
    merged_at: Optional[str]
    closed_at: Optional[str]
    last_activity: str


class PRListResponse(BaseModel):
    """Paginated PR list response."""

    items: List[PRItemResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class PRReferenceResponse(BaseModel):
    """PR reference in point transaction."""

    id: str
    title: str
    pr_number: int
    github_url: str


class PointTransactionResponse(BaseModel):
    """Point transaction item."""

    id: str
    points: int
    reason: str
    transaction_type: str
    pr_reference: Optional[PRReferenceResponse]
    metadata: Optional[dict]
    created_at: str


class PointsHistoryResponse(BaseModel):
    """Paginated points history response."""

    items: List[PointTransactionResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class BadgeResponse(BaseModel):
    """Badge information."""

    id: str
    name: str
    description: str
    icon_url: Optional[str]
    earned_at: Optional[str] = None  # Only for earned badges
    criteria: Optional[dict] = None  # Only for available badges


class BadgesResponse(BaseModel):
    """User badges response."""

    earned: List[BadgeResponse]
    available: List[BadgeResponse]


class RankInfoResponse(BaseModel):
    """User rank information."""

    rank: int
    previous_rank: Optional[int]
    rank_change: int
    total_points: int
    percentile: float
    next_rank_points: int
    progress_percentage: float
    leaderboard_type: str
    last_updated: str


class ContributionDayResponse(BaseModel):
    """Single day contribution data."""

    date: str
    count: int


class ContributionStatsResponse(BaseModel):
    """Contribution statistics."""

    total_contributions: int
    current_streak: int
    longest_streak: int
    best_day: Optional[dict]


class ContributionGraphResponse(BaseModel):
    """Contribution graph response."""

    range: str
    data: List[ContributionDayResponse]
    stats: ContributionStatsResponse


class SkillTagResponse(BaseModel):
    """Skill tag information."""

    name: str
    weight: float
    contribution_count: int


class SkillsResponse(BaseModel):
    """User skills response."""

    skills: List[SkillTagResponse]


class DashboardStatsResponse(BaseModel):
    """Dashboard summary statistics."""

    total_prs: int
    merged_prs: int
    open_prs: int
    under_review_prs: int
    total_points: int
    active_projects: int
    badges_earned: int
    current_rank: Optional[int]
