"""create processing tasks table

Revision ID: 20240209_04
Revises: 20240209_03
Create Date: 2024-02-09 00:30:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_04"
down_revision: Union[str, None] = "20240209_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TASK_STATUS_ENUM = "task_status"
AGENT_TYPE_ENUM = "agent_type"


def upgrade() -> None:
    """Create processing_tasks table with enums and indexes."""
    task_status_enum = sa.Enum(
        "pending",
        "running",
        "completed",
        "failed",
        "retrying",
        "cancelled",
        name=TASK_STATUS_ENUM,
    )
    task_status_enum.create(op.get_bind(), checkfirst=True)

    agent_type_enum = sa.Enum(
        "orchestrator",
        "document_analyzer",
        "pdf_extractor",
        "image_ocr",
        "word_extractor",
        "csv_processor",
        "web_scraper",
        "amharic_nlp",
        "quality_assurance",
        name=AGENT_TYPE_ENUM,
    )
    agent_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "processing_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_type", agent_type_enum, nullable=False),
        sa.Column(
            "status",
            task_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "input_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "max_retries", sa.Integer(), nullable=False, server_default=sa.text("3")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_processing_tasks_job_status",
        "processing_tasks",
        ["job_id", "status"],
    )
    op.create_index(
        "ix_processing_tasks_document_agent",
        "processing_tasks",
        ["document_id", "agent_type"],
    )


def downgrade() -> None:
    """Drop processing_tasks table and enums."""
    op.drop_index(
        "ix_processing_tasks_document_agent", table_name="processing_tasks"
    )
    op.drop_index("ix_processing_tasks_job_status", table_name="processing_tasks")
    op.drop_table("processing_tasks")

    agent_type_enum = sa.Enum(
        "orchestrator",
        "document_analyzer",
        "pdf_extractor",
        "image_ocr",
        "word_extractor",
        "csv_processor",
        "web_scraper",
        "amharic_nlp",
        "quality_assurance",
        name=AGENT_TYPE_ENUM,
    )
    agent_type_enum.drop(op.get_bind(), checkfirst=True)

    task_status_enum = sa.Enum(
        "pending",
        "running",
        "completed",
        "failed",
        "retrying",
        "cancelled",
        name=TASK_STATUS_ENUM,
    )
    task_status_enum.drop(op.get_bind(), checkfirst=True)
