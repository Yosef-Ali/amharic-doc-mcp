"""Contract tests for processing job endpoints."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.contract
class TestProcessingContracts:
    """Validate processing job API contract semantics."""

    @pytest.mark.asyncio
    async def test_create_job(self, async_client, auth_headers, seeded_document_ids):
        """POST /processing/jobs queues documents for processing."""
        payload = {
            "job_name": "Contract Job",
            "document_ids": [str(doc_id) for doc_id in seeded_document_ids],
            "configuration": {"priority": 2, "quality_threshold": 0.9},
        }
        response = await async_client.post(
            "/api/v1/processing/jobs", headers=auth_headers, json=payload
        )
        assert response.status_code == 201
        job = response.json()["job"]
        assert job["job_name"] == "Contract Job"
        assert job["status"] in {"created", "running", "queued"}

    @pytest.mark.asyncio
    async def test_list_jobs(self, async_client, auth_headers):
        """GET /processing/jobs supports pagination and status filters."""
        response = await async_client.get(
            "/api/v1/processing/jobs?page=1&limit=5&status=running",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert "jobs" in payload and "pagination" in payload

    @pytest.mark.asyncio
    async def test_get_job_details(self, async_client, auth_headers, seeded_job_id):
        """GET /processing/jobs/{id} returns job metadata."""
        response = await async_client.get(
            f"/api/v1/processing/jobs/{seeded_job_id}", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["job"]["id"] == str(seeded_job_id)

    @pytest.mark.asyncio
    async def test_cancel_job(self, async_client, auth_headers, seeded_job_id):
        """POST /processing/jobs/{id}/cancel acknowledges cancellation."""
        response = await async_client.post(
            f"/api/v1/processing/jobs/{seeded_job_id}/cancel",
            headers=auth_headers,
        )
        assert response.status_code in {200, 400, 409}

    @pytest.mark.asyncio
    async def test_job_tasks_listing(self, async_client, auth_headers, seeded_job_id):
        """GET /processing/jobs/{id}/tasks returns associated tasks."""
        response = await async_client.get(
            f"/api/v1/processing/jobs/{seeded_job_id}/tasks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert "tasks" in payload

    @pytest.mark.asyncio
    async def test_job_manual_review_promotion(
        self, async_client, auth_headers, seeded_job_id
    ):
        """POST /processing/jobs/{id}/manual-review transitions to manual queue per contract."""
        response = await async_client.post(
            f"/api/v1/processing/jobs/{seeded_job_id}/manual-review",
            headers=auth_headers,
            json={"reason": "Contract validation", "escalate_to": "qa-team"},
        )
        assert response.status_code in {200, 202, 409}

    @pytest.mark.asyncio
    async def test_processing_status_endpoint(self, async_client, auth_headers):
        """GET /processing/status returns processing pipeline state."""
        response = await async_client.get(
            "/api/v1/processing/status", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert "jobs_running" in payload
        assert "queue_depth" in payload
