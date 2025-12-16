"""
GitHub OAuth client for authentication.
"""

from typing import Optional
from urllib.parse import urlencode

import httpx
import structlog

from backend.core.config import settings
from backend.core.exceptions import ContriVerseException

logger = structlog.get_logger(__name__)


class GitHubOAuthClient:
    """GitHub OAuth client for handling authentication flow."""

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"
    USER_EMAILS_API_URL = "https://api.github.com/user/emails"

    def __init__(self):
        """Initialize GitHub OAuth client."""
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = settings.GITHUB_REDIRECT_URI

    def get_authorization_url(self, state: str) -> str:
        """
        Generate GitHub OAuth authorization URL.

        Args:
            state: CSRF protection state parameter

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }

        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        logger.info("github_auth_url_generated", state=state)

        return url

    async def exchange_code_for_token(self, code: str) -> str:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from GitHub

        Returns:
            GitHub access token

        Raises:
            ContriVerseException: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Accept": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL, data=data, headers=headers, timeout=10.0
                )
                response.raise_for_status()

                result = response.json()

                if "error" in result:
                    logger.error(
                        "github_token_exchange_error",
                        error=result.get("error"),
                        error_description=result.get("error_description"),
                    )
                    raise ContriVerseException(
                        "Failed to exchange code for token", status_code=400
                    )

                access_token = result.get("access_token")
                if not access_token:
                    logger.error("github_token_missing", result=result)
                    raise ContriVerseException("No access token in response", status_code=400)

                logger.info("github_token_exchanged_successfully")
                return access_token

        except httpx.HTTPError as e:
            logger.error("github_token_exchange_http_error", error=str(e))
            raise ContriVerseException("GitHub API request failed", status_code=503)

    async def get_user_profile(self, access_token: str) -> dict:
        """
        Fetch GitHub user profile.

        Args:
            access_token: GitHub access token

        Returns:
            User profile data

        Raises:
            ContriVerseException: If profile fetch fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                # Fetch user profile
                user_response = await client.get(
                    self.USER_API_URL, headers=headers, timeout=10.0
                )
                user_response.raise_for_status()
                user_data = user_response.json()

                # Fetch user emails (email may not be in profile)
                try:
                    emails_response = await client.get(
                        self.USER_EMAILS_API_URL, headers=headers, timeout=10.0
                    )
                    emails_response.raise_for_status()
                    emails_data = emails_response.json()

                    # Find primary verified email
                    primary_email = next(
                        (
                            email["email"]
                            for email in emails_data
                            if email.get("primary") and email.get("verified")
                        ),
                        None,
                    )

                    if primary_email:
                        user_data["email"] = primary_email

                except httpx.HTTPError:
                    logger.warning("github_emails_fetch_failed")
                    # Continue without email - it's optional

                logger.info(
                    "github_user_profile_fetched",
                    github_id=user_data.get("id"),
                    username=user_data.get("login"),
                )

                return user_data

        except httpx.HTTPError as e:
            logger.error("github_user_profile_fetch_error", error=str(e))
            raise ContriVerseException("Failed to fetch GitHub user profile", status_code=503)

    async def verify_token(self, access_token: str) -> bool:
        """
        Verify if a GitHub access token is still valid.

        Args:
            access_token: GitHub access token

        Returns:
            True if token is valid
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.USER_API_URL, headers=headers, timeout=10.0)
                return response.status_code == 200

        except httpx.HTTPError:
            return False


# Global OAuth client instance
github_oauth_client = GitHubOAuthClient()
