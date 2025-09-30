"""Pydantic schemas for processing jobs and tasks."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .documents import PaginationMeta, DocumentMetadata


class JobStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    DOCUMENT_ANALYZER = "document_analyzer"
    PDF_EXTRACTOR = "pdf_extractor"
    IMAGE_OCR = "image_ocr"
    WORD_EXTRACTOR = "word_extractor"
    CSV_PROCESSOR = "csv_processor"
    WEB_SCRAPER = "web_scraper"
    AMHARIC_NLP = "amharic_nlp"
    QUALITY_ASSURANCE = "quality_assurance"


class JobConfiguration(BaseModel):
    """Processing configuration provided by clients."""

    ocr_languages: List[str] = Field(default_factory=lambda: ["amh", "eng"])
    quality_threshold: float = 0.85
    enable_spell_check: bool = True
    enable_ner: bool = True
    output_formats: List[str] = Field(default_factory=lambda: ["pdf", "docx"])
    batch_size: int = Field(default=10, ge=1, le=100)
    priority: int = Field(default=1, ge=1, le=5)


class JobCreateRequest(BaseModel):
    """Payload to create/queue a new processing job."""

    job_name: str
    document_ids: List[str] = Field(..., min_items=1)
    configuration: JobConfiguration = Field(default_factory=JobConfiguration)


class JobSummary(BaseModel):
    """Summary view of a processing job."""

    id: str
    user_id: Optional[str] = None
    job_name: str
    status: JobStatus
    total_documents: int
    completed_documents: int
    progress_percentage: float
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class JobResponse(BaseModel):
    """Detailed processing job response."""

    job: JobSummary
    configuration: JobConfiguration
    documents: List[DocumentMetadata]


class JobListResponse(BaseModel):
    """Paginated list of processing jobs."""

    jobs: List[JobSummary]
    pagination: PaginationMeta


class TaskResponse(BaseModel):
    """Processing task status response."""

    id: str
    job_id: str
    document_id: str
    agent_type: AgentType
    status: TaskStatus
    confidence_score: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    """List of tasks for a processing job."""

    tasks: List[TaskResponse]


class ManualReviewPromotionRequest(BaseModel):
    """Payload to move a job to manual review queue."""

    reason: str = Field(..., min_length=5, max_length=500)
    escalate_to: Optional[str] = Field(
        default=None, description="Optional identifier of reviewer/queue"
    )
