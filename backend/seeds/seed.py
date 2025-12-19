"""
Main seed script for populating demo data.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
import random
import os
from dotenv import load_dotenv

# Load environment variables from root directory (parent of parent of seeds)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

from prisma import Prisma, Json
from .data import (
    DEMO_BADGES,
    DEMO_CONTRIBUTORS,
    DEMO_MAINTAINERS,
    DEMO_PROJECTS,
    DEMO_PR_TEMPLATES,
)
from .generators import generate_deterministic_id, generate_timestamps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_badges(prisma: Prisma) -> None:
    """Seed badge definitions."""
    logger.info("Seeding badges...")
    for badge_data in DEMO_BADGES:
        badge_id = generate_deterministic_id(f"badge_{badge_data['name']}")
        
        # Prepare data with properly typed Json fields
        data_payload = badge_data.copy()
        if "criteria" in data_payload:
            data_payload["criteria"] = Json(data_payload["criteria"])
            
        await prisma.badge.upsert(
            where={"name": badge_data["name"]},
            data={
                "create": {
                    "id": badge_id,
                    **data_payload,
                    "isActive": True,
                },
                "update": {
                    **data_payload,
                },
            },
        )
    logger.info(f"Seeded {len(DEMO_BADGES)} badges.")

async def seed_users(prisma: Prisma) -> dict:
    """Seed maintainers and contributors."""
    logger.info("Seeding users...")
    users_map = {}

    all_users = DEMO_MAINTAINERS + DEMO_CONTRIBUTORS
    
    for user_data in all_users:
        user_id = generate_deterministic_id(f"user_{user_data['github_username']}")
        
        # Upsert user
        user = await prisma.user.upsert(
            where={"githubId": user_data["github_id"]},
            data={
                "create": {
                    "id": user_id,
                    "githubId": user_data["github_id"],
                    "githubUsername": user_data["github_username"],
                    "avatarUrl": user_data["avatar_url"],
                    "email": user_data.get("email"),
                    "totalPoints": user_data.get("total_points", 0),
                    "isDemo": True,
                },
                "update": {
                    "githubUsername": user_data["github_username"],
                    "avatarUrl": user_data["avatar_url"],
                    "totalPoints": user_data.get("total_points", 0),
                    "isDemo": True,
                },
            },
        )
        users_map[user_data["github_username"]] = user.id
        
    logger.info(f"Seeded {len(users_map)} users.")
    return users_map

async def seed_projects(prisma: Prisma, users_map: dict) -> dict:
    """Seed projects and repositories."""
    logger.info("Seeding projects...")
    repo_map = {}
    
    for project_data in DEMO_PROJECTS:
        owner_id = users_map[project_data["owner_username"]]
        project_id = generate_deterministic_id(f"project_{project_data['slug']}")
        
        # Upsert Project
        project = await prisma.project.upsert(
            where={"slug": project_data["slug"]},
            data={
                "create": {
                    "id": project_id,
                    "name": project_data["name"],
                    "slug": project_data["slug"],
                    "description": project_data["description"],
                    "difficulty": project_data["difficulty"],
                    "tags": project_data["tags"],
                    "ownerId": owner_id,
                    "isActive": True,
                    "isDemo": True,
                },
                "update": {
                    "name": project_data["name"],
                    "description": project_data["description"],
                    "difficulty": project_data["difficulty"],
                    "tags": project_data["tags"],
                    "isDemo": True,
                },
            },
        )
        
        # Link owner as maintainer
        maintainer_id = generate_deterministic_id(f"maintainer_{project.id}_{owner_id}")
        await prisma.projectmaintainer.upsert(
            where={
                "projectId_userId": {
                    "projectId": project.id,
                    "userId": owner_id,
                }
            },
            data={
                "create": {
                    "id": maintainer_id,
                    "projectId": project.id,
                    "userId": owner_id,
                    "role": "owner",
                },
                "update": {"role": "owner"},
            },
        )

        # Seed Repositories
        for repo_data in project_data["repositories"]:
            repo_id = generate_deterministic_id(f"repo_{repo_data['github_repo_id']}")
            repo = await prisma.repository.upsert(
                where={"githubRepoId": repo_data["github_repo_id"]},
                data={
                    "create": {
                        "id": repo_id,
                        "projectId": project.id,
                        "githubRepoId": repo_data["github_repo_id"],
                        "name": repo_data["name"],
                        "fullName": repo_data["full_name"],
                        "defaultBranch": repo_data["default_branch"],
                        "isActive": True,
                        "isDemo": True,
                    },
                    "update": {
                        "projectId": project.id,
                        "name": repo_data["name"],
                        "fullName": repo_data["full_name"],
                        "isDemo": True,
                    },
                },
            )
            repo_map[repo.id] = repo
            
    logger.info(f"Seeded {len(DEMO_PROJECTS)} projects.")
    return repo_map

async def seed_prs(prisma: Prisma, repo_map: dict, users_map: dict) -> None:
    """Seed historical PRs for repositories."""
    logger.info("Seeding PRs...")
    
    # Use a fixed seed for PR generation stability
    rng = random.Random(123)
    start_date = datetime.now(timezone.utc) - timedelta(days=180)
    
    contributor_usernames = [u["github_username"] for u in DEMO_CONTRIBUTORS]
    
    pr_count = 0
    
    for repo_id, repo in repo_map.items():
        # Generate 5-10 PRs per repo
        num_prs = rng.randint(5, 10)
        repo_timestamps = generate_timestamps(start_date, num_prs)
        
        for i in range(num_prs):
            template = rng.choice(DEMO_PR_TEMPLATES)
            author_username = rng.choice(contributor_usernames)
            author_id = users_map[author_username]
            
            pr_number = 100 + i
            github_pr_id = repo.githubRepoId * 1000 + pr_number
            
            pr_id = generate_deterministic_id(f"pr_{github_pr_id}")
            created_at = repo_timestamps[i]
            
            # Determine status based on random chance
            status_roll = rng.random()
            if status_roll < 0.6:
                status = "MERGED"
                merged_at = created_at + timedelta(hours=rng.randint(24, 72))
                closed_at = merged_at
            elif status_roll < 0.8:
                status = "OPEN"
                merged_at = None
                closed_at = None
            elif status_roll < 0.9:
                status = "CLOSED"
                merged_at = None
                closed_at = created_at + timedelta(hours=rng.randint(12, 48))
            else:
                status = "UNDER_REVIEW"
                merged_at = None
                closed_at = None

            await prisma.pullrequest.upsert(
                where={"githubPrId": github_pr_id},
                data={
                    "create": {
                        "id": pr_id,
                        "repositoryId": repo.id,
                        "authorId": author_id,
                        "githubPrId": github_pr_id,
                        "prNumber": pr_number,
                        "title": template["title"],
                        "status": status,
                        "score": template["score"],
                        "diffSize": template["diff_size"],
                        "githubUrl": f"https://github.com/{repo.fullName}/pull/{pr_number}",
                        "openedAt": created_at,
                        "mergedAt": merged_at,
                        "closedAt": closed_at,
                        "isDemo": True,
                    },
                    "update": {
                        "status": status,
                        "score": template["score"],
                        "isDemo": True,
                    }
                }
            )
            pr_count += 1
            
    logger.info(f"Seeded {pr_count} PRs.")

async def main() -> None:
    prisma = Prisma()
    await prisma.connect()
    
    try:
        await seed_badges(prisma)
        users_map = await seed_users(prisma)
        repo_map = await seed_projects(prisma, users_map)
        await seed_prs(prisma, repo_map, users_map)
        
        logger.info("Seed completed successfully! 🌱")
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        raise
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
