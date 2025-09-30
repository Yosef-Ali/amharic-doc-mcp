"""Integration test for multi-format ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

TEST_DATA_DIR = Path("tests/data")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_format_ingestion(async_client, auth_headers):
    """Uploading multiple formats triggers appropriate pipelines."""
    files = [
        ("files", ("sample.pdf", (TEST_DATA_DIR / "sample.pdf").read_bytes(), "application/pdf")),
        ("files", ("sample.jpg", (TEST_DATA_DIR / "sample.jpg").read_bytes(), "image/jpeg")),
        ("files", ("sample.docx", (TEST_DATA_DIR / "sample.docx").read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("sample.csv", (TEST_DATA_DIR / "sample.csv").read_bytes(), "text/csv")),
    ]

    response = await async_client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files=files,
        data={"job_name": "Integration Pipeline"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert len(payload["documents"]) == 4
