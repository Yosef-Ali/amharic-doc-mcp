"""create export templates table

Revision ID: 20240209_07
Revises: 20240209_06
Create Date: 2024-02-09 01:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20240209_07"
down_revision: Union[str, None] = "20240209_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OUTPUT_FORMAT_ENUM = "output_format"


def upgrade() -> None:
    """Create export_templates table and output format enum."""
    output_format_enum = sa.Enum(
        "pdf",
        "docx",
        "html",
        "markdown",
        "json",
        name=OUTPUT_FORMAT_ENUM,
    )
    output_format_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "export_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("output_format", output_format_enum, nullable=False),
        sa.Column(
            "template_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "signature_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "watermark_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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

    op.create_index("ix_export_templates_default", "export_templates", ["is_default"])


def downgrade() -> None:
    """Drop export_templates table and enum."""
    op.drop_index("ix_export_templates_default", table_name="export_templates")
    op.drop_table("export_templates")

    output_format_enum = sa.Enum(
        "pdf",
        "docx",
        "html",
        "markdown",
        "json",
        name=OUTPUT_FORMAT_ENUM,
    )
    output_format_enum.drop(op.get_bind(), checkfirst=True)
