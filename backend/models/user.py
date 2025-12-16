"""
User model - GitHub ID as immutable primary identity.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User model with GitHub as single source of truth.

    Key principles:
    - github_id is immutable and primary identity
    - github_username is mutable (can change on GitHub)
    - Never use username as identity reference
    - Email is optional (user may not make it public)
    """

    __tablename__ = "users"

    # Primary identity - immutable GitHub ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    github_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )

    # Mutable GitHub profile data (updated on every login)
    github_username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Account state flags
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Contribution metrics (to be populated later)
    total_points: Mapped[int] = mapped_column(default=0, nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, github_id={self.github_id}, username={self.github_username})>"

    @property
    def is_active(self) -> bool:
        """Check if user is active (not banned and not deleted)."""
        return not self.is_banned and not self.is_deleted
