"""Contract tests for document management endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_FILE = Path("tests/data/sample.pdf")


@pytest.mark.contract
class TestDocumentContracts:
    """Ensure document endpoints honor the public contract."""

    @pytest.mark.asyncio
    async def test_upload_documents_accepts_supported_formats(self, async_client, auth_headers):
        """Multipart upload returns 201 and job metadata."""
        files = {
            "files": ("sample.pdf", SAMPLE_FILE.read_bytes(), "application/pdf"),
        }
        response = await async_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files=files,
            data={"job_name": "Contract Test"},
        )
        assert response.status_code == 201
        payload = response.json()
        assert "job_id" in payload
        assert payload["documents"][0]["status"] in {"uploaded", "queued"}

    @pytest.mark.asyncio
    async def test_upload_documents_rejects_large_files(self, async_client, auth_headers):
        """Files beyond size limit should trigger validation error."""
        files = {
            "files": ("large.pdf", b"0" * (110 * 1024 * 1024), "application/pdf"),
        }
        response = await async_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_get_document_details(self, async_client, auth_headers, seeded_document_id):
        """GET /documents/{id} returns document metadata per schema."""
        response = await async_client.get(
            f"/api/v1/documents/{seeded_document_id}", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["document"]["id"] == str(seeded_document_id)

    @pytest.mark.asyncio
    async def test_document_listing_supports_pagination(self, async_client, auth_headers):
        """GET /documents obeys pagination contract."""
        response = await async_client.get(
            "/api/v1/documents?page=1&limit=10", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert "documents" in payload and "pagination" in payload
        assert payload["pagination"]["page"] == 1

    @pytest.mark.asyncio
    async def test_delete_document(self, async_client, auth_headers, seeded_document_id):
        """DELETE /documents/{id} returns 204 on success."""
        response = await async_client.delete(
            f"/api/v1/documents/{seeded_document_id}", headers=auth_headers
        )
        assert response.status_code == 204
