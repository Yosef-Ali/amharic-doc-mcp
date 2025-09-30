"""MCP routes aligning with CopilotKit expectations for Model Context Protocol integration."""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_async_session
from ...services.processing import get_processing_orchestrator
from ...services.documents import get_document_service
from ...services.search import get_search_service
from ...services.export import get_export_service
from ...services.summarization import get_summarization_service
from ...services.webhooks import get_webhook_service
from ...mcp.tools import get_mcp_tools, execute_mcp_tool
from ...models.schemas.mcp import (
    MCPToolListResponse,
    MCPToolExecutionRequest,
    MCPToolExecutionResponse,
    MCPStatusResponse,
    MCPWebSocketMessage
)
from ...config.settings import get_settings
from .auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])
settings = get_settings()


@router.get(
    "/tools",
    response_model=MCPToolListResponse,
    summary="List MCP tools",
    description="Get list of available MCP tools for CopilotKit integration"
)
async def list_mcp_tools(
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List all available MCP tools."""
    try:
        tools = get_mcp_tools()
        
        return MCPToolListResponse(
            tools=list(tools.keys()),
            tool_definitions=tools,
            capabilities=[
                "document_upload",
                "processing_status",
                "search_documents", 
                "export_documents",
                "summarization",
                "webhook_management",
                "system_status"
            ],
            protocol_version="1.0",
            server_info={
                "name": "amharic-doc-mcp",
                "version": "1.0.0",
                "description": "Amharic Document Processing MCP Server"
            }
        )
        
    except Exception as e:
        logger.error(f"List MCP tools failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve MCP tools"
        )


@router.post(
    "/tools/{tool_name}/execute",
    response_model=MCPToolExecutionResponse,
    summary="Execute MCP tool",
    description="Execute a specific MCP tool with provided arguments"
)
async def execute_mcp_tool_endpoint(
    tool_name: str,
    request: MCPToolExecutionRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Execute an MCP tool."""
    try:
        # Validate tool exists
        available_tools = get_mcp_tools()
        if tool_name not in available_tools:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP tool '{tool_name}' not found"
            )
        
        # Execute the tool
        result = await execute_mcp_tool(
            session=session,
            tool_name=tool_name,
            arguments=request.arguments,
            user_id=current_user.id,
            settings=settings
        )
        
        return MCPToolExecutionResponse(
            tool_name=tool_name,
            success=result.get("success", False),
            result=result.get("result"),
            error=result.get("error"),
            execution_time_ms=result.get("execution_time_ms", 0),
            metadata=result.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP tool execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute MCP tool '{tool_name}'"
        )


@router.get(
    "/status",
    response_model=MCPStatusResponse,
    summary="Get MCP server status",
    description="Get current status of the MCP server and its capabilities"
)
async def get_mcp_status(
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get MCP server status."""
    try:
        # Get service statuses
        processing_service = get_processing_orchestrator(settings)
        document_service = get_document_service(settings)
        
        processing_stats = await processing_service.get_processing_statistics(session)
        
        return MCPStatusResponse(
            server_status="healthy",
            protocol_version="1.0",
            tools_available=len(get_mcp_tools()),
            active_connections=0,  # Will be updated by WebSocket manager
            processing_queue_size=processing_stats.get("queued", 0),
            total_documents_processed=processing_stats.get("completed", 0),
            server_uptime_seconds=0,  # Would be calculated from server start time
            capabilities={
                "document_processing": True,
                "real_time_updates": True,
                "batch_operations": True,
                "export_formats": ["pdf", "docx", "html", "markdown", "json"],
                "languages_supported": ["amharic", "english"],
                "max_file_size_mb": settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            },
            resource_usage={
                "cpu_percent": 0.0,  # Would be calculated from system metrics
                "memory_percent": 0.0,
                "disk_usage_percent": 0.0
            }
        )
        
    except Exception as e:
        logger.error(f"Get MCP status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve MCP server status"
        )


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Simple health check for MCP server"
)
async def health_check():
    """Health check endpoint for MCP server."""
    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "version": "1.0.0"
        }
    )


# WebSocket connection manager for real-time updates
class MCPConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"MCP WebSocket connected for user {user_id}")
        
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"MCP WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message to {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected connections
        for user_id in disconnected_users:
            self.disconnect(user_id)

# Global connection manager instance
mcp_manager = MCPConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """WebSocket endpoint for real-time MCP communication."""
    await mcp_manager.connect(websocket, user_id)
    
    try:
        # Send initial connection message
        await mcp_manager.send_personal_message({
            "type": "connection_established",
            "message": "MCP WebSocket connection established",
            "timestamp": "2024-01-01T00:00:00Z",
            "capabilities": [
                "processing_updates",
                "document_notifications", 
                "system_alerts"
            ]
        }, user_id)
        
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await mcp_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": "2024-01-01T00:00:00Z"
                }, user_id)
                
            elif data.get("type") == "subscribe":
                # Handle subscription requests
                subscription_type = data.get("subscription_type")
                await mcp_manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "subscription_type": subscription_type,
                    "message": f"Subscribed to {subscription_type} updates"
                }, user_id)
                
            elif data.get("type") == "tool_execution":
                # Handle tool execution via WebSocket
                tool_name = data.get("tool_name")
                arguments = data.get("arguments", {})
                
                try:
                    result = await execute_mcp_tool(
                        session=session,
                        tool_name=tool_name,
                        arguments=arguments,
                        user_id=user_id,
                        settings=settings
                    )
                    
                    await mcp_manager.send_personal_message({
                        "type": "tool_execution_result",
                        "tool_name": tool_name,
                        "result": result,
                        "request_id": data.get("request_id")
                    }, user_id)
                    
                except Exception as e:
                    await mcp_manager.send_personal_message({
                        "type": "tool_execution_error",
                        "tool_name": tool_name,
                        "error": str(e),
                        "request_id": data.get("request_id")
                    }, user_id)
            
    except WebSocketDisconnect:
        mcp_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        mcp_manager.disconnect(user_id)


# Function to get the connection manager for use in other services
def get_mcp_connection_manager() -> MCPConnectionManager:
    """Get the MCP connection manager for broadcasting updates."""
    return mcp_manager