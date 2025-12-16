"""
Celery tasks for PR synchronization and management.
"""

from datetime import datetime, timedelta

import structlog
from celery import shared_task

from backend.db.prisma_client import get_prisma_client
from backend.integrations.github.rest_client import GitHubRESTClient
from backend.integrations.github.token_manager import TokenManager
from backend.services.event_deduplicator import EventDeduplicator
from backend.services.point_ledger import PointLedger
from backend.services.pr_state_machine import PRState, PRStateMachine
from backend.services.scoring_engine import ScoringEngine

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def sync_repository_prs(self, repository_id: str, user_id: str) -> dict:
    """
    Sync all PRs for a repository from GitHub (idempotent).

    Args:
        repository_id: Repository ID
        user_id: User ID for GitHub token

    Returns:
        Sync result
    """
    logger.info(
        "syncing_repository_prs",
        repository_id=repository_id,
        task_id=self.request.id,
    )

    try:
        import asyncio

        db = get_prisma_client()

        async def sync():
            # Get repository
            repository = await db.repository.find_unique(
                where={"id": repository_id}, include={"project": True}
            )

            if not repository:
                raise ValueError(f"Repository {repository_id} not found")

            # Get user's GitHub token
            token_manager = TokenManager(db)
            github_token = await token_manager.get_token(user_id)

            if not github_token:
                raise ValueError(f"GitHub token not found for user {user_id}")

            # Parse owner/repo
            owner, repo = repository.fullName.split("/")

            # Fetch all PRs from GitHub
            async with GitHubRESTClient(github_token.accessToken) as client:
                prs = await client.list_pull_requests(owner, repo, state="all")

            synced_count = 0
            skipped_count = 0

            # Reconcile with database
            for pr_data in prs:
                github_pr_id = pr_data.get("id")

                # Check if PR exists
                existing_pr = await db.pullrequest.find_unique(where={"githubPrId": github_pr_id})

                if existing_pr:
                    # Update existing PR
                    await db.pullrequest.update(
                        where={"id": existing_pr.id},
                        data={
                            "status": _get_pr_status(pr_data),
                            "diffSize": pr_data.get("additions", 0) + pr_data.get("deletions", 0),
                            "lastSyncedAt": datetime.utcnow(),
                        },
                    )
                    skipped_count += 1
                else:
                    # Create new PR (missing from webhook)
                    author_github_id = pr_data.get("user", {}).get("id")
                    user = await db.user.find_unique(where={"githubId": author_github_id})

                    if not user:
                        logger.warning("pr_author_not_registered", github_id=author_github_id)
                        continue

                    await db.pullrequest.create(
                        data={
                            "repositoryId": repository.id,
                            "authorId": user.id,
                            "githubPrId": github_pr_id,
                            "prNumber": pr_data.get("number"),
                            "title": pr_data.get("title", ""),
                            "status": _get_pr_status(pr_data),
                            "githubUrl": pr_data.get("html_url", ""),
                            "diffSize": pr_data.get("additions", 0) + pr_data.get("deletions", 0),
                            "openedAt": datetime.fromisoformat(
                                pr_data.get("created_at", "").replace("Z", "+00:00")
                            ),
                            "mergedAt": (
                                datetime.fromisoformat(
                                    pr_data.get("merged_at", "").replace("Z", "+00:00")
                                )
                                if pr_data.get("merged_at")
                                else None
                            ),
                            "closedAt": (
                                datetime.fromisoformat(
                                    pr_data.get("closed_at", "").replace("Z", "+00:00")
                                )
                                if pr_data.get("closed_at")
                                else None
                            ),
                            "lastSyncedAt": datetime.utcnow(),
                        },
                    )
                    synced_count += 1

            # Update repository sync status
            await db.repository.update(
                where={"id": repository_id},
                data={"lastSyncedAt": datetime.utcnow(), "syncStatus": "synced"},
            )

            return {"synced": synced_count, "skipped": skipped_count}

        result = asyncio.run(sync())

        logger.info(
            "repository_prs_synced",
            repository_id=repository_id,
            synced=result["synced"],
            skipped=result["skipped"],
        )

        return result

    except Exception as e:
        logger.error("repository_pr_sync_failed", repository_id=repository_id, error=str(e))
        raise


@shared_task(bind=True)
def detect_stale_prs(self, days_threshold: int = 30) -> dict:
    """
    Detect PRs that have been inactive for X days.

    Args:
        days_threshold: Days of inactivity threshold

    Returns:
        Detection result
    """
    logger.info("detecting_stale_prs", days_threshold=days_threshold, task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def detect():
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

            # Find open PRs not updated since cutoff
            stale_prs = await db.pullrequest.find_many(
                where={
                    "status": "OPEN",
                    "updatedAt": {"lt": cutoff_date},
                }
            )

            stale_count = len(stale_prs)

            # Log stale PRs (don't auto-close without maintainer permission)
            for pr in stale_prs:
                logger.warning(
                    "stale_pr_detected",
                    pr_id=pr.id,
                    pr_number=pr.prNumber,
                    days_inactive=(datetime.utcnow() - pr.updatedAt).days,
                )

            return {"stale_count": stale_count}

        result = asyncio.run(detect())

        logger.info("stale_prs_detected", count=result["stale_count"])

        return result

    except Exception as e:
        logger.error("stale_pr_detection_failed", error=str(e))
        raise


def _get_pr_status(pr_data: dict) -> str:
    """Get PR status from GitHub data."""
    if pr_data.get("merged"):
        return "MERGED"
    elif pr_data.get("state") == "closed":
        return "CLOSED"
    else:
        return "OPEN"
