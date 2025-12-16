"""
JWT token utilities for authentication.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import settings

logger = structlog.get_logger(__name__)

# Password hashing context (for token hashing)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: int, github_id: int) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: Internal user ID
        github_id: GitHub user ID

    Returns:
        Encoded JWT token
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user_id),
        "github_id": github_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.debug("access_token_created", user_id=user_id, expires_at=expire.isoformat())

    return encoded_jwt


def create_refresh_token() -> str:
    """
    Create a cryptographically secure refresh token.

    Returns:
        Random token string
    """
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.

    Args:
        token: Token to hash

    Returns:
        Hashed token
    """
    return pwd_context.hash(token)


def verify_token_hash(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a token against its hash.

    Args:
        plain_token: Plain text token
        hashed_token: Hashed token

    Returns:
        True if token matches hash
    """
    return pwd_context.verify(plain_token, hashed_token)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token to decode

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Verify token type
        if payload.get("type") != "access":
            logger.warning("invalid_token_type", token_type=payload.get("type"))
            return None

        # Verify expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            logger.debug("token_expired", exp=exp)
            return None

        return payload

    except JWTError as e:
        logger.warning("jwt_decode_error", error=str(e))
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    Extract user ID from JWT token.

    Args:
        token: JWT token

    Returns:
        User ID if valid, None otherwise
    """
    payload = decode_access_token(token)
    if not payload:
        return None

    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        logger.warning("invalid_user_id_in_token", sub=payload.get("sub"))
        return None


def create_oauth_state() -> str:
    """
    Create a secure OAuth state parameter for CSRF protection.

    Returns:
        Random state string
    """
    return secrets.token_urlsafe(32)
