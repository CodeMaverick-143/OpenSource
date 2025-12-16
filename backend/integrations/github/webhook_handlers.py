"""
GitHub webhook event handlers for pull_request, push, and repository events.
"""

from datetime import datetime
from typing import Any, Optional

import structlog
from prisma import Prisma
from prisma.models import PullRequest, Repository, User

logger = structlog.get_logger(__name__)


class WebhookHandler:
    """Base class for webhook event handlers."""

    def __init__(self, db: Prisma):
        """Initialize handler with database client."""
        self.db = db

    async def handle(self, payload: dict) -> None:
        """Handle webhook event. Override in subclasses."""
        raise NotImplementedError


class PullRequestHandler(WebhookHandler):
    """Handler for pull_request webhook events."""

    async def handle(self, payload: dict) -> None:
        """
        Handle pull_request events: opened, synchronize, reopened, closed.

        Args:
            payload: Webhook payload
        """
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})

        logger.info(
            "handling_pull_request_event",
            action=action,
            pr_number=pr_data.get("number"),
            repo=repo_data.get("full_name"),
        )

        if action == "opened":
            await self._handle_opened(pr_data, repo_data)
        elif action == "synchronize":
            await self._handle_synchronize(pr_data)
        elif action == "reopened":
            await self._handle_reopened(pr_data)
        elif action == "closed":
            await self._handle_closed(pr_data)
        else:
            logger.debug("unhandled_pr_action", action=action)

    async def _handle_opened(self, pr_data: dict, repo_data: dict) -> None:
        """Handle PR opened event."""
        # Get or create user
        author_data = pr_data.get("user", {})
        github_id = author_data.get("id")

        user = await self.db.user.find_unique(where={"githubId": github_id})
        if not user:
            logger.warning("pr_author_not_registered", github_id=github_id)
            return

        # Get repository
        github_repo_id = repo_data.get("id")
        repository = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})

        if not repository:
            logger.warning("repository_not_registered", github_repo_id=github_repo_id)
            return

        # Create or update PR
        github_pr_id = pr_data.get("id")
        pr_number = pr_data.get("number")

        existing_pr = await self.db.pullrequest.find_unique(where={"githubPrId": github_pr_id})

        if existing_pr:
            logger.info("pr_already_exists", pr_id=existing_pr.id)
            return

        # Calculate diff size
        additions = pr_data.get("additions", 0)
        deletions = pr_data.get("deletions", 0)
        diff_size = additions + deletions

        pr = await self.db.pullrequest.create(
            data={
                "repositoryId": repository.id,
                "authorId": user.id,
                "githubPrId": github_pr_id,
                "prNumber": pr_number,
                "title": pr_data.get("title", ""),
                "status": "OPEN",
                "score": 0,
                "githubUrl": pr_data.get("html_url", ""),
                "diffSize": diff_size,
                "openedAt": datetime.fromisoformat(
                    pr_data.get("created_at", "").replace("Z", "+00:00")
                ),
            }
        )

        logger.info("pr_created", pr_id=pr.id, pr_number=pr_number, author_id=user.id)

        # Award points for opening PR
        await self.db.pointtransaction.create(
            data={
                "userId": user.id,
                "pullRequestId": pr.id,
                "points": 10,  # Base points for opening PR
                "reason": "PR_OPENED",
                "metadata": {"pr_number": pr_number, "diff_size": diff_size},
            }
        )

        # Update user total points
        await self.db.user.update(
            where={"id": user.id}, data={"totalPoints": {"increment": 10}}
        )

    async def _handle_synchronize(self, pr_data: dict) -> None:
        """Handle PR synchronize event (new commits pushed)."""
        github_pr_id = pr_data.get("id")

        pr = await self.db.pullrequest.find_unique(where={"githubPrId": github_pr_id})
        if not pr:
            logger.warning("pr_not_found_for_synchronize", github_pr_id=github_pr_id)
            return

        # Update diff size
        additions = pr_data.get("additions", 0)
        deletions = pr_data.get("deletions", 0)
        diff_size = additions + deletions

        await self.db.pullrequest.update(
            where={"id": pr.id}, data={"diffSize": diff_size, "status": "OPEN"}
        )

        logger.info("pr_synchronized", pr_id=pr.id)

    async def _handle_reopened(self, pr_data: dict) -> None:
        """Handle PR reopened event."""
        github_pr_id = pr_data.get("id")

        pr = await self.db.pullrequest.find_unique(where={"githubPrId": github_pr_id})
        if not pr:
            logger.warning("pr_not_found_for_reopen", github_pr_id=github_pr_id)
            return

        await self.db.pullrequest.update(
            where={"id": pr.id}, data={"status": "OPEN", "closedAt": None}
        )

        logger.info("pr_reopened", pr_id=pr.id)

    async def _handle_closed(self, pr_data: dict) -> None:
        """Handle PR closed event (merged or not merged)."""
        github_pr_id = pr_data.get("id")
        merged = pr_data.get("merged", False)

        pr = await self.db.pullrequest.find_unique(where={"githubPrId": github_pr_id})
        if not pr:
            logger.warning("pr_not_found_for_close", github_pr_id=github_pr_id)
            return

        closed_at = datetime.fromisoformat(pr_data.get("closed_at", "").replace("Z", "+00:00"))
        merged_at = None
        status = "CLOSED"
        points_to_award = 0

        if merged:
            merged_at = datetime.fromisoformat(pr_data.get("merged_at", "").replace("Z", "+00:00"))
            status = "MERGED"
            points_to_award = 50  # Base points for merged PR

            # Bonus points for quality (based on diff size)
            if pr.diffSize and pr.diffSize > 100:
                points_to_award += 20

        await self.db.pullrequest.update(
            where={"id": pr.id},
            data={"status": status, "closedAt": closed_at, "mergedAt": merged_at},
        )

        # Award points if merged
        if merged and points_to_award > 0:
            await self.db.pointtransaction.create(
                data={
                    "userId": pr.authorId,
                    "pullRequestId": pr.id,
                    "points": points_to_award,
                    "reason": "PR_MERGED",
                    "metadata": {"diff_size": pr.diffSize},
                }
            )

            await self.db.user.update(
                where={"id": pr.authorId}, data={"totalPoints": {"increment": points_to_award}}
            )

        logger.info("pr_closed", pr_id=pr.id, merged=merged, points=points_to_award)


