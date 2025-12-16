"""
Tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_health_check(client: AsyncClient) -> None:
    """Test basic health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "version" in data


@pytest.mark.integration
async def test_database_health_check(client: AsyncClient) -> None:
    """Test database health check endpoint."""
    response = await client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.integration
async def test_redis_health_check(client: AsyncClient) -> None:
    """Test Redis health check endpoint."""
    response = await client.get("/api/v1/health/redis")
    assert response.status_code == 200
    data = response.json()
    # Redis may or may not be available in test environment
    assert "status" in data
    assert "redis" in data
