"""Pydantic schemas for document ingestion and retrieval APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Metadata describing paginated responses."""

    page: int = 1
    limit: int = Field(..., gt=0)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    has_next: bool = False
    has_previous: bool = False


class DocumentMetadata(BaseModel):
    """Surface representation of document metadata."""

    id: str
    owner_id: str
    job_id: Optional[str] = None
    filename: str
    document_type: str
    status: str
    file_size: int
    mime_type: Optional[str] = None
    storage_path: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None


class DocumentUploadItem(BaseModel):
    """Information returned for each uploaded document."""

    document_id: str
    filename: str
    status: str
    message: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response payload after uploading documents for processing."""

    job_id: str
    documents: List[DocumentUploadItem]
    message: str = "Documents queued for processing"


class DocumentResponse(BaseModel):
    """Response payload containing a single document."""

    document: DocumentMetadata


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: List[DocumentMetadata]
    pagination: PaginationMeta


class DocumentStatusUpdate(BaseModel):
    """Payload used to update document status (e.g., manual archival)."""

    status: str = Field(..., description="New document status value")
    reason: Optional[str] = Field(
        default=None, description="Optional explanation for the status change"
    )
