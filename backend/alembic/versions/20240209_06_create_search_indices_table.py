"""create search indices table

Revision ID: 20240209_06
Revises: 20240209_05
Create Date: 2024-02-09 00:50:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_06"
down_revision: Union[str, None] = "20240209_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create search_indices table for stored search metadata."""
    op.create_table(
        "search_indices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("search_content", sa.Text(), nullable=False),
        sa.Column(
            "facets",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("language", sa.String(length=32), nullable=False, server_default="am"),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("processing_quality", sa.String(length=32), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column(
            "indexed_at",
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

    op.create_index("ix_search_indices_document", "search_indices", ["document_id"])
    op.create_index("ix_search_indices_language", "search_indices", ["language"])


def downgrade() -> None:
    """Drop search_indices table."""
    op.drop_index("ix_search_indices_language", table_name="search_indices")
    op.drop_index("ix_search_indices_document", table_name="search_indices")
    op.drop_table("search_indices")
