"""Contract tests for document export endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.contract
class TestExportContracts:
    """Verify export endpoints follow the documented contract."""

    @pytest.mark.asyncio
    async def test_export_document(self, async_client, auth_headers, seeded_document_id):
        """POST /export/documents/{id} initiates export flow."""
        payload = {"format": "pdf", "include_watermark": True}
        response = await async_client.post(
            f"/api/v1/export/documents/{seeded_document_id}",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code in {200, 202}
        body = response.json()
        assert "export_id" in body

    @pytest.mark.asyncio
    async def test_export_document_unsupported_format(
        self, async_client, auth_headers, seeded_document_id
    ):
        """Unsupported formats should return 400 according to contract."""
        response = await async_client.post(
            f"/api/v1/export/documents/{seeded_document_id}",
            headers=auth_headers,
            json={"format": "exe"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_templates(self, async_client, auth_headers):
        """GET /export/templates returns template listings."""
        response = await async_client.get(
            "/api/v1/export/templates", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert "templates" in payload

    @pytest.mark.asyncio
    async def test_create_template(self, async_client, auth_headers):
        """POST /export/templates creates a new template."""
        payload = {
            "name": "Contract Template",
            "output_format": "pdf",
            "template_config": {"header": "Test"},
            "signature_required": True,
        }
        response = await async_client.post(
            "/api/v1/export/templates",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["template"]["name"] == "Contract Template"
