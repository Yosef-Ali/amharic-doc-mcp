"""Contract tests for search endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.contract
class TestSearchContracts:
    """Validate search endpoints against OpenAPI definitions."""

    @pytest.mark.asyncio
    async def test_search_documents(self, async_client, auth_headers):
        """GET /search/documents supports query, facets, and pagination."""
        response = await async_client.get(
            "/api/v1/search/documents",
            headers=auth_headers,
            params={
                "query": "ትምህርት",
                "page": 1,
                "limit": 5,
                "language": "am",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "results" in payload and "pagination" in payload

    @pytest.mark.asyncio
    async def test_search_documents_requires_query(self, async_client, auth_headers):
        """Missing query parameter should trigger validation error."""
        response = await async_client.get(
            "/api/v1/search/documents",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_suggestions(self, async_client, auth_headers):
        """GET /search/suggestions returns suggestion list."""
        response = await async_client.get(
            "/api/v1/search/suggestions",
            headers=auth_headers,
            params={"query": "ኢት"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "suggestions" in payload

    @pytest.mark.asyncio
    async def test_reindex_documents(self, async_client, auth_headers):
        """POST /search/reindex triggers reindex operations."""
        response = await async_client.post(
            "/api/v1/search/reindex",
            headers=auth_headers,
            json={"document_ids": [], "rebuild_embeddings": True},
        )
        assert response.status_code in {202, 200}

