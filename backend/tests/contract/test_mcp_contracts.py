"""Contract tests for MCP endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.contract
class TestMCPContracts:
    """Validate MCP tool listing and execution contract."""

    @pytest.mark.asyncio
    async def test_list_mcp_tools(self, async_client, auth_headers):
        """GET /mcp/tools returns available tool descriptions."""
        response = await async_client.get(
            "/api/v1/mcp/tools", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        if payload:
            assert "name" in payload[0]
            assert "description" in payload[0]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool(self, async_client, auth_headers):
        """POST /mcp/tools/{tool}/execute triggers tool execution."""
        response = await async_client.post(
            "/api/v1/mcp/tools/upload/execute",
            headers=auth_headers,
            json={"parameters": {"file_id": "dummy"}},
        )
        assert response.status_code in {200, 202, 400}

    @pytest.mark.asyncio
    async def test_mcp_websocket_upgrade(self, websocket_client, auth_token):
        """/ws/processing/{job_id} handshake matches contract."""
        job_id = "00000000-0000-0000-0000-000000000000"
        async with websocket_client.connect(
            f"/api/v1/ws/processing/{job_id}?token={auth_token}"
        ) as ws:
            await ws.close()
