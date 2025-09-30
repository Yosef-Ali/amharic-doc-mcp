"""create processing jobs table

Revision ID: 20240209_03
Revises: 20240209_02
Create Date: 2024-02-09 00:20:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_03"
down_revision: Union[str, None] = "20240209_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROCESSING_STATUS_ENUM = "processing_status"
PROCESSING_PRIORITY_ENUM = "processing_priority"


def upgrade() -> None:
    """Create processing_jobs table with enums and indices."""
    processing_status_enum = sa.Enum(
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        "manual_review",
        name=PROCESSING_STATUS_ENUM,
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)

    processing_priority_enum = sa.Enum(
        "urgent",
        "standard",
        "bulk",
        name=PROCESSING_PRIORITY_ENUM,
    )
    processing_priority_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            processing_status_enum,
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column(
            "priority",
            processing_priority_enum,
            nullable=False,
            server_default=sa.text("'standard'"),
        ),
        sa.Column(
            "total_documents", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "completed_documents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_processing_jobs_user_status",
        "processing_jobs",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_processing_jobs_priority",
        "processing_jobs",
        ["priority", "status"],
    )


def downgrade() -> None:
    """Drop processing_jobs table and enums."""
    op.drop_index("ix_processing_jobs_priority", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_user_status", table_name="processing_jobs")
    op.drop_table("processing_jobs")

    processing_priority_enum = sa.Enum(
        "urgent",
        "standard",
        "bulk",
        name=PROCESSING_PRIORITY_ENUM,
    )
    processing_priority_enum.drop(op.get_bind(), checkfirst=True)

    processing_status_enum = sa.Enum(
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        "manual_review",
        name=PROCESSING_STATUS_ENUM,
    )
    processing_status_enum.drop(op.get_bind(), checkfirst=True)
