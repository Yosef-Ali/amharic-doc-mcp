"""
Integration tests for MCP tools.

These tests verify the integration between MCP tools and the backend services.
"""

import pytest
import base64
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestMCPToolIntegration:
    """Test MCP tool integration with backend services."""

    @pytest.mark.asyncio
    async def test_list_mcp_tools(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing available MCP tools."""
        response = await async_client.get(
            "/api/v1/mcp/tools",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tools" in data
        assert "tool_definitions" in data
        assert "capabilities" in data
        assert "protocol_version" in data
        assert "server_info" in data
        
        # Verify expected tools are present
        expected_tools = [
            "upload_document",
            "get_processing_progress",
            "search_documents",
            "export_document",
            "generate_summary",
            "manage_webhook_subscription",
            "get_system_status"
        ]
        
        for tool in expected_tools:
            assert tool in data["tools"]
            assert tool in data["tool_definitions"]

    @pytest.mark.asyncio
    async def test_mcp_server_status(self, async_client: AsyncClient, auth_headers: dict):
        """Test MCP server status endpoint."""
        response = await async_client.get(
            "/api/v1/mcp/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["server_status"] == "healthy"
        assert data["protocol_version"] == "1.0"
        assert "tools_available" in data
        assert "capabilities" in data
        assert "resource_usage" in data

    @pytest.mark.asyncio
    async def test_upload_document_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_pdf_base64: str
    ):
        """Test document upload via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/upload_document/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "file_data": sample_pdf_base64,
                    "filename": "test_document.pdf",
                    "content_type": "application/pdf",
                    "metadata": {
                        "source": "test",
                        "priority": "high"
                    }
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool_name"] == "upload_document"
        assert "result" in data
        
        result = data["result"]
        assert "document_id" in result
        assert "job_id" in result
        assert result["filename"] == "test_document.pdf"
        assert result["status"] == "uploaded"
        assert result["processing_started"] is True

    @pytest.mark.asyncio
    async def test_get_processing_progress_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        processing_job_id: str
    ):
        """Test getting processing progress via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/get_processing_progress/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "job_id": processing_job_id
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool_name"] == "get_processing_progress"
        
        result = data["result"]
        assert result["job_id"] == processing_job_id
        assert "status" in result
        assert "progress" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_search_documents_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        indexed_document_id: str
    ):
        """Test document search via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/search_documents/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "query": "test",
                    "page": 1,
                    "page_size": 20
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool_name"] == "search_documents"
        
        result = data["result"]
        assert "results" in result
        assert "total" in result
        assert "page" in result
        assert result["query"] == "test"

    @pytest.mark.asyncio
    async def test_export_document_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        completed_document_id: str
    ):
        """Test document export via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/export_document/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "document_id": completed_document_id,
                    "export_format": "pdf",
                    "options": {
                        "include_metadata": True
                    }
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool_name"] == "export_document"
        
        result = data["result"]
        assert result["document_id"] == completed_document_id
        assert result["format"] == "pdf"
        assert "filename" in result
        assert "data" in result  # Base64 encoded

    @pytest.mark.asyncio
    async def test_generate_summary_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        completed_document_id: str
    ):
        """Test summary generation via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/generate_summary/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "document_id": completed_document_id,
                    "summary_type": "extractive",
                    "language": "amh"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["tool_name"] == "generate_summary"
        
        result = data["result"]
        assert result["document_id"] == completed_document_id
        assert "summary" in result
        assert "confidence" in result
        assert result["summary_type"] == "extractive"

    @pytest.mark.asyncio
    async def test_manage_webhook_create(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test webhook subscription creation via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/manage_webhook_subscription/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "action": "create",
                    "url": "https://example.com/webhook",
                    "events": ["document.uploaded", "document.completed"]
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        result = data["result"]
        assert result["action"] == "created"
        assert "subscription_id" in result
        assert result["url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_get_system_status_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test system status retrieval via MCP tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/get_system_status/execute",
            headers=auth_headers,
            json={"arguments": {}}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        result = data["result"]
        assert "processing_statistics" in result
        assert "quality_metrics" in result
        assert "user_activity" in result
        assert result["system_health"] == "operational"

    @pytest.mark.asyncio
    async def test_tool_not_found(self, async_client: AsyncClient, auth_headers: dict):
        """Test executing non-existent tool."""
        response = await async_client.post(
            "/api/v1/mcp/tools/nonexistent_tool/execute",
            headers=auth_headers,
            json={"arguments": {}}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_tool_invalid_arguments(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test tool execution with invalid arguments."""
        response = await async_client.post(
            "/api/v1/mcp/tools/upload_document/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    # Missing required arguments
                    "filename": "test.pdf"
                }
            }
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        assert "error" in data or data["success"] is False

    @pytest.mark.asyncio
    async def test_tool_execution_timing(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_pdf_base64: str
    ):
        """Test that tool execution includes timing information."""
        response = await async_client.post(
            "/api/v1/mcp/tools/upload_document/execute",
            headers=auth_headers,
            json={
                "arguments": {
                    "file_data": sample_pdf_base64,
                    "filename": "timing_test.pdf",
                    "content_type": "application/pdf"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], (int, float))
        assert data["execution_time_ms"] > 0


class TestMCPWebSocket:
    """Test MCP WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_websocket_connection(
        self,
        async_client: AsyncClient,
        auth_token: str
    ):
        """Test WebSocket connection establishment."""
        async with async_client.websocket_connect(
            f"/api/v1/mcp/ws/test-user-id?token={auth_token}"
        ) as websocket:
            # Receive connection established message
            data = await websocket.receive_json()
            
            assert data["type"] == "connection_established"
            assert "capabilities" in data

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(
        self,
        async_client: AsyncClient,
        auth_token: str
    ):
        """Test WebSocket ping/pong."""
        async with async_client.websocket_connect(
            f"/api/v1/mcp/ws/test-user-id?token={auth_token}"
        ) as websocket:
            # Skip connection message
            await websocket.receive_json()
            
            # Send ping
            await websocket.send_json({"type": "ping"})
            
            # Receive pong
            response = await websocket.receive_json()
            assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_websocket_tool_execution(
        self,
        async_client: AsyncClient,
        auth_token: str
    ):
        """Test executing tool via WebSocket."""
        async with async_client.websocket_connect(
            f"/api/v1/mcp/ws/test-user-id?token={auth_token}"
        ) as websocket:
            # Skip connection message
            await websocket.receive_json()
            
            # Execute tool
            await websocket.send_json({
                "type": "tool_execution",
                "tool_name": "get_system_status",
                "arguments": {},
                "request_id": "test-request-1"
            })
            
            # Receive result
            response = await websocket.receive_json()
            assert response["type"] == "tool_execution_result"
            assert response["request_id"] == "test-request-1"
            assert "result" in response

    @pytest.mark.asyncio
    async def test_websocket_subscription(
        self,
        async_client: AsyncClient,
        auth_token: str
    ):
        """Test WebSocket subscription to updates."""
        async with async_client.websocket_connect(
            f"/api/v1/mcp/ws/test-user-id?token={auth_token}"
        ) as websocket:
            # Skip connection message
            await websocket.receive_json()
            
            # Subscribe to updates
            await websocket.send_json({
                "type": "subscribe",
                "subscription_type": "processing_updates"
            })
            
            # Receive subscription confirmation
            response = await websocket.receive_json()
            assert response["type"] == "subscription_confirmed"
            assert response["subscription_type"] == "processing_updates"


# Fixtures for testing
@pytest.fixture
def sample_pdf_base64() -> str:
    """Provide a sample PDF file as base64."""
    # Minimal valid PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n110\n%%EOF"
    return base64.b64encode(pdf_content).decode()


@pytest.fixture
async def processing_job_id(
    async_client: AsyncClient,
    auth_headers: dict,
    sample_pdf_base64: str
) -> str:
    """Create a processing job and return its ID."""
    response = await async_client.post(
        "/api/v1/mcp/tools/upload_document/execute",
        headers=auth_headers,
        json={
            "arguments": {
                "file_data": sample_pdf_base64,
                "filename": "fixture_test.pdf",
                "content_type": "application/pdf"
            }
        }
    )
    
    data = response.json()
    return data["result"]["job_id"]


@pytest.fixture
async def completed_document_id(
    async_client: AsyncClient,
    db_session: AsyncSession
) -> str:
    """Create a completed document for testing."""
    # This would create a document in the test database
    # and mark it as completed
    # Implementation depends on your database models
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
async def indexed_document_id(
    async_client: AsyncClient,
    db_session: AsyncSession
) -> str:
    """Create an indexed document for search testing."""
    # This would create and index a document
    # Implementation depends on your Elasticsearch setup
    return "550e8400-e29b-41d4-a716-446655440001"
