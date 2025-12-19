"""
Maintainer dashboard service for project management operations.
Provides maintainers with PR management, contributor stats, and analytics.
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from prisma.models import Project, PullRequest, User

from prisma import Prisma

logger = structlog.get_logger(__name__)


class MaintainerDashboardService:
    """Service for maintainer dashboard operations."""

    def __init__(self, db: Prisma):
        """Initialize maintainer dashboard service with Prisma client."""
        self.db = db

    async def check_maintainer_access(
        self, user_id: str, project_id: str
    ) -> bool:
        """
        Check if user is a maintainer of the project.

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            True if user is maintainer or owner
        """
        # Check if user is project owner
        project = await self.db.project.find_unique(where={"id": project_id})
        if project and project.ownerId == user_id:
            return True

        # Check if user is maintainer
        maintainer = await self.db.projectmaintainer.find_unique(
            where={"projectId_userId": {"projectId": project_id, "userId": user_id}}
        )
        return maintainer is not None

    async def get_project_prs(
        self,
        project_id: str,
        status: Optional[str] = None,
        author_id: Optional[str] = None,
        sort_by: str = "newest",
        skip: int = 0,
        take: int = 20,
    ) -> tuple[list[PullRequest], int]:
        """
        Get PRs for a project with filtering and sorting.

        Args:
            project_id: Project ID
            status: Filter by PR status
            author_id: Filter by author
            sort_by: Sort order (newest, oldest, review_age)
            skip: Number of records to skip
            take: Number of records to return

        Returns:
            Tuple of (PRs, total_count)
        """
        # Get project repositories
        repositories = await self.db.repository.find_many(
            where={"projectId": project_id}
        )
        repo_ids = [repo.id for repo in repositories]

        if not repo_ids:
            return [], 0

        # Build where clause
        where = {"repositoryId": {"in": repo_ids}}
        if status:
            where["status"] = status
        if author_id:
            where["authorId"] = author_id

        # Build order clause
        order = {}
        if sort_by == "newest":
            order = {"createdAt": "desc"}
        elif sort_by == "oldest":
            order = {"createdAt": "asc"}
        elif sort_by == "review_age":
            order = {"reviewedAt": "asc"}
        else:
            order = {"createdAt": "desc"}

        # Get PRs
        prs = await self.db.pullrequest.find_many(
            where=where,
            include={"author": True, "repository": True, "reviews": True},
            order=order,
            skip=skip,
            take=take,
        )

        # Get total count
        total = await self.db.pullrequest.count(where=where)

        return prs, total

    async def get_pr_details(
        self, pr_id: str, user_id: str
    ) -> Optional[PullRequest]:
        """
        Get detailed PR information with full context.

        Args:
            pr_id: PR ID
            user_id: Requesting user ID (for access control)

        Returns:
            PR with full details or None
        """
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id},
            include={
                "author": True,
                "repository": {"include": {"project": True}},
                "reviews": {"include": {"reviewer": True}},
                "reviewComments": {"include": {"reviewer": True}},
            },
        )

        if not pr or not pr.repository:
            return None

        # Check access
        project_id = pr.repository.project.id if pr.repository.project else None
        if not project_id:
            return None

        has_access = await self.check_maintainer_access(user_id, project_id)
        if not has_access:
            logger.warning(
                "unauthorized_pr_access",
                user_id=user_id,
                pr_id=pr_id,
                project_id=project_id,
            )
            return None

        return pr

    async def add_internal_comment(
        self, pr_id: str, reviewer_id: str, comment: str
    ) -> bool:
        """
        Add an internal comment to a PR.

        Args:
            pr_id: PR ID
            reviewer_id: Reviewer ID
            comment: Comment text

        Returns:
            True if comment added successfully
        """
        try:
            await self.db.reviewcomment.create(
                data={
                    "pullRequestId": pr_id,
                    "reviewerId": reviewer_id,
                    "comment": comment,
                    "isInternal": True,
                }
            )

            logger.info(
                "internal_comment_added",
                pr_id=pr_id,
                reviewer_id=reviewer_id,
            )
            return True

        except Exception as e:
            logger.error(
                "internal_comment_error",
                pr_id=pr_id,
                reviewer_id=reviewer_id,
                error=str(e),
            )
            return False

    async def get_contributor_stats(
        self, project_id: str, user_id: str
    ) -> Optional[dict]:
        """
        Get contributor statistics for a project.

        Args:
            project_id: Project ID
            user_id: Contributor user ID

        Returns:
            Dictionary with contributor stats
        """
        # Get project repositories
        repositories = await self.db.repository.find_many(
            where={"projectId": project_id}
        )
        repo_ids = [repo.id for repo in repositories]

        if not repo_ids:
            return None

        # Get all PRs by contributor
        prs = await self.db.pullrequest.find_many(
            where={"repositoryId": {"in": repo_ids}, "authorId": user_id},
            include={"reviews": True},
        )

        # Calculate stats
        total_prs = len(prs)
        merged_prs = sum(1 for pr in prs if pr.status == "MERGED")
        open_prs = sum(1 for pr in prs if pr.status == "OPEN")

        # Calculate average rating
        total_rating = 0
        rated_reviews = 0
        for pr in prs:
            for review in pr.reviews:
                if review.rating is not None:
                    total_rating += review.rating
                    rated_reviews += 1

        avg_rating = total_rating / rated_reviews if rated_reviews > 0 else None

        # Calculate average review time (for merged PRs)
        review_times = []
        for pr in prs:
            if pr.status == "MERGED" and pr.openedAt and pr.mergedAt:
                review_time = (pr.mergedAt - pr.openedAt).total_seconds() / 3600  # hours
                review_times.append(review_time)

        avg_review_time = (
            sum(review_times) / len(review_times) if review_times else None
        )

        # Get points earned in project
        points = await self.db.pointtransaction.aggregate(
            where={
                "userId": user_id,
                "pullRequest": {"repositoryId": {"in": repo_ids}},
            },
            _sum={"points": True},
        )

        total_points = points["_sum"]["points"] if points["_sum"]["points"] else 0

        return {
            "user_id": user_id,
            "project_id": project_id,
            "total_prs": total_prs,
            "merged_prs": merged_prs,
            "open_prs": open_prs,
            "avg_rating": round(avg_rating, 2) if avg_rating else None,
            "avg_review_time_hours": (
                round(avg_review_time, 1) if avg_review_time else None
            ),
            "total_points": total_points,
        }

    async def get_project_analytics(
        self, project_id: str, days: int = 30
    ) -> dict:
        """
        Get project analytics for specified time range.

        Args:
            project_id: Project ID
            days: Number of days to analyze

        Returns:
            Dictionary with analytics data
        """
        # Get project repositories
        repositories = await self.db.repository.find_many(
            where={"projectId": project_id}
        )
        repo_ids = [repo.id for repo in repositories]

        if not repo_ids:
            return {
                "contribution_volume": [],
                "top_contributors": [],
                "pr_merge_rate": 0,
                "avg_review_time_hours": None,
                "quality_trends": {},
            }

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get PRs in time range
        prs = await self.db.pullrequest.find_many(
            where={
                "repositoryId": {"in": repo_ids},
                "createdAt": {"gte": start_date},
            },
            include={"author": True, "reviews": True},
        )

        # Contribution volume over time (by week)
        contribution_volume = {}
        for pr in prs:
            week_key = pr.createdAt.strftime("%Y-W%U")
            contribution_volume[week_key] = contribution_volume.get(week_key, 0) + 1

        volume_data = [
            {"week": week, "count": count}
            for week, count in sorted(contribution_volume.items())
        ]

        # Top contributors
        contributor_counts = {}
        for pr in prs:
            if pr.author:
                contributor_counts[pr.author.id] = {
                    "user_id": pr.author.id,
                    "username": pr.author.githubUsername,
                    "count": contributor_counts.get(pr.author.id, {}).get("count", 0)
                    + 1,
                }

        top_contributors = sorted(
            contributor_counts.values(), key=lambda x: x["count"], reverse=True
        )[:10]

        # PR merge rate
        total_prs = len(prs)
        merged_prs = sum(1 for pr in prs if pr.status == "MERGED")
        merge_rate = (merged_prs / total_prs * 100) if total_prs > 0 else 0

        # Average review time
        review_times = []
        for pr in prs:
            if pr.status == "MERGED" and pr.openedAt and pr.mergedAt:
                review_time = (pr.mergedAt - pr.openedAt).total_seconds() / 3600
                review_times.append(review_time)

        avg_review_time = (
            sum(review_times) / len(review_times) if review_times else None
        )

        # Quality trends (rating distribution)
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for pr in prs:
            for review in pr.reviews:
                if review.rating is not None:
                    rating_distribution[review.rating] = (
                        rating_distribution.get(review.rating, 0) + 1
                    )

        return {
            "contribution_volume": volume_data,
            "top_contributors": top_contributors,
            "pr_merge_rate": round(merge_rate, 1),
            "avg_review_time_hours": (
                round(avg_review_time, 1) if avg_review_time else None
            ),
            "quality_trends": rating_distribution,
            "total_prs": total_prs,
            "merged_prs": merged_prs,
        }

    async def get_all_contributors(
        self, project_id: str
    ) -> list[dict]:
        """
        Get all contributors for a project with basic stats.

        Args:
            project_id: Project ID

        Returns:
            List of contributors with stats
        """
        # Get project repositories
        repositories = await self.db.repository.find_many(
            where={"projectId": project_id}
        )
        repo_ids = [repo.id for repo in repositories]

        if not repo_ids:
            return []

        # Get all PRs
        prs = await self.db.pullrequest.find_many(
            where={"repositoryId": {"in": repo_ids}},
            include={"author": True},
        )

        # Group by contributor
        contributors = {}
        for pr in prs:
            if not pr.author:
                continue

            user_id = pr.author.id
            if user_id not in contributors:
                contributors[user_id] = {
                    "user_id": user_id,
                    "username": pr.author.githubUsername,
                    "avatar_url": pr.author.avatarUrl,
                    "total_prs": 0,
                    "merged_prs": 0,
                }

            contributors[user_id]["total_prs"] += 1
            if pr.status == "MERGED":
                contributors[user_id]["merged_prs"] += 1

        return sorted(
            contributors.values(), key=lambda x: x["merged_prs"], reverse=True
        )
