"""SQLAlchemy model for search index metadata persisted in PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class SearchIndex(Base):
    """Stored search representation for processed documents."""

    __tablename__ = "search_indices"
    __table_args__ = (
        Index("ix_search_indices_document", "document_id"),
        Index("ix_search_indices_language", "language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_content: Mapped[str] = mapped_column(String, nullable=False)
    facets: Mapped[Dict[str, str]] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="am", server_default="am")
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    processing_quality: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        postgresql.ARRAY(postgresql.DOUBLE_PRECISION), nullable=True
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"SearchIndex(id={self.id!s}, document_id={self.document_id!s})"
