"""
Quick verification script for dashboard API endpoints.
"""

import asyncio

from prisma import Prisma

from backend.services.contribution_graph_service import ContributionGraphService
from backend.services.dashboard_service import DashboardService
from backend.services.skill_tagger import SkillTagger


async def test_dashboard_services():
    """Test dashboard services with a sample user."""
    db = Prisma()
    await db.connect()

    try:
        # Find a user with PRs
        user = await db.user.find_first(
            where={"isBanned": False, "isDeleted": False},
            include={"pullRequests": True},
        )

        if not user:
            print("❌ No users found in database")
            return

        print(f"✅ Testing with user: {user.githubUsername} (ID: {user.id})")
        print(f"   Total PRs: {len(user.pullRequests)}")
        print()

        # Test DashboardService
        print("Testing DashboardService...")
        dashboard_service = DashboardService(db)

        # Test get_user_prs
        prs_result = await dashboard_service.get_user_prs(user_id=user.id, limit=5)
        print(f"  ✅ get_user_prs: {prs_result['total']} total PRs, showing {len(prs_result['items'])}")

        # Test get_points_history
        points_result = await dashboard_service.get_points_history(user_id=user.id, limit=5)
        print(f"  ✅ get_points_history: {points_result['total']} total transactions")

        # Test get_user_badges
        badges_result = await dashboard_service.get_user_badges(user_id=user.id)
        print(
            f"  ✅ get_user_badges: {len(badges_result['earned'])} earned, {len(badges_result['available'])} available"
        )

        # Test get_user_rank_info
        rank_result = await dashboard_service.get_user_rank_info(user_id=user.id)
        if rank_result:
            print(f"  ✅ get_user_rank_info: Rank #{rank_result['rank']}")
        else:
            print("  ⚠️  get_user_rank_info: No rank snapshot available")

        # Test get_dashboard_stats
        stats_result = await dashboard_service.get_dashboard_stats(user_id=user.id)
        print(f"  ✅ get_dashboard_stats: {stats_result['total_prs']} PRs, {stats_result['total_points']} points")

        print()

        # Test ContributionGraphService
        print("Testing ContributionGraphService...")
        contribution_service = ContributionGraphService(db)

        graph_result = await contribution_service.generate_contribution_graph(
            user_id=user.id, range_type="30d"
        )
        print(
            f"  ✅ generate_contribution_graph: {graph_result['stats']['total_contributions']} contributions"
        )

        print()

        # Test SkillTagger
        print("Testing SkillTagger...")
        skill_service = SkillTagger(db)

        skills_result = await skill_service.get_top_skills(user_id=user.id, limit=5)
        print(f"  ✅ get_top_skills: {len(skills_result['skills'])} skills")
        if skills_result["skills"]:
            for skill in skills_result["skills"][:3]:
                print(f"     - {skill['name']}: {skill['weight']} ({skill['contribution_count']} contributions)")

        print()
        print("✅ All dashboard services working correctly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(test_dashboard_services())
