"""
Initial badge definitions for the platform.
Run this script to seed the database with badge definitions.
"""

import asyncio
import json

from prisma import Prisma


async def seed_badges():
    """Seed database with initial badge definitions."""
    db = Prisma()
    await db.connect()

    badges = [
        # Milestone Badges - PR Count
        {
            "name": "First Contribution",
            "description": "Merged your first pull request! Welcome to the community.",
            "rarity": "COMMON",
            "category": "MILESTONE",
            "criteria": json.dumps({"type": "first_pr"}),
            "version": 1,
        },
        {
            "name": "10 PRs Merged",
            "description": "Successfully merged 10 pull requests. You're building momentum!",
            "rarity": "COMMON",
            "category": "MILESTONE",
            "criteria": json.dumps({"type": "pr_count", "threshold": 10}),
            "version": 1,
        },
        {
            "name": "50 PRs Merged",
            "description": "Merged 50 pull requests. You're a regular contributor!",
            "rarity": "RARE",
            "category": "MILESTONE",
            "criteria": json.dumps({"type": "pr_count", "threshold": 50}),
            "version": 1,
        },
        {
            "name": "100 PRs Merged",
            "description": "Reached 100 merged pull requests. You're a core contributor!",
            "rarity": "EPIC",
            "category": "MILESTONE",
            "criteria": json.dumps({"type": "pr_count", "threshold": 100}),
            "version": 1,
        },
        {
            "name": "500 PRs Merged",
            "description": "An incredible 500 merged pull requests. You're a legend!",
            "rarity": "LEGENDARY",
            "category": "MILESTONE",
            "criteria": json.dumps({"type": "pr_count", "threshold": 500}),
            "version": 1,
        },
        # Quality Badges
        {
            "name": "Quality Contributor",
            "description": "Maintained an average rating of 4.0+ across 10+ merged PRs.",
            "rarity": "RARE",
            "category": "QUALITY",
            "criteria": json.dumps(
                {"type": "quality_rating", "min_rating": 4.0, "min_prs": 10}
            ),
            "version": 1,
        },
        {
            "name": "Excellence Award",
            "description": "Achieved an exceptional 4.5+ average rating across 25+ merged PRs.",
            "rarity": "EPIC",
            "category": "QUALITY",
            "criteria": json.dumps(
                {"type": "quality_rating", "min_rating": 4.5, "min_prs": 25}
            ),
            "version": 1,
        },
        {
            "name": "Perfect Contributor",
            "description": "Maintained a perfect 5.0 average rating across 50+ merged PRs.",
            "rarity": "LEGENDARY",
            "category": "QUALITY",
            "criteria": json.dumps(
                {"type": "quality_rating", "min_rating": 5.0, "min_prs": 50}
            ),
            "version": 1,
        },
        # Streak Badges
        {
            "name": "3-Month Streak",
            "description": "Contributed for 3 consecutive months. Consistency is key!",
            "rarity": "COMMON",
            "category": "STREAK",
            "criteria": json.dumps({"type": "streak", "months": 3}),
            "version": 1,
        },
        {
            "name": "6-Month Streak",
            "description": "Contributed for 6 consecutive months. You're dedicated!",
            "rarity": "RARE",
            "category": "STREAK",
            "criteria": json.dumps({"type": "streak", "months": 6}),
            "version": 1,
        },
        {
            "name": "Year-Long Contributor",
            "description": "Contributed for 12 consecutive months. Truly committed!",
            "rarity": "EPIC",
            "category": "STREAK",
            "criteria": json.dumps({"type": "streak", "months": 12}),
            "version": 1,
        },
        {
            "name": "2-Year Veteran",
            "description": "Contributed for 24 consecutive months. A pillar of the community!",
            "rarity": "LEGENDARY",
            "category": "STREAK",
            "criteria": json.dumps({"type": "streak", "months": 24}),
            "version": 1,
        },
    ]

    created_count = 0
    skipped_count = 0

    for badge_data in badges:
        # Check if badge already exists
        existing = await db.badge.find_unique(where={"name": badge_data["name"]})

        if existing:
            print(f"⏭️  Skipping existing badge: {badge_data['name']}")
            skipped_count += 1
            continue

        # Create badge
        await db.badge.create(data=badge_data)
        print(f"✅ Created badge: {badge_data['name']} ({badge_data['rarity']})")
        created_count += 1

    await db.disconnect()

    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} badges")
    print(f"   Skipped: {skipped_count} badges")
    print(f"   Total: {len(badges)} badges")


if __name__ == "__main__":
    print("🎖️  Seeding badge definitions...\n")
    asyncio.run(seed_badges())
    print("\n✨ Badge seeding complete!")
