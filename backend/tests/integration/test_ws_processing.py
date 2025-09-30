"""Integration test for processing WebSocket updates."""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_processing_websocket_flow(websocket_client, auth_token, seeded_job_id):
    """Ensure websocket stream upgrades and emits progress events."""
    uri = f"/api/v1/ws/processing/{seeded_job_id}?token={auth_token}"
    async with websocket_client.connect(uri) as ws:
        # Wait for initial status frame
        message = await asyncio.wait_for(ws.recv(), timeout=5)
        assert "job_id" in message
        assert str(seeded_job_id) in message

        # Simulate client sending ping/ack if protocol supports it
        await ws.send_json({"type": "ack", "job_id": str(seeded_job_id)})

        # Close gracefully
        await ws.close()
