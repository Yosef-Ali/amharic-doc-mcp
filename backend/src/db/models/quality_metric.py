"""SQLAlchemy model for processing quality metrics."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Float, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class MetricType(str, Enum):
    """Types of quality metrics captured during processing."""

    OCR_ACCURACY = "ocr_accuracy"
    LANGUAGE_DETECTION = "language_detection"
    STRUCTURE_EXTRACTION = "structure_extraction"
    NER_CONFIDENCE = "ner_confidence"
    PROCESSING_TIME = "processing_time"
    CONTENT_COMPLETENESS = "content_completeness"


class QualityMetric(Base):
    """Quality assurance measurement for a document/job."""

    __tablename__ = "quality_metrics"
    __table_args__ = (
        Index("ix_quality_metrics_document_type", "document_id", "metric_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    metric_type: Mapped[MetricType] = mapped_column(
        SAEnum(MetricType, name="metric_type"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[Dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    measured_at: Mapped[datetime] = mapped_column(
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
        return f"QualityMetric(id={self.id!s}, type={self.metric_type.value}, score={self.score})"
