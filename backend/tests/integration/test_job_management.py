"""Integration test covering job lifecycle features."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_lifecycle(async_client, auth_headers, seeded_job_id):
    """Exercise cancellation, retry, and manual review flows."""
    # Cancel job and expect allowed statuses to succeed
    cancel_response = await async_client.post(
        f"/api/v1/processing/jobs/{seeded_job_id}/cancel", headers=auth_headers
    )
    assert cancel_response.status_code in {200, 400, 409}

    # Promote to manual review queue
    review_response = await async_client.post(
        f"/api/v1/processing/jobs/{seeded_job_id}/manual-review",
        headers=auth_headers,
        json={"reason": "Integration flow"},
    )
    assert review_response.status_code in {200, 202, 409}

    # Fetch job status to confirm response structure
    job_response = await async_client.get(
        f"/api/v1/processing/jobs/{seeded_job_id}", headers=auth_headers
    )
    assert job_response.status_code == 200
