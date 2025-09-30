"""SQLAlchemy export template model for document generation."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class OutputFormat(str, Enum):
    """Supported export output formats."""

    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class ExportTemplate(Base):
    """Reusable template configuration for document exports."""

    __tablename__ = "export_templates"
    __table_args__ = (Index("ix_export_templates_default", "is_default"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    output_format: Mapped[OutputFormat] = mapped_column(
        SAEnum(OutputFormat, name="output_format"), nullable=False
    )
    template_config: Mapped[Dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    signature_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    watermark_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"ExportTemplate(id={self.id!s}, name={self.name!r}, format={self.output_format.value})"
