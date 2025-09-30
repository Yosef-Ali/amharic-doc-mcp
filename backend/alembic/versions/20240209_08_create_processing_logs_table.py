"""create processing logs table

Revision ID: 20240209_08
Revises: 20240209_07
Create Date: 2024-02-09 01:10:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_08"
down_revision: Union[str, None] = "20240209_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROCESSING_LOG_LEVEL_ENUM = "processing_log_level"


def upgrade() -> None:
    """Create processing_logs table and log level enum."""
    log_level_enum = sa.Enum(
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        name=PROCESSING_LOG_LEVEL_ENUM,
    )
    log_level_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "processing_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("log_level", log_level_enum, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_processing_logs_task_level",
        "processing_logs",
        ["task_id", "log_level"],
    )


def downgrade() -> None:
    """Drop processing_logs table and enum."""
    op.drop_index("ix_processing_logs_task_level", table_name="processing_logs")
    op.drop_table("processing_logs")

    log_level_enum = sa.Enum(
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        name=PROCESSING_LOG_LEVEL_ENUM,
    )
    log_level_enum.drop(op.get_bind(), checkfirst=True)
