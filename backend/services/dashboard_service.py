"""
Dashboard service for contributor dashboard data aggregation.
"""

from datetime import datetime
from typing import Dict, List, Optional

import structlog
from prisma.models import Badge, PullRequest, User

from prisma import Prisma

logger = structlog.get_logger(__name__)


class DashboardService:
    """Service for aggregating contributor dashboard data."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def get_user_prs(
        self,
        user_id: str,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        repository_id: Optional[str] = None,
        sort_by: str = "recent",
        page: int = 1,
        limit: int = 20,
    ) -> Dict:
        """
        Get user's PRs with filtering, sorting, and pagination.

        Args:
            user_id: User ID
            status: Filter by PR status (OPEN, MERGED, CLOSED, etc.)
            project_id: Filter by project ID
            repository_id: Filter by repository ID
            sort_by: Sort order (recent, score, oldest)
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Dictionary with items, total, page, limit, total_pages
        """
        logger.info(
            "fetching_user_prs",
            user_id=user_id,
            status=status,
            project_id=project_id,
            repository_id=repository_id,
            sort_by=sort_by,
            page=page,
            limit=limit,
        )

        # Build where clause
        where_clause = {"authorId": user_id}

        if status:
            where_clause["status"] = status

        if repository_id:
            where_clause["repositoryId"] = repository_id
        elif project_id:
            # Filter by project through repository
            where_clause["repository"] = {"is": {"projectId": project_id}}

        # Build order by clause
        order_by = []
        if sort_by == "recent":
            order_by = [{"openedAt": "desc"}]
        elif sort_by == "score":
            order_by = [{"score": "desc"}, {"openedAt": "desc"}]
        elif sort_by == "oldest":
            order_by = [{"openedAt": "asc"}]
        else:
            order_by = [{"openedAt": "desc"}]  # Default to recent

        # Calculate offset
        offset = (page - 1) * limit

        # Fetch PRs with repository and project joins
        prs = await self.db.pullrequest.find_many(
            where=where_clause,
            include={
                "repository": {"include": {"project": True}},
            },
            order=order_by,
            skip=offset,
            take=limit,
        )

        # Get total count
        total = await self.db.pullrequest.count(where=where_clause)

        # Calculate total pages
        total_pages = (total + limit - 1) // limit if total > 0 else 0

        # Format response
        items = []
        for pr in prs:
            # Determine last activity timestamp
            last_activity = pr.updatedAt
            if pr.mergedAt:
                last_activity = pr.mergedAt
            elif pr.closedAt:
                last_activity = pr.closedAt

            items.append(
                {
                    "id": pr.id,
                    "title": pr.title,
                    "pr_number": pr.prNumber,
                    "github_url": pr.githubUrl,
                    "status": pr.status,
                    "score": pr.score,
                    "project_name": (
                        pr.repository.project.name
                        if pr.repository and pr.repository.project
                        else None
                    ),
                    "project_slug": (
                        pr.repository.project.slug
                        if pr.repository and pr.repository.project
                        else None
                    ),
                    "project_is_active": (
                        pr.repository.project.isActive
                        if pr.repository and pr.repository.project
                        else None
                    ),
                    "repository_name": pr.repository.fullName if pr.repository else None,
                    "repository_is_active": pr.repository.isActive if pr.repository else None,
                    "opened_at": pr.openedAt.isoformat(),
                    "merged_at": pr.mergedAt.isoformat() if pr.mergedAt else None,
                    "closed_at": pr.closedAt.isoformat() if pr.closedAt else None,
                    "last_activity": last_activity.isoformat(),
                }
            )

        logger.info(
            "user_prs_fetched",
            user_id=user_id,
            total=total,
            page=page,
            items_count=len(items),
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    async def get_points_history(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> Dict:
        """
        Get user's points transaction history.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Dictionary with items, total, page, limit, total_pages
        """
        logger.info("fetching_points_history", user_id=user_id, page=page, limit=limit)

        # Calculate offset
        offset = (page - 1) * limit

        # Fetch transactions with PR joins
        transactions = await self.db.pointtransaction.find_many(
            where={"userId": user_id},
            include={"pullRequest": True},
            order=[{"createdAt": "desc"}],
            skip=offset,
            take=limit,
        )

        # Get total count
        total = await self.db.pointtransaction.count(where={"userId": user_id})

        # Calculate total pages
        total_pages = (total + limit - 1) // limit if total > 0 else 0

        # Format response
        items = []
        for txn in transactions:
            pr_reference = None
            if txn.pullRequest:
                pr_reference = {
                    "id": txn.pullRequest.id,
                    "title": txn.pullRequest.title,
                    "pr_number": txn.pullRequest.prNumber,
                    "github_url": txn.pullRequest.githubUrl,
                }

            items.append(
                {
                    "id": txn.id,
                    "points": txn.points,
                    "reason": txn.reason,
                    "transaction_type": txn.transactionType,
                    "pr_reference": pr_reference,
                    "metadata": txn.metadata,
                    "created_at": txn.createdAt.isoformat(),
                }
            )

        logger.info(
            "points_history_fetched",
            user_id=user_id,
            total=total,
            page=page,
            items_count=len(items),
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    async def get_user_badges(self, user_id: str) -> Dict:
        """
        Get user's earned badges and available badges.

        Args:
            user_id: User ID

        Returns:
            Dictionary with earned and available badges
        """
        logger.info("fetching_user_badges", user_id=user_id)

        # Fetch earned badges
        user_badges = await self.db.userbadge.find_many(
            where={"userId": user_id},
            include={"badge": True},
            order=[{"earnedAt": "desc"}],
        )

        earned = []
        earned_badge_ids = set()
        for ub in user_badges:
            earned_badge_ids.add(ub.badgeId)
            earned.append(
                {
                    "id": ub.badge.id,
                    "name": ub.badge.name,
                    "description": ub.badge.description,
                    "icon_url": ub.badge.iconUrl,
                    "earned_at": ub.earnedAt.isoformat(),
                }
            )

        # Fetch all badges to show available ones
        all_badges = await self.db.badge.find_many(order=[{"name": "asc"}])

        available = []
        for badge in all_badges:
            if badge.id not in earned_badge_ids:
                available.append(
                    {
                        "id": badge.id,
                        "name": badge.name,
                        "description": badge.description,
                        "icon_url": badge.iconUrl,
                        "criteria": badge.criteria,
                    }
                )

        logger.info(
            "user_badges_fetched",
            user_id=user_id,
            earned_count=len(earned),
            available_count=len(available),
        )

        return {"earned": earned, "available": available}

    async def get_user_rank_info(self, user_id: str) -> Optional[Dict]:
        """
        Get user's rank information from snapshots.

        Args:
            user_id: User ID

        Returns:
            Rank info dictionary or None if rank unavailable
        """
        logger.info("fetching_user_rank_info", user_id=user_id)

        # Fetch latest global rank snapshot
        latest_snapshot = await self.db.ranksnapshot.find_first(
            where={"userId": user_id, "leaderboardType": "GLOBAL"},
            order=[{"snapshotAt": "desc"}],
        )

        if not latest_snapshot:
            logger.info("rank_unavailable", user_id=user_id)
            return None

        # Fetch previous snapshot for rank change
        previous_snapshot = await self.db.ranksnapshot.find_first(
            where={
                "userId": user_id,
                "leaderboardType": "GLOBAL",
                "snapshotAt": {"lt": latest_snapshot.snapshotAt},
            },
            order=[{"snapshotAt": "desc"}],
        )

        # Calculate rank change
        rank_change = 0
        if previous_snapshot:
            # Rank improvement means lower rank number (e.g., 50 -> 42 is +8 improvement)
            rank_change = previous_snapshot.rank - latest_snapshot.rank

        # Get total users for percentile calculation
        total_users = await self.db.user.count(
            where={"isBanned": False, "isDeleted": False, "totalPoints": {"gt": 0}}
        )

        # Calculate percentile (higher is better)
        percentile = 0.0
        if total_users > 0:
            percentile = ((total_users - latest_snapshot.rank) / total_users) * 100

        # Get user's current points
        user = await self.db.user.find_unique(where={"id": user_id})

        # Calculate progress to next rank (simplified - assume 150 points per rank)
        # In production, this should be based on actual next user's points
        next_rank_points = latest_snapshot.totalPoints + 150
        progress_percentage = 0.0
        if user:
            points_to_next = next_rank_points - user.totalPoints
            if points_to_next > 0:
                progress_percentage = (150 - points_to_next) / 150 * 100
            else:
                progress_percentage = 100.0

        logger.info(
            "user_rank_info_fetched",
            user_id=user_id,
            rank=latest_snapshot.rank,
            rank_change=rank_change,
        )

        return {
            "rank": latest_snapshot.rank,
            "previous_rank": previous_snapshot.rank if previous_snapshot else None,
            "rank_change": rank_change,
            "total_points": user.totalPoints if user else latest_snapshot.totalPoints,
            "percentile": round(percentile, 1),
            "next_rank_points": next_rank_points,
            "progress_percentage": round(progress_percentage, 1),
            "leaderboard_type": "GLOBAL",
            "last_updated": latest_snapshot.snapshotAt.isoformat(),
        }

    async def get_dashboard_stats(self, user_id: str) -> Dict:
        """
        Get dashboard summary statistics.

        Args:
            user_id: User ID

        Returns:
            Summary statistics dictionary
        """
        logger.info("fetching_dashboard_stats", user_id=user_id)

        # Get user info
        user = await self.db.user.find_unique(where={"id": user_id})

        if not user:
            logger.error("user_not_found", user_id=user_id)
            raise ValueError("User not found")

        # Count PRs by status
        total_prs = await self.db.pullrequest.count(where={"authorId": user_id})
        merged_prs = await self.db.pullrequest.count(
            where={"authorId": user_id, "status": "MERGED"}
        )
        open_prs = await self.db.pullrequest.count(where={"authorId": user_id, "status": "OPEN"})
        under_review_prs = await self.db.pullrequest.count(
            where={"authorId": user_id, "status": "UNDER_REVIEW"}
        )

        # Count active projects (projects with at least one PR)
        active_projects_result = await self.db.query_raw(
            """
            SELECT COUNT(DISTINCT p.id) as count
            FROM projects p
            JOIN repositories r ON r.project_id = p.id
            JOIN pull_requests pr ON pr.repository_id = r.id
            WHERE pr.author_id = $1 AND p.is_active = true
            """,
            user_id,
        )
        active_projects = active_projects_result[0]["count"] if active_projects_result else 0

        # Count earned badges
        badges_earned = await self.db.userbadge.count(where={"userId": user_id})

        logger.info(
            "dashboard_stats_fetched",
            user_id=user_id,
            total_prs=total_prs,
            merged_prs=merged_prs,
        )

        return {
            "total_prs": total_prs,
            "merged_prs": merged_prs,
            "open_prs": open_prs,
            "under_review_prs": under_review_prs,
            "total_points": user.totalPoints,
            "active_projects": active_projects,
            "badges_earned": badges_earned,
            "current_rank": user.rank,
        }