class PushHandler(WebhookHandler):
    """Handler for push webhook events."""

    async def handle(self, payload: dict) -> None:
        """
        Handle push events on default branch.

        Args:
            payload: Webhook payload
        """
        ref = payload.get("ref", "")
        repo_data = payload.get("repository", {})
        default_branch = repo_data.get("default_branch", "main")

        # Only handle pushes to default branch
        if not ref.endswith(default_branch):
            logger.debug("ignoring_non_default_branch_push", ref=ref)
            return

        github_repo_id = repo_data.get("id")
        repository = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})

        if not repository:
            logger.warning("repository_not_registered_for_push", github_repo_id=github_repo_id)
            return

        commits = payload.get("commits", [])
        logger.info(
            "handling_push_event",
            repo=repo_data.get("full_name"),
            branch=default_branch,
            commit_count=len(commits),
        )

        # Could trigger PR resync here if needed
        # For now, just log the event


class RepositoryHandler(WebhookHandler):
    """Handler for repository webhook events."""

    async def handle(self, payload: dict) -> None:
        """
        Handle repository events: renamed, transferred, privatized, deleted.

        Args:
            payload: Webhook payload
        """
        action = payload.get("action")
        repo_data = payload.get("repository", {})

        logger.info("handling_repository_event", action=action, repo=repo_data.get("full_name"))

        if action == "renamed":
            await self._handle_renamed(repo_data, payload.get("changes", {}))
        elif action == "transferred":
            await self._handle_transferred(repo_data)
        elif action == "privatized":
            await self._handle_privatized(repo_data)
        elif action == "deleted":
            await self._handle_deleted(repo_data)
        else:
            logger.debug("unhandled_repository_action", action=action)

    async def _handle_renamed(self, repo_data: dict, changes: dict) -> None:
        """Handle repository renamed event."""
        github_repo_id = repo_data.get("id")
        new_name = repo_data.get("name")
        new_full_name = repo_data.get("full_name")

        repository = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})
        if not repository:
            logger.warning("repository_not_found_for_rename", github_repo_id=github_repo_id)
            return

        await self.db.repository.update(
            where={"id": repository.id}, data={"name": new_name, "fullName": new_full_name}
        )

        logger.info("repository_renamed", repo_id=repository.id, new_name=new_full_name)

    async def _handle_transferred(self, repo_data: dict) -> None:
        """Handle repository transferred event."""
        github_repo_id = repo_data.get("id")
        new_full_name = repo_data.get("full_name")

        repository = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})
        if not repository:
            logger.warning("repository_not_found_for_transfer", github_repo_id=github_repo_id)
            return

        await self.db.repository.update(
            where={"id": repository.id}, data={"fullName": new_full_name}
        )

        logger.info("repository_transferred", repo_id=repository.id, new_owner=new_full_name)

    async def _handle_privatized(self, repo_data: dict) -> None:
        """Handle repository made private event."""
        github_repo_id = repo_data.get("id")

        repository = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})
        if not repository:
            logger.warning("repository_not_found_for_privatize", github_repo_id=github_repo_id)
            return

        # Deactivate repository
        await self.db.repository.update(where={"id": repository.id}, data={"isActive": False})

        logger.warning("repository_privatized", repo_id=repository.id)

    async def _handle_deleted(self, repo_data: dict) -> None:
        """Handle repository deleted event."""
        github_repo_id = repo_data.get("id")

        repository = await self.db.repository.find_unique(where={"githubRepoId": github_repo_id})
        if not repository:
            logger.warning("repository_not_found_for_delete", github_repo_id=github_repo_id)
            return

        # Deactivate repository (don't delete to preserve history)
        await self.db.repository.update(where={"id": repository.id}, data={"isActive": False})

        logger.warning("repository_deleted", repo_id=repository.id)


def get_handler(event_type: str, db: Prisma) -> Optional[WebhookHandler]:
    """
    Get appropriate handler for webhook event type.

    Args:
        event_type: GitHub event type
        db: Prisma client

    Returns:
        Handler instance or None
    """
    handlers = {
        "pull_request": PullRequestHandler,
        "push": PushHandler,
        "repository": RepositoryHandler,
    }

    handler_class = handlers.get(event_type)
    if handler_class:
        return handler_class(db)

    return None
