"""Add document_inbox_items table

Revision ID: 011_add_document_inbox
Revises: 009_add_diag_integration
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "011_add_document_inbox"
down_revision: str | None = "009_add_diag_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_inbox_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("suggested_building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True),
        sa.Column("linked_building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True),
        sa.Column("linked_document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("classification", JSON, nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="upload"),
        sa.Column("uploaded_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_document_inbox_items_status", "document_inbox_items", ["status"])
    op.create_index("ix_document_inbox_items_source", "document_inbox_items", ["source"])


def downgrade() -> None:
    op.drop_index("ix_document_inbox_items_source", table_name="document_inbox_items")
    op.drop_index("ix_document_inbox_items_status", table_name="document_inbox_items")
    op.drop_table("document_inbox_items")
