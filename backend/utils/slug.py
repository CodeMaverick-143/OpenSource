"""Utility functions for generating URL-safe slugs."""

import re
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


def generate_slug(text: str, max_length: int = 255) -> str:
    """
    Generate a URL-safe slug from text.

    Args:
        text: Input text
        max_length: Maximum slug length

    Returns:
        URL-safe slug

    Examples:
        >>> generate_slug("My Awesome Project!")
        "my-awesome-project"
        >>> generate_slug("React.js & TypeScript")
        "reactjs-typescript"
    """
    # Convert to lowercase
    slug = text.lower()

    # Replace spaces and special characters with hyphens
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug


def ensure_unique_slug(base_slug: str, existing_slugs: list[str]) -> str:
    """
    Ensure slug is unique by appending a number if necessary.

    Args:
        base_slug: Base slug
        existing_slugs: List of existing slugs

    Returns:
        Unique slug

    Examples:
        >>> ensure_unique_slug("my-project", ["my-project"])
        "my-project-2"
        >>> ensure_unique_slug("my-project", ["my-project", "my-project-2"])
        "my-project-3"
    """
    if base_slug not in existing_slugs:
        return base_slug

    # Find next available number
    counter = 2
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1

    return f"{base_slug}-{counter}"


async def generate_unique_project_slug(name: str, db) -> str:
    """
    Generate a unique project slug.

    Args:
        name: Project name
        db: Prisma client

    Returns:
        Unique slug
    """
    base_slug = generate_slug(name)

    # Check if slug exists
    existing = await db.project.find_unique(where={"slug": base_slug})

    if not existing:
        return base_slug

    # Find all slugs with same base
    projects = await db.project.find_many(
        where={"slug": {"startswith": base_slug}}, select={"slug": True}
    )

    existing_slugs = [p.slug for p in projects]

    unique_slug = ensure_unique_slug(base_slug, existing_slugs)

    logger.info("generated_unique_slug", base_slug=base_slug, unique_slug=unique_slug)

    return unique_slug
