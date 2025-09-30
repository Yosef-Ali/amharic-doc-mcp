"""Pydantic request/response schemas for the public API."""

from .auth import LoginRequest, AuthResponse, RefreshTokenRequest, LogoutResponse
from .documents import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentStatusUpdate,
)
from .processing import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
    TaskResponse,
    ManualReviewPromotionRequest,
)
from .search import (
    SearchRequest,
    SearchResponse,
    SuggestionResponse,
    ReindexRequest,
)
from .export import (
    ExportRequest,
    ExportResponse,
    TemplateCreateRequest,
    TemplateResponse,
    TemplateListResponse,
)
from .quality import QualityMetricResponse, QualitySummaryResponse
from .mcp import MCPToolDescription, MCPExecuteRequest, MCPExecuteResponse

__all__ = [
    # Auth
    "LoginRequest",
    "AuthResponse",
    "RefreshTokenRequest",
    "LogoutResponse",
    # Documents
    "DocumentUploadResponse",
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentMetadata",
    "DocumentStatusUpdate",
    # Processing
    "JobCreateRequest",
    "JobResponse",
    "JobListResponse",
    "TaskResponse",
    "ManualReviewPromotionRequest",
    # Search
    "SearchRequest",
    "SearchResponse",
    "SuggestionResponse",
    "ReindexRequest",
    # Export
    "ExportRequest",
    "ExportResponse",
    "TemplateCreateRequest",
    "TemplateResponse",
    "TemplateListResponse",
    # Quality
    "QualityMetricResponse",
    "QualitySummaryResponse",
    # MCP
    "MCPToolDescription",
    "MCPExecuteRequest",
    "MCPExecuteResponse",
]
