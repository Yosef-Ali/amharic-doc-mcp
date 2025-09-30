"""SQLAlchemy model for processing task logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class LogLevel(str, Enum):
    """Log level categories for processing logs."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ProcessingLog(Base):
    """Structured log emitted during processing task execution."""

    __tablename__ = "processing_logs"
    __table_args__ = (Index("ix_processing_logs_task_level", "task_id", "log_level"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    log_level: Mapped[LogLevel] = mapped_column(
        SAEnum(LogLevel, name="processing_log_level"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            "ProcessingLog(id={id}, task_id={task}, level={level})".format(
                id=self.id, task=self.task_id, level=self.log_level.value
            )
        )
