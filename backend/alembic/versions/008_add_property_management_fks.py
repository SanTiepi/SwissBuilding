"""Add property management FK columns to existing tables

Revision ID: 008_add_property_mgmt_fks
Revises: 007_add_property_mgmt_tables
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "008_add_property_mgmt_fks"
down_revision: str | None = "007_add_property_mgmt_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # interventions: add contract_id
    op.add_column("interventions", sa.Column("contract_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_interventions_contract_id",
        "interventions",
        "contracts",
        ["contract_id"],
        ["id"],
    )

    # zones: add usage_type
    op.add_column("zones", sa.Column("usage_type", sa.String(30), nullable=True))

    # documents: add content_hash + partial unique index
    op.add_column("documents", sa.Column("content_hash", sa.String(64), nullable=True))
    op.create_index(
        "uq_documents_content_hash_file_path",
        "documents",
        ["content_hash", "file_path"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_documents_content_hash_file_path", table_name="documents")
    op.drop_column("documents", "content_hash")
    op.drop_column("zones", "usage_type")

    op.drop_constraint("fk_interventions_contract_id", "interventions", type_="foreignkey")
    op.drop_column("interventions", "contract_id")
