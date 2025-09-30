"""SQLAlchemy document model capturing ingestion metadata."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID, BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DocumentType(str, Enum):
    """Supported document formats."""

    PDF = "pdf"
    IMAGE = "image"
    WORD = "word"
    CSV = "csv"
    WEB_CONTENT = "web_content"


class DocumentStatus(str, Enum):
    """Lifecycle states for document processing."""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class Document(Base):
    """Persistent metadata for uploaded documents."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_job_status", "job_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(BIGINT, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        server_default=DocumentStatus.UPLOADED.value,
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Document(id={self.id!s}, type={self.document_type.value}, status={self.status.value})"
