"""Schemas for Model Context Protocol endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MCPToolDescription(BaseModel):
    """Description of an MCP tool exposed to CopilotKit."""

    name: str
    description: str
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="JSON schema describing tool parameters"
    )
    returns: Dict[str, Any] = Field(
        default_factory=dict, description="JSON schema describing tool response"
    )


class MCPExecuteRequest(BaseModel):
    """Execution request coming from the MCP client."""

    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None


class MCPExecuteResponse(BaseModel):
    """Response payload returned after executing an MCP tool."""

    status: str
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
