"""
GitHub REST API client with rate limiting, pagination, and error handling.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import structlog

from backend.core.config import settings

logger = structlog.get_logger(__name__)


class GitHubRateLimitError(Exception):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(self, reset_at: datetime, remaining: int = 0):
        self.reset_at = reset_at
        self.remaining = remaining
        super().__init__(f"Rate limit exceeded. Resets at {reset_at.isoformat()}")


class GitHubAPIError(Exception):
    """Raised when GitHub API returns an error."""

    def __init__(self, status_code: int, message: str, response: dict = None):
        self.status_code = status_code
        self.message = message
        self.response = response or {}
        super().__init__(f"GitHub API error {status_code}: {message}")


class GitHubRESTClient:
    """
    GitHub REST API client with production-grade features:
    - OAuth and GitHub App authentication
    - Automatic pagination
    - Conditional requests (ETags)
    - Rate limit handling
    - Exponential backoff retry
    """

    BASE_URL = "https://api.github.com"
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # seconds

    def __init__(self, access_token: str, token_type: str = "oauth"):
        """
        Initialize GitHub REST client.

        Args:
            access_token: GitHub OAuth token or App token
            token_type: "oauth" or "app"
        """
        self.access_token = access_token
        self.token_type = token_type
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[datetime] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self._get_headers(),
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.token_type == "oauth":
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.token_type == "app":
            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers

    def _update_rate_limit(self, headers: httpx.Headers) -> None:
        """Update rate limit info from response headers."""
        try:
            self._rate_limit_remaining = int(headers.get("x-ratelimit-remaining", 0))
            reset_timestamp = int(headers.get("x-ratelimit-reset", 0))
            self._rate_limit_reset = datetime.fromtimestamp(reset_timestamp)

            logger.debug(
                "github_rate_limit_updated",
                remaining=self._rate_limit_remaining,
                reset_at=self._rate_limit_reset.isoformat(),
            )
        except (ValueError, TypeError) as e:
            logger.warning("failed_to_parse_rate_limit_headers", error=str(e))

    async def _check_rate_limit(self) -> None:
        """Check if we're approaching rate limit and throttle if needed."""
        if self._rate_limit_remaining is not None and self._rate_limit_remaining < 10:
            if self._rate_limit_reset and datetime.now() < self._rate_limit_reset:
                wait_seconds = (self._rate_limit_reset - datetime.now()).total_seconds()
                logger.warning(
                    "github_rate_limit_low",
                    remaining=self._rate_limit_remaining,
                    wait_seconds=wait_seconds,
                )

                # If very close to limit, wait
                if self._rate_limit_remaining < 5:
                    logger.info("github_rate_limit_throttling", wait_seconds=wait_seconds)
                    await asyncio.sleep(min(wait_seconds, 60))  # Max 60s wait

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        etag: Optional[str] = None,
        retry_count: int = 0,
    ) -> tuple[dict | list, httpx.Headers]:
        """
        Make HTTP request to GitHub API with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json: JSON body
            etag: ETag for conditional requests
            retry_count: Current retry attempt

        Returns:
            Tuple of (response data, headers)

        Raises:
            GitHubRateLimitError: If rate limit exceeded
            GitHubAPIError: If API returns error
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Check rate limit before request
        await self._check_rate_limit()

        # Add ETag header if provided
        headers = {}
        if etag:
            headers["If-None-Match"] = etag

        try:
            response = await self._client.request(
                method, endpoint, params=params, json=json, headers=headers
            )

            # Update rate limit info
            self._update_rate_limit(response.headers)

            # Handle rate limit
            if response.status_code == 429 or response.status_code == 403:
                if "x-ratelimit-remaining" in response.headers:
                    remaining = int(response.headers["x-ratelimit-remaining"])
                    if remaining == 0:
                        reset_timestamp = int(response.headers.get("x-ratelimit-reset", 0))
                        reset_at = datetime.fromtimestamp(reset_timestamp)
                        raise GitHubRateLimitError(reset_at, remaining)

            # Handle 304 Not Modified (ETag match)
            if response.status_code == 304:
                logger.debug("github_etag_match", endpoint=endpoint)
                return {}, response.headers

            # Handle errors
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("message", "Unknown error")

                # Retry on server errors
                if response.status_code >= 500 and retry_count < self.MAX_RETRIES:
                    wait_time = self.RETRY_BACKOFF_BASE**retry_count
                    logger.warning(
                        "github_api_error_retrying",
                        status_code=response.status_code,
                        retry_count=retry_count,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    return await self._request(
                        method, endpoint, params, json, etag, retry_count + 1
                    )

                raise GitHubAPIError(response.status_code, error_message, error_data)

            # Parse response
            data = response.json() if response.content else {}

            logger.debug(
                "github_api_request_success",
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            )

            return data, response.headers

        except httpx.HTTPError as e:
            # Retry on network errors
            if retry_count < self.MAX_RETRIES:
                wait_time = self.RETRY_BACKOFF_BASE**retry_count
                logger.warning(
                    "github_api_network_error_retrying",
                    error=str(e),
                    retry_count=retry_count,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)
                return await self._request(method, endpoint, params, json, etag, retry_count + 1)

            logger.error("github_api_network_error", error=str(e))
            raise GitHubAPIError(0, f"Network error: {str(e)}")

    async def get(
        self, endpoint: str, params: Optional[dict] = None, etag: Optional[str] = None
    ) -> tuple[dict | list, httpx.Headers]:
        """GET request to GitHub API."""
        return await self._request("GET", endpoint, params=params, etag=etag)

    async def post(self, endpoint: str, json: Optional[dict] = None) -> tuple[dict, httpx.Headers]:
        """POST request to GitHub API."""
        return await self._request("POST", endpoint, json=json)

    async def patch(self, endpoint: str, json: Optional[dict] = None) -> tuple[dict, httpx.Headers]:
        """PATCH request to GitHub API."""
        return await self._request("PATCH", endpoint, json=json)

    async def paginate(
        self, endpoint: str, params: Optional[dict] = None, per_page: int = 100
    ) -> AsyncGenerator[dict, None]:
        """
        Paginate through GitHub API results using Link headers.

        Args:
            endpoint: API endpoint
            params: Query parameters
            per_page: Items per page (max 100)

        Yields:
            Individual items from paginated results
        """
        params = params or {}
        params["per_page"] = min(per_page, 100)

        current_url = endpoint

        while current_url:
            data, headers = await self.get(current_url, params if current_url == endpoint else None)

            # Yield items
            if isinstance(data, list):
                for item in data:
                    yield item
            else:
                yield data
                break

            # Check for next page
            link_header = headers.get("link", "")
            next_url = self._parse_next_link(link_header)

            if not next_url:
                break

            current_url = next_url

    def _parse_next_link(self, link_header: str) -> Optional[str]:
        """
        Parse Link header to find next page URL.

        Args:
            link_header: Link header value

        Returns:
            Next page URL or None
        """
        if not link_header:
            return None

        links = link_header.split(",")
        for link in links:
            parts = link.split(";")
            if len(parts) == 2:
                url = parts[0].strip().strip("<>")
                rel = parts[1].strip()
                if 'rel="next"' in rel:
                    # Extract path from full URL
                    parsed = urlparse(url)
                    return f"{parsed.path}?{parsed.query}"

        return None

    # Convenience methods for common endpoints

    async def get_user(self, username: str) -> dict:
        """Get user profile."""
        data, _ = await self.get(f"/users/{username}")
        return data

    async def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository information."""
        data, _ = await self.get(f"/repos/{owner}/{repo}")
        return data

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict:
        """Get pull request details."""
        data, _ = await self.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return data

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "all", per_page: int = 100
    ) -> AsyncGenerator[dict, None]:
        """List pull requests with pagination."""
        async for pr in self.paginate(
            f"/repos/{owner}/{repo}/pulls", params={"state": state}, per_page=per_page
        ):
            yield pr

    async def get_commit(self, owner: str, repo: str, sha: str) -> dict:
        """Get commit details."""
        data, _ = await self.get(f"/repos/{owner}/{repo}/commits/{sha}")
        return data

    async def verify_token(self) -> bool:
        """
        Verify if the access token is still valid.

        Returns:
            True if token is valid, False otherwise
        """
        try:
            await self.get("/user")
            return True
        except GitHubAPIError as e:
            if e.status_code == 401:
                logger.warning("github_token_invalid")
                return False
            raise
