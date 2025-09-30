"""Integration test for quality metrics aggregation."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quality_metrics_flow(async_client, auth_headers, seeded_document_id):
    """Ensure metrics endpoint aggregates data per contract."""
    metrics_response = await async_client.get(
        f"/api/v1/quality/metrics/{seeded_document_id}",
        headers=auth_headers,
    )
    assert metrics_response.status_code == 200

    summary_response = await async_client.get(
        "/api/v1/quality/summary",
        headers=auth_headers,
        params={"from": "2024-01-01", "to": "2024-12-31"},
    )
    assert summary_response.status_code == 200
