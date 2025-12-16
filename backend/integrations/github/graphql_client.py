"""
GitHub GraphQL API client for bulk operations and complex queries.
"""

from typing import Any, Optional

import httpx
import structlog

from backend.integrations.github.rest_client import GitHubAPIError, GitHubRateLimitError

logger = structlog.get_logger(__name__)


class GitHubGraphQLClient:
    """
    GitHub GraphQL API client for efficient bulk operations.
    """

    GRAPHQL_URL = "https://api.github.com/graphql"
    MAX_RETRIES = 3

    def __init__(self, access_token: str):
        """
        Initialize GitHub GraphQL client.

        Args:
            access_token: GitHub OAuth or App token
        """
        self.access_token = access_token
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def query(self, query: str, variables: Optional[dict] = None) -> dict:
        """
        Execute GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query response data

        Raises:
            GitHubAPIError: If query fails
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = await self._client.post(self.GRAPHQL_URL, json=payload)

            if response.status_code >= 400:
                raise GitHubAPIError(
                    response.status_code, f"GraphQL request failed: {response.text}"
                )

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                errors = data["errors"]
                error_messages = [e.get("message", "Unknown error") for e in errors]
                logger.error("github_graphql_errors", errors=error_messages)

                # Check for rate limit errors
                for error in errors:
                    if error.get("type") == "RATE_LIMITED":
                        raise GitHubRateLimitError(None, 0)

                raise GitHubAPIError(400, f"GraphQL errors: {', '.join(error_messages)}")

            logger.debug("github_graphql_query_success")

            return data.get("data", {})

        except httpx.HTTPError as e:
            logger.error("github_graphql_network_error", error=str(e))
            raise GitHubAPIError(0, f"Network error: {str(e)}")

    async def get_pull_requests_bulk(
        self, owner: str, repo: str, first: int = 100, after: Optional[str] = None
    ) -> dict:
        """
        Fetch pull requests in bulk using GraphQL.

        Args:
            owner: Repository owner
            repo: Repository name
            first: Number of PRs to fetch
            after: Cursor for pagination

        Returns:
            Pull requests data with pagination info
        """
        query = """
        query($owner: String!, $repo: String!, $first: Int!, $after: String) {
          repository(owner: $owner, name: $repo) {
            pullRequests(first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                number
                title
                state
                createdAt
                updatedAt
                mergedAt
                closedAt
                author {
                  login
                  ... on User {
                    databaseId
                  }
                }
                additions
                deletions
                changedFiles
                commits(last: 1) {
                  nodes {
                    commit {
                      oid
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"owner": owner, "repo": repo, "first": first}
        if after:
            variables["after"] = after

        return await self.query(query, variables)

    async def get_user_contributions(self, username: str, from_date: str) -> dict:
        """
        Get user's contribution activity.

        Args:
            username: GitHub username
            from_date: ISO 8601 date string

        Returns:
            User contribution data
        """
        query = """
        query($username: String!, $from: DateTime!) {
          user(login: $username) {
            contributionsCollection(from: $from) {
              totalCommitContributions
              totalPullRequestContributions
              totalPullRequestReviewContributions
              pullRequestContributions(first: 100) {
                nodes {
                  pullRequest {
                    number
                    title
                    repository {
                      nameWithOwner
                    }
                    createdAt
                    mergedAt
                  }
                }
              }
            }
          }
        }
        """

        variables = {"username": username, "from": from_date}
        return await self.query(query, variables)

    async def get_repository_info(self, owner: str, repo: str) -> dict:
        """
        Get detailed repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository data
        """
        query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            id
            databaseId
            name
            nameWithOwner
            description
            defaultBranchRef {
              name
            }
            isPrivate
            isArchived
            createdAt
            updatedAt
          }
        }
        """

        variables = {"owner": owner, "repo": repo}
        return await self.query(query, variables)
