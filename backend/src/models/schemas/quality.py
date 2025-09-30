"""Quality metrics API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class QualityMetricResponse(BaseModel):
    """Single quality metric measurement."""

    id: str
    job_id: str | None = None
    document_id: str
    metric_type: str
    score: float = Field(..., ge=0.0, le=1.0)
    details: Dict[str, object] = Field(default_factory=dict)
    measured_at: datetime


class QualitySummaryMetric(BaseModel):
    """Aggregated metric output for summaries."""

    metric_type: str
    average_score: float = Field(..., ge=0.0, le=1.0)
    total_measurements: int = Field(..., ge=0)
    trend: str


class QualitySummaryResponse(BaseModel):
    """Summary of quality metrics over a time period."""

    period_from: datetime
    period_to: datetime
    metrics: List[QualitySummaryMetric]
