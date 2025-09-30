"""Schemas for export APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Payload to request document export."""

    format: str = Field(..., description="Desired export format", examples=["pdf"])
    template_id: Optional[str] = Field(
        default=None, description="Optional export template identifier"
    )
    include_watermark: bool = False
    include_signature: bool = False
    metadata_overrides: Dict[str, str] = Field(default_factory=dict)


class ExportResponse(BaseModel):
    """Response returned after initiating an export."""

    export_id: str
    status: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class TemplateCreateRequest(BaseModel):
    """Payload to create or update export templates."""

    name: str
    description: Optional[str] = None
    output_format: str
    template_config: Dict[str, object] = Field(default_factory=dict)
    signature_required: bool = False
    watermark_enabled: bool = False
    is_default: bool = False


class TemplateResponse(BaseModel):
    """Representation of an export template."""

    id: str
    name: str
    description: Optional[str] = None
    output_format: str
    template_config: Dict[str, object]
    signature_required: bool
    watermark_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    """List of templates available to the current user."""

    templates: List[TemplateResponse]
