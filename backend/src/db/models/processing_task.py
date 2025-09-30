"""SQLAlchemy model describing per-document processing tasks."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
    text,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class TaskStatus(str, Enum):
    """Lifecycle status for a processing task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Supported agent identifiers for processors."""

    ORCHESTRATOR = "orchestrator"
    DOCUMENT_ANALYZER = "document_analyzer"
    PDF_EXTRACTOR = "pdf_extractor"
    IMAGE_OCR = "image_ocr"
    WORD_EXTRACTOR = "word_extractor"
    CSV_PROCESSOR = "csv_processor"
    WEB_SCRAPER = "web_scraper"
    AMHARIC_NLP = "amharic_nlp"
    QUALITY_ASSURANCE = "quality_assurance"


class ProcessingTask(Base):
    """Unit of work executed by a specific agent for a document."""

    __tablename__ = "processing_tasks"
    __table_args__ = (
        Index("ix_processing_tasks_job_status", "job_id", "status"),
        Index("ix_processing_tasks_document_agent", "document_id", "agent_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_type: Mapped[AgentType] = mapped_column(
        SAEnum(AgentType, name="agent_type"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.PENDING,
        server_default=TaskStatus.PENDING.value,
    )
    input_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default=text("3")
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            "ProcessingTask(id={id}, agent={agent}, status={status})".format(
                id=self.id, agent=self.agent_type.value, status=self.status.value
            )
        )
