"""
Review service for maintainer-driven PR reviews.
"""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import HTTPException, status
from prisma import Prisma
from prisma.models import PRReview, PullRequest, User

from backend.services.pr_state_machine import PRState, PRStateMachine

logger = structlog.get_logger(__name__)


class ReviewService:
    """Service for PR review management."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def list_prs_for_maintainer(
        self,
        maintainer_id: str,
        state_filter: Optional[str] = None,
        project_id: Optional[str] = None,
        repository_id: Optional[str] = None,
        sort_by: str = "age",
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[PullRequest], int]:
        """
        List PRs for maintainer's projects.

        Args:
            maintainer_id: Maintainer user ID
            state_filter: Filter by PR state
            project_id: Filter by project
            repository_id: Filter by repository
            sort_by: Sort by (age, activity, last_updated)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (PRs, total_count)
        """
        # Get projects where user is maintainer
        maintainer_records = await self.db.projectmaintainer.find_many(
            where={"userId": maintainer_id}
        )

        project_ids = [m.projectId for m in maintainer_records]

        if not project_ids:
            return [], 0

        # Build where clause
        where_clause = {
            "repository": {"projectId": {"in": project_ids}},
            "isActive": True,
        }

        if state_filter:
            where_clause["status"] = state_filter

        if project_id:
            where_clause["repository"] = {"projectId": project_id}

        if repository_id:
            where_clause["repositoryId"] = repository_id

        # Build order clause
        order_clause = {}
        if sort_by == "age":
            order_clause = {"openedAt": "asc"}
        elif sort_by == "activity":
            order_clause = {"updatedAt": "desc"}
        elif sort_by == "last_updated":
            order_clause = {"updatedAt": "desc"}

        # Get PRs
        prs = await self.db.pullrequest.find_many(
            where=where_clause,
            order=order_clause,
            skip=skip,
            take=limit,
            include={"author": True, "repository": {"include": {"project": True}}},
        )

        total = await self.db.pullrequest.count(where=where_clause)

        return prs, total

    async def transition_pr_state(
        self,
        pr_id: str,
        new_state: str,
        reviewer_id: str,
        internal_comment: Optional[str] = None,
    ) -> PullRequest:
        """
        Transition PR to new state.

        Args:
            pr_id: PR ID
            new_state: Target state
            reviewer_id: Reviewer user ID
            internal_comment: Optional internal comment

        Returns:
            Updated PR

        Raises:
            HTTPException: If transition invalid or permission denied
        """
        # Get PR
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id}, include={"repository": {"include": {"project": True}}}
        )

        if not pr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PR not found")

        # Check permission
        is_maintainer = await self._is_maintainer(reviewer_id, pr.repository.projectId)
        if not is_maintainer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project maintainers can review PRs",
            )

        # Validate transition
        is_valid, error_msg = PRStateMachine.validate_transition(pr.status, new_state, pr_id)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        # Get timestamp updates
        timestamp_updates = PRStateMachine.get_timestamp_updates(new_state)

        # Update PR state
        async with self.db.tx() as transaction:
            updated_pr = await transaction.pullrequest.update(
                where={"id": pr_id},
                data={"status": new_state, **timestamp_updates},
            )

            # Create review record
            action = self._get_review_action(new_state)
            review_status = self._get_review_status(new_state)

            await transaction.prreview.create(
                data={
                    "pullRequestId": pr_id,
                    "reviewerId": reviewer_id,
                    "action": action,
                    "status": review_status,
                    "internalComment": internal_comment,
                }
            )

            logger.info(
                "pr_state_transitioned",
                pr_id=pr_id,
                from_state=pr.status,
                to_state=new_state,
                reviewer_id=reviewer_id,
            )

        return updated_pr

    async def add_review_comment(
        self,
        pr_id: str,
        reviewer_id: str,
        comment: str,
        is_internal: bool = True,
    ) -> dict:
        """
        Add review comment to PR.

        Args:
            pr_id: PR ID
            reviewer_id: Reviewer user ID
            comment: Comment text
            is_internal: Whether comment is internal (platform-only)

        Returns:
            Created comment
        """
        # Get PR
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id}, include={"repository": {"include": {"project": True}}}
        )

        if not pr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PR not found")

        # Check permission
        is_maintainer = await self._is_maintainer(reviewer_id, pr.repository.projectId)
        if not is_maintainer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project maintainers can add review comments",
            )

        # Create comment
        review_comment = await self.db.reviewcomment.create(
            data={
                "pullRequestId": pr_id,
                "reviewerId": reviewer_id,
                "comment": comment,
                "isInternal": is_internal,
            }
        )

        logger.info(
            "review_comment_added",
            pr_id=pr_id,
            reviewer_id=reviewer_id,
            is_internal=is_internal,
        )

        return review_comment

    async def add_quality_rating(
        self,
        pr_id: str,
        reviewer_id: str,
        rating: int,
        internal_comment: Optional[str] = None,
    ) -> PRReview:
        """
        Add quality rating to PR.

        Args:
            pr_id: PR ID
            reviewer_id: Reviewer user ID
            rating: Quality rating (1-5)
            internal_comment: Optional internal comment

        Returns:
            Created review

        Raises:
            HTTPException: If rating invalid or permission denied
        """
        if rating < 1 or rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5",
            )

        # Get PR
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id}, include={"repository": {"include": {"project": True}}}
        )

        if not pr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PR not found")

        # Check permission
        is_maintainer = await self._is_maintainer(reviewer_id, pr.repository.projectId)
        if not is_maintainer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project maintainers can rate PRs",
            )

        # Create review with rating
        review = await self.db.prreview.create(
            data={
                "pullRequestId": pr_id,
                "reviewerId": reviewer_id,
                "action": "RATED",
                "status": "PENDING",
                "rating": rating,
                "internalComment": internal_comment,
            }
        )

        logger.info(
            "quality_rating_added",
            pr_id=pr_id,
            reviewer_id=reviewer_id,
            rating=rating,
        )

        return review

    async def get_review_history(
        self, pr_id: str, requester_id: str
    ) -> List[PRReview]:
        """
        Get review history for PR.

        Args:
            pr_id: PR ID
            requester_id: User requesting history

        Returns:
            List of reviews

        Raises:
            HTTPException: If permission denied
        """
        # Get PR
        pr = await self.db.pullrequest.find_unique(
            where={"id": pr_id}, include={"repository": {"include": {"project": True}}}
        )

        if not pr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PR not found")

        # Check if requester is maintainer or PR author
        is_maintainer = await self._is_maintainer(requester_id, pr.repository.projectId)
        is_author = pr.authorId == requester_id

        if not is_maintainer and not is_author:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only maintainers and PR author can view review history",
            )

        # Get reviews
        reviews = await self.db.prreview.find_many(
            where={"pullRequestId": pr_id},
            order={"createdAt": "asc"},
            include={"reviewer": True},
        )

        # Filter internal comments for non-maintainers
        if not is_maintainer:
            for review in reviews:
                review.internalComment = None

        return reviews

    async def _is_maintainer(self, user_id: str, project_id: str) -> bool:
        """Check if user is maintainer of project."""
        maintainer = await self.db.projectmaintainer.find_unique(
            where={"projectId_userId": {"projectId": project_id, "userId": user_id}}
        )

        return maintainer is not None

    def _get_review_action(self, state: str) -> str:
        """Get review action from state."""
        action_map = {
            PRState.UNDER_REVIEW: "STARTED_REVIEW",
            PRState.CHANGES_REQUESTED: "REQUESTED_CHANGES",
            PRState.APPROVED: "APPROVED",
        }

        return action_map.get(state, "COMMENTED")

    def _get_review_status(self, state: str) -> str:
        """Get review status from state."""
        status_map = {
            PRState.UNDER_REVIEW: "PENDING",
            PRState.CHANGES_REQUESTED: "CHANGES_REQUESTED",
            PRState.APPROVED: "APPROVED",
        }

        return status_map.get(state, "PENDING")
