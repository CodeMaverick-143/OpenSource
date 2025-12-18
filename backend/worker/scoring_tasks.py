"""
Celery tasks for scoring and leaderboard management.
"""

from datetime import datetime

import structlog
from celery import shared_task

from backend.db.prisma_client import get_prisma_client
from backend.services.gaming_detector import GamingDetector
from backend.services.leaderboard_service import LeaderboardService
from backend.services.rank_calculator import RankCalculator

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def recalculate_global_ranks(self) -> dict:
    """
    Recalculate global ranks and save snapshot.

    Returns:
        Calculation result
    """
    logger.info("recalculating_global_ranks", task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def calculate():
            calculator = RankCalculator(db)

            # Calculate ranks
            ranks = await calculator.calculate_global_ranks()

            # Save snapshot
            await calculator.save_rank_snapshot(leaderboard_type="GLOBAL", ranks=ranks)

            # Save leaderboard snapshot
            leaderboard_service = LeaderboardService(db)
            await leaderboard_service.save_leaderboard_snapshot(
                leaderboard_type="GLOBAL", top_users=ranks[:1000]  # Top 1000
            )

            return {"total_users": len(ranks)}

        result = asyncio.run(calculate())

        logger.info("global_ranks_recalculated", total_users=result["total_users"])

        return result

    except Exception as e:
        logger.error("global_ranks_recalculation_failed", error=str(e))
        raise


@shared_task(bind=True)
def generate_monthly_leaderboard_snapshot(self, year: int, month: int) -> dict:
    """
    Generate monthly leaderboard snapshot.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Generation result
    """
    logger.info(
        "generating_monthly_leaderboard_snapshot",
        year=year,
        month=month,
        task_id=self.request.id,
    )

    try:
        import asyncio

        db = get_prisma_client()

        async def generate():
            calculator = RankCalculator(db)

            # Calculate monthly ranks
            ranks = await calculator.calculate_monthly_ranks(year, month)

            period = f"{year}-{month:02d}"

            # Save snapshot
            await calculator.save_rank_snapshot(
                leaderboard_type="MONTHLY", ranks=ranks, period=period
            )

            # Save leaderboard snapshot
            leaderboard_service = LeaderboardService(db)
            await leaderboard_service.save_leaderboard_snapshot(
                leaderboard_type="MONTHLY", top_users=ranks[:500], period=period
            )

            return {"total_users": len(ranks), "period": period}

        result = asyncio.run(generate())

        logger.info(
            "monthly_leaderboard_snapshot_generated",
            period=result["period"],
            total_users=result["total_users"],
        )

        return result

    except Exception as e:
        logger.error("monthly_leaderboard_snapshot_generation_failed", error=str(e))
        raise


@shared_task(bind=True)
def detect_gaming_patterns(self) -> dict:
    """
    Detect gaming patterns across all recent PRs.

    Returns:
        Detection result
    """
    logger.info("detecting_gaming_patterns", task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def detect():
            # Get recent PRs (last 7 days)
            from datetime import timedelta

            cutoff = datetime.utcnow() - timedelta(days=7)

            prs = await db.pullrequest.find_many(
                where={"createdAt": {"gte": cutoff}}, include={"author": True}
            )

            detector = GamingDetector(db)
            gaming_count = 0

            for pr in prs:
                result = await detector.run_all_checks(pr.id, pr.authorId, pr.repositoryId)

                if result["has_gaming"]:
                    gaming_count += 1

                    logger.warning(
                        "gaming_pattern_detected",
                        pr_id=pr.id,
                        user_id=pr.authorId,
                        patterns=result,
                    )

            return {"prs_checked": len(prs), "gaming_detected": gaming_count}

        result = asyncio.run(detect())

        logger.info(
            "gaming_patterns_detected",
            prs_checked=result["prs_checked"],
            gaming_count=result["gaming_detected"],
        )

        return result

    except Exception as e:
        logger.error("gaming_pattern_detection_failed", error=str(e))
        raise


@shared_task(bind=True)
def warm_leaderboard_cache(self) -> dict:
    """
    Warm leaderboard cache with top leaderboards.

    Returns:
        Warming result
    """
    logger.info("warming_leaderboard_cache", task_id=self.request.id)

    try:
        import asyncio

        db = get_prisma_client()

        async def warm():
            leaderboard_service = LeaderboardService(db)

            # Warm global leaderboard
            global_lb = await leaderboard_service.get_global_leaderboard(limit=100)

            # Warm current month leaderboard
            now = datetime.utcnow()
            monthly_lb = await leaderboard_service.get_monthly_leaderboard(
                year=now.year, month=now.month, limit=100
            )

            return {"global": len(global_lb["users"]), "monthly": len(monthly_lb["users"])}

        result = asyncio.run(warm())

        logger.info("leaderboard_cache_warmed", result=result)

        return result

    except Exception as e:
        logger.error("leaderboard_cache_warming_failed", error=str(e))
        raise
