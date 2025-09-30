"""create quality metrics table

Revision ID: 20240209_05
Revises: 20240209_04
Create Date: 2024-02-09 00:40:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_05"
down_revision: Union[str, None] = "20240209_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

METRIC_TYPE_ENUM = "metric_type"


def upgrade() -> None:
    """Create quality_metrics table and metric type enum."""
    metric_type_enum = sa.Enum(
        "ocr_accuracy",
        "language_detection",
        "structure_extraction",
        "ner_confidence",
        "processing_time",
        "content_completeness",
        name=METRIC_TYPE_ENUM,
    )
    metric_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "quality_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_type", metric_type_enum, nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_quality_metrics_document_type",
        "quality_metrics",
        ["document_id", "metric_type"],
    )


def downgrade() -> None:
    """Drop quality_metrics table and enum."""
    op.drop_index("ix_quality_metrics_document_type", table_name="quality_metrics")
    op.drop_table("quality_metrics")

    metric_type_enum = sa.Enum(
        "ocr_accuracy",
        "language_detection",
        "structure_extraction",
        "ner_confidence",
        "processing_time",
        "content_completeness",
        name=METRIC_TYPE_ENUM,
    )
    metric_type_enum.drop(op.get_bind(), checkfirst=True)
