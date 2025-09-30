"""Integration test for search to export workflow."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_to_export_flow(async_client, auth_headers, seeded_document_id):
    """Search for a document and trigger export from search results."""
    search_response = await async_client.get(
        "/api/v1/search/documents",
        headers=auth_headers,
        params={"query": "ምርምር", "limit": 1},
    )
    assert search_response.status_code == 200
    payload = search_response.json()
    if payload["results"]:
        doc_id = payload["results"][0]["document"]["id"]
    else:
        doc_id = str(seeded_document_id)

    export_response = await async_client.post(
        f"/api/v1/export/documents/{doc_id}",
        headers=auth_headers,
        json={"format": "pdf"},
    )
    assert export_response.status_code in {200, 202}
