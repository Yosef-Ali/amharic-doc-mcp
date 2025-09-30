"""SQLAlchemy processing job model with priority tiers and SLA tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ProcessingStatus(str, Enum):
    """State machine for processing jobs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MANUAL_REVIEW = "manual_review"


class ProcessingPriority(str, Enum):
    """Priority tiers aligned with SLA expectations."""

    URGENT = "urgent"
    STANDARD = "standard"
    BULK = "bulk"


class ProcessingJob(Base):
    """Batch of documents progressing through the processing pipeline."""

    __tablename__ = "processing_jobs"
    __table_args__ = (
        Index("ix_processing_jobs_user_status", "user_id", "status"),
        Index("ix_processing_jobs_priority", "priority", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(ProcessingStatus, name="processing_status"),
        nullable=False,
        default=ProcessingStatus.QUEUED,
        server_default=ProcessingStatus.QUEUED.value,
    )
    priority: Mapped[ProcessingPriority] = mapped_column(
        SAEnum(ProcessingPriority, name="processing_priority"),
        nullable=False,
        default=ProcessingPriority.STANDARD,
        server_default=ProcessingPriority.STANDARD.value,
    )
    total_documents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    completed_documents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    configuration: Mapped[Dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    sla_due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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
            "ProcessingJob(id={id}, status={status}, priority={priority})".format(
                id=self.id, status=self.status.value, priority=self.priority.value
            )
        )
