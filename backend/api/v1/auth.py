"""
Authentication API endpoints.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_active_user
from backend.core.exceptions import ContriVerseException
from backend.core.security import create_oauth_state
from backend.db.session import get_db
from backend.models.user import User
from backend.services.auth_service import AuthService

router = APIRouter(tags=["authentication"])
logger = structlog.get_logger(__name__)


# Pydantic models for request/response
class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response model."""

    id: int
    github_id: int
    github_username: str
    avatar_url: str | None
    email: str | None
    total_points: int
    rank: int | None

    class Config:
        from_attributes = True


# OAuth state storage (in production, use Redis)
# For now, we'll use a simple in-memory dict
oauth_states: dict[str, bool] = {}


@router.get("/github/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def github_login() -> RedirectResponse:
    """
    Initiate GitHub OAuth flow.

    Returns:
        Redirect to GitHub authorization page
    """
    from backend.core.oauth import github_oauth_client

    # Generate CSRF state token
    state = create_oauth_state()

    # Store state for validation (expires in 10 minutes)
    oauth_states[state] = True

    # Generate authorization URL
    auth_url = github_oauth_client.get_authorization_url(state)

    logger.info("github_oauth_initiated", state=state)

    return RedirectResponse(url=auth_url)


@router.get("/github/callback", response_model=TokenResponse)
async def github_callback(
    code: str = Query(..., description="GitHub OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Handle GitHub OAuth callback.

    Args:
        code: Authorization code from GitHub
        state: OAuth state parameter for CSRF protection
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If OAuth flow fails
    """
    # Validate state parameter (CSRF protection)
    if state not in oauth_states:
        logger.warning("invalid_oauth_state", state=state)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter",
        )

    # Remove used state
    del oauth_states[state]

    try:
        # Authenticate with GitHub
        auth_service = AuthService(db)
        access_token, refresh_token, user = await auth_service.authenticate_with_github(code)

        logger.info(
            "github_oauth_completed",
            user_id=user.id,
            github_id=user.github_id,
            username=user.github_username,
        )

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    except ContriVerseException as e:
        logger.error("github_oauth_failed", error=str(e))
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception("github_oauth_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token request
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh fails
    """
    try:
        auth_service = AuthService(db)
        access_token, new_refresh_token = await auth_service.refresh_access_token(
            request.refresh_token
        )

        logger.info("token_refreshed")

        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)

    except ValueError as e:
        logger.warning("token_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )
    except Exception as e:
        logger.exception("token_refresh_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh failed"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> None:
    """
    Logout user by invalidating refresh token.

    Args:
        request: Refresh token request
        db: Database session
    """
    try:
        auth_service = AuthService(db)
        await auth_service.logout(request.refresh_token)

        logger.info("user_logout_completed")

    except Exception as e:
        logger.warning("logout_error", error=str(e))
        # Don't fail logout even if token is invalid
        pass


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    logger.debug("user_info_requested", user_id=current_user.id)

    return UserResponse.model_validate(current_user)
