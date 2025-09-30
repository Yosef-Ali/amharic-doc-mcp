"""create documents table

Revision ID: 20240209_02
Revises: 20240209_01
Create Date: 2024-02-09 00:10:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_02"
down_revision: Union[str, None] = "20240209_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DOCUMENT_TYPE_ENUM = "document_type"
DOCUMENT_STATUS_ENUM = "document_status"


def upgrade() -> None:
    """Create documents table and enums."""
    doc_type_enum = sa.Enum(
        "pdf",
        "image",
        "word",
        "csv",
        "web_content",
        name=DOCUMENT_TYPE_ENUM,
    )
    doc_type_enum.create(op.get_bind(), checkfirst=True)

    doc_status_enum = sa.Enum(
        "uploaded",
        "queued",
        "processing",
        "completed",
        "failed",
        "archived",
        name=DOCUMENT_STATUS_ENUM,
    )
    doc_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("document_type", doc_type_enum, nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("source_uri", sa.String(length=1024), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            doc_status_enum,
            nullable=False,
            server_default=sa.text("'uploaded'"),
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_documents_owner_status", "documents", ["owner_id", "status"]
    )
    op.create_index("ix_documents_job_status", "documents", ["job_id", "status"])


def downgrade() -> None:
    """Drop documents table and enums."""
    op.drop_index("ix_documents_job_status", table_name="documents")
    op.drop_index("ix_documents_owner_status", table_name="documents")
    op.drop_table("documents")

    doc_status_enum = sa.Enum(
        "uploaded",
        "queued",
        "processing",
        "completed",
        "failed",
        "archived",
        name=DOCUMENT_STATUS_ENUM,
    )
    doc_status_enum.drop(op.get_bind(), checkfirst=True)

    doc_type_enum = sa.Enum(
        "pdf",
        "image",
        "word",
        "csv",
        "web_content",
        name=DOCUMENT_TYPE_ENUM,
    )
    doc_type_enum.drop(op.get_bind(), checkfirst=True)
