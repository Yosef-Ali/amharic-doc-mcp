"""Integration test for MCP tool execution."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_tool_execution(async_client, auth_headers):
    """Execute MCP tool via REST endpoint."""
    response = await async_client.post(
        "/api/v1/mcp/tools/upload/execute",
        headers=auth_headers,
        json={"parameters": {"file_id": "demo"}},
    )
    assert response.status_code in {200, 202, 400}

