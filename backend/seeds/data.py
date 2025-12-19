"""
Deterministic static data for seeding the database.
"""

from typing import Dict, List, Any

# ============================================================================
# USERS
# ============================================================================

DEMO_MAINTAINERS = [
    {
        "github_username": "SarahDev",
        "github_id": 1001,
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah",
        "email": "sarah@example.com",
    },
    {
        "github_username": "AlexCode",
        "github_id": 1002,
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Alex",
        "email": "alex@example.com",
    },
]

DEMO_CONTRIBUTORS = [
    {
        "github_username": "NewbieDev",
        "github_id": 2001,
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Newbie",
        "total_points": 150,
    },
    {
        "github_username": "FullStackNinja",
        "github_id": 2002,
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Ninja",
        "total_points": 2500,
    },
    {
        "github_username": "BugHunter99",
        "github_id": 2003,
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=BugHunter",
        "total_points": 850,
    },
    {
        "github_username": "DocsMaster",
        "github_id": 2004,
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Docs",
        "total_points": 450,
    },
]

# ============================================================================
# PROJECTS & REPOSITORIES
# ============================================================================

DEMO_PROJECTS = [
    {
        "name": "FastWeb Framework",
        "slug": "fastweb-framework",
        "description": "A high-performance web framework for modern apps. Beginner friendly!",
        "difficulty": "Beginner",
        "tags": ["frontend", "javascript", "web"],
        "owner_username": "SarahDev",
        "repositories": [
            {
                "name": "fastweb-core",
                "full_name": "SarahDev/fastweb-core",
                "github_repo_id": 9001,
                "default_branch": "main",
            }
        ],
    },
    {
        "name": "Nexus API Gateway",
        "slug": "nexus-api-gateway",
        "description": "Scalable API gateway for microservices. Written in Go and Python.",
        "difficulty": "Advanced",
        "tags": ["backend", "go", "infrastructure"],
        "owner_username": "AlexCode",
        "repositories": [
            {
                "name": "nexus-gateway",
                "full_name": "AlexCode/nexus-gateway",
                "github_repo_id": 9002,
                "default_branch": "master",
            },
             {
                "name": "nexus-plugins",
                "full_name": "AlexCode/nexus-plugins",
                "github_repo_id": 9003,
                "default_branch": "main",
            }
        ],
    },
    {
        "name": "DevOps CLI Tool",
        "slug": "devops-cli-tool",
        "description": "Automate your deployments with this rusty CLI tool.",
        "difficulty": "Intermediate",
        "tags": ["cli", "rust", "devops"],
        "owner_username": "SarahDev",
        "repositories": [
            {
                "name": "ops-cli",
                "full_name": "SarahDev/ops-cli",
                "github_repo_id": 9004,
                "default_branch": "main",
            }
        ],
    },
]

# ============================================================================
# BADGES
# ============================================================================

DEMO_BADGES = [
    {
        "name": "First Contribution",
        "description": "Merged your first Pull Request.",
        "rarity": "COMMON",
        "category": "MILESTONE",
        "iconUrl": "https://api.iconify.design/heroicons:rocket-launch-solid.svg?color=%233b82f6",
        "criteria": {"type": "PR_COUNT", "threshold": 1},
    },
    {
        "name": "Code Warrior",
        "description": "Merged 10 Pull Requests.",
        "rarity": "RARE",
        "category": "MILESTONE",
        "iconUrl": "https://api.iconify.design/heroicons:shield-check-solid.svg?color=%23a855f7",
        "criteria": {"type": "PR_COUNT", "threshold": 10},
    },
    {
        "name": "Bug Exterminator",
        "description": "Fixed critical bugs in backend systems.",
        "rarity": "EPIC",
        "category": "SPECIAL",
        "iconUrl": "https://api.iconify.design/heroicons:bug-ant-solid.svg?color=%23ef4444",
        "criteria": {"type": "MANUAL", "threshold": 0},
    },
    {
        "name": "Quality Champion",
        "description": "Consistently high quality code reviews.",
        "rarity": "LEGENDARY",
        "category": "QUALITY",
        "iconUrl": "https://api.iconify.design/heroicons:trophy-solid.svg?color=%23eab308",
        "criteria": {"type": "QUALITY_SCORE", "threshold": 4.8},
    },
]

# ============================================================================
# PULL REQUESTS (Templates)
# ============================================================================

# These will be dynamically assigned timestamps in generators.py
DEMO_PR_TEMPLATES = [
    {"title": "Fix typo in documentation", "diff_size": 12, "score": 10},
    {"title": "Add new API endpoint for user profile", "diff_size": 150, "score": 80},
    {"title": "Refactor authentication middleware", "diff_size": 300, "score": 150},
    {"title": "Update dependencies", "diff_size": 45, "score": 20},
    {"title": "Fix memory leak in worker", "diff_size": 80, "score": 120},
    {"title": "Add unit tests for payment service", "diff_size": 220, "score": 100},
    {"title": "Improve error handling", "diff_size": 60, "score": 50},
    {"title": "Setup CI pipeline", "diff_size": 120, "score": 90},
]
