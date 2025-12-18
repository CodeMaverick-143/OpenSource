"""
Redis caching layer for leaderboards.
"""

import json
from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


class LeaderboardCache:
    """
    Redis caching for fast leaderboard lookups.

    Cache Keys:
    - leaderboard:global:top100
    - leaderboard:monthly:2025-01:top100
    - leaderboard:project:{project_id}:top50
    - user:rank:{user_id}:global

    TTLs:
    - Leaderboards: 5 minutes
    - User ranks: 1 minute
    """

    def __init__(self, redis_client):
        """
        Initialize cache.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.leaderboard_ttl = 300  # 5 minutes
        self.rank_ttl = 60  # 1 minute

    async def get_leaderboard(
        self, leaderboard_type: str, period: Optional[str] = None, limit: int = 100
    ) -> Optional[List[dict]]:
        """
        Get leaderboard from cache.

        Args:
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            period: Period identifier
            limit: Number of users

        Returns:
            Cached leaderboard or None
        """
        key = self._get_leaderboard_key(leaderboard_type, period, limit)

        try:
            cached = await self.redis.get(key)
            if cached:
                logger.debug("leaderboard_cache_hit", key=key)
                return json.loads(cached)
        except Exception as e:
            logger.error("leaderboard_cache_get_error", key=key, error=str(e))

        return None

    async def set_leaderboard(
        self,
        leaderboard_type: str,
        data: List[dict],
        period: Optional[str] = None,
        limit: int = 100,
    ) -> None:
        """
        Set leaderboard in cache.

        Args:
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            data: Leaderboard data
            period: Period identifier
            limit: Number of users
        """
        key = self._get_leaderboard_key(leaderboard_type, period, limit)

        try:
            await self.redis.setex(key, self.leaderboard_ttl, json.dumps(data))
            logger.debug("leaderboard_cache_set", key=key)
        except Exception as e:
            logger.error("leaderboard_cache_set_error", key=key, error=str(e))

    async def get_user_rank(
        self, user_id: str, leaderboard_type: str, period: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get user rank from cache.

        Args:
            user_id: User ID
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            period: Period identifier

        Returns:
            Cached rank or None
        """
        key = self._get_rank_key(user_id, leaderboard_type, period)

        try:
            cached = await self.redis.get(key)
            if cached:
                logger.debug("rank_cache_hit", key=key)
                return json.loads(cached)
        except Exception as e:
            logger.error("rank_cache_get_error", key=key, error=str(e))

        return None

    async def set_user_rank(
        self,
        user_id: str,
        leaderboard_type: str,
        rank_data: dict,
        period: Optional[str] = None,
    ) -> None:
        """
        Set user rank in cache.

        Args:
            user_id: User ID
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            rank_data: Rank data
            period: Period identifier
        """
        key = self._get_rank_key(user_id, leaderboard_type, period)

        try:
            await self.redis.setex(key, self.rank_ttl, json.dumps(rank_data))
            logger.debug("rank_cache_set", key=key)
        except Exception as e:
            logger.error("rank_cache_set_error", key=key, error=str(e))

    async def invalidate_leaderboard(
        self, leaderboard_type: str, period: Optional[str] = None
    ) -> None:
        """
        Invalidate leaderboard cache.

        Args:
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL
            period: Period identifier
        """
        # Delete all cached leaderboards for this type/period
        pattern = f"leaderboard:{leaderboard_type.lower()}"
        if period:
            pattern += f":{period}"
        pattern += ":*"

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info("leaderboard_cache_invalidated", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.error("leaderboard_cache_invalidate_error", pattern=pattern, error=str(e))

    async def invalidate_user_rank(
        self, user_id: str, leaderboard_type: Optional[str] = None
    ) -> None:
        """
        Invalidate user rank cache.

        Args:
            user_id: User ID
            leaderboard_type: GLOBAL, MONTHLY, PROJECT, SKILL (None = all)
        """
        if leaderboard_type:
            pattern = f"user:rank:{user_id}:{leaderboard_type.lower()}:*"
        else:
            pattern = f"user:rank:{user_id}:*"

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info("rank_cache_invalidated", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.error("rank_cache_invalidate_error", pattern=pattern, error=str(e))

    def _get_leaderboard_key(self, leaderboard_type: str, period: Optional[str], limit: int) -> str:
        """Generate leaderboard cache key."""
        key = f"leaderboard:{leaderboard_type.lower()}"
        if period:
            key += f":{period}"
        key += f":top{limit}"
        return key

    def _get_rank_key(self, user_id: str, leaderboard_type: str, period: Optional[str]) -> str:
        """Generate rank cache key."""
        key = f"user:rank:{user_id}:{leaderboard_type.lower()}"
        if period:
            key += f":{period}"
        return key
