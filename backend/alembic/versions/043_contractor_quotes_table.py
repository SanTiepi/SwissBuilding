"""Add contractor quotes table for automatic extraction of contractor estimates.

Revision ID: 043_contractor_quotes
Revises: 042_add_defect_timeline
Create Date: 2026-04-03
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "043_contractor_quotes"
down_revision = "042_add_defect_timeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contractor_quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("contractor_name", sa.String(500), nullable=True),
        sa.Column("contractor_contact", sa.String(500), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CHF"),
        sa.Column("price_per_unit", sa.Numeric(12, 2), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("vat_included", sa.String(50), nullable=True),
        sa.Column("scope", sa.Text, nullable=True),
        sa.Column("work_type", sa.String(100), nullable=True),
        sa.Column("timeline", sa.String(255), nullable=True),
        sa.Column("start_date", sa.DateTime, nullable=True),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("validity_days", sa.String(100), nullable=True),
        sa.Column("conditions", sa.Text, nullable=True),
        sa.Column("ai_generated", sa.String(50), nullable=False, server_default="claude-sonnet"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("confidence_breakdown", sa.JSON, nullable=True),
        sa.Column("raw_extraction", sa.JSON, nullable=True),
        sa.Column("reviewed", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("idx_contractor_quote_document", "contractor_quotes", ["document_id"])
    op.create_index("idx_contractor_quote_building", "contractor_quotes", ["building_id"])
    op.create_index("idx_contractor_quote_confidence", "contractor_quotes", ["confidence"])
    op.create_index("idx_contractor_quote_reviewed", "contractor_quotes", ["reviewed"])


def downgrade() -> None:
    op.drop_index("idx_contractor_quote_reviewed", table_name="contractor_quotes")
    op.drop_index("idx_contractor_quote_confidence", table_name="contractor_quotes")
    op.drop_index("idx_contractor_quote_building", table_name="contractor_quotes")
    op.drop_index("idx_contractor_quote_document", table_name="contractor_quotes")
    op.drop_table("contractor_quotes")
