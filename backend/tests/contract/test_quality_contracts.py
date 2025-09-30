"""Contract tests for quality metrics endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.contract
class TestQualityContracts:
    """Ensure quality endpoints adhere to the documented contract."""

    @pytest.mark.asyncio
    async def test_get_quality_metrics(self, async_client, auth_headers, seeded_document_id):
        """GET /quality/metrics/{document_id} returns metric list."""
        response = await async_client.get(
            f"/api/v1/quality/metrics/{seeded_document_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert "metrics" in payload

    @pytest.mark.asyncio
    async def test_get_quality_summary(self, async_client, auth_headers):
        """GET /quality/summary supports date filters and returns summary."""
        response = await async_client.get(
            "/api/v1/quality/summary",
            headers=auth_headers,
            params={"from": "2024-01-01", "to": "2024-01-31"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "metrics" in payload

    @pytest.mark.asyncio
    async def test_quality_summary_requires_valid_range(self, async_client, auth_headers):
        """Invalid date range should trigger validation error."""
        response = await async_client.get(
            "/api/v1/quality/summary",
            headers=auth_headers,
            params={"from": "2024-02-01", "to": "2024-01-01"},
        )
        assert response.status_code in {400, 422}
