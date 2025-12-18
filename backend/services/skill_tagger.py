"""
Skill tagger service for computing user skill tags.
"""

from typing import Dict, List

import structlog

from prisma import Prisma

logger = structlog.get_logger(__name__)


class SkillTagger:
    """Service for computing and weighting user skill tags."""

    def __init__(self, db: Prisma):
        """Initialize service."""
        self.db = db

    async def compute_user_skills(self, user_id: str, top_n: int = 10) -> List[Dict]:
        """
        Compute user's skill tags based on project tags and contribution history.

        Args:
            user_id: User ID
            top_n: Number of top skills to return

        Returns:
            List of skill dictionaries with name, weight, and contribution count
        """
        logger.info("computing_user_skills", user_id=user_id, top_n=top_n)

        # Fetch user's PRs with project tags
        prs = await self.db.pullrequest.find_many(
            where={"authorId": user_id, "status": "MERGED"},
            include={"repository": {"include": {"project": True}}},
        )

        # Aggregate skills by project tags
        skill_data: Dict[str, Dict] = {}

        for pr in prs:
            if pr.repository and pr.repository.project:
                project = pr.repository.project
                tags = project.tags if project.tags else []

                for tag in tags:
                    if tag not in skill_data:
                        skill_data[tag] = {"count": 0, "total_points": 0}

                    skill_data[tag]["count"] += 1
                    skill_data[tag]["total_points"] += pr.score

        # Weight skills by impact (combination of count and points)
        skills = await self._weight_skills_by_impact(skill_data)

        # Sort by weight and return top N
        skills_sorted = sorted(skills, key=lambda x: x["weight"], reverse=True)
        top_skills = skills_sorted[:top_n]

        logger.info(
            "user_skills_computed",
            user_id=user_id,
            total_skills=len(skills),
            top_skills_count=len(top_skills),
        )

        return top_skills

    async def _weight_skills_by_impact(self, skill_data: Dict[str, Dict]) -> List[Dict]:
        """
        Weight skills by contribution impact.

        Args:
            skill_data: Dictionary of skill -> {count, total_points}

        Returns:
            List of weighted skills
        """
        if not skill_data:
            return []

        # Find max values for normalization
        max_count = max(data["count"] for data in skill_data.values())
        max_points = max(data["total_points"] for data in skill_data.values())

        skills = []
        for skill_name, data in skill_data.items():
            # Normalize count and points to 0-1 range
            normalized_count = data["count"] / max_count if max_count > 0 else 0
            normalized_points = data["total_points"] / max_points if max_points > 0 else 0

            # Weight: 60% contribution count, 40% total points
            weight = (0.6 * normalized_count) + (0.4 * normalized_points)

            skills.append(
                {
                    "name": skill_name,
                    "weight": round(weight, 2),
                    "contribution_count": data["count"],
                }
            )

        return skills

    async def get_top_skills(self, user_id: str, limit: int = 5) -> Dict:
        """
        Get user's top skills.

        Args:
            user_id: User ID
            limit: Number of skills to return

        Returns:
            Dictionary with skills list
        """
        logger.info("fetching_top_skills", user_id=user_id, limit=limit)

        skills = await self.compute_user_skills(user_id, top_n=limit)

        logger.info("top_skills_fetched", user_id=user_id, skills_count=len(skills))

        return {"skills": skills}
