"""Add proof_deliveries table

Revision ID: 015_add_proof_delivery
Revises: 013_add_intake_requests
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "015_add_proof_delivery"
down_revision: str | None = "013_add_intake_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proof_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("audience", sa.String(30), nullable=False),
        sa.Column("recipient_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("recipient_email", sa.String(200), nullable=True),
        sa.Column("delivery_method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("delivered_at", sa.DateTime, nullable=True),
        sa.Column("viewed_at", sa.DateTime, nullable=True),
        sa.Column("acknowledged_at", sa.DateTime, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("content_version", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        # ProvenanceMixin columns
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        # Timestamps
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("idx_proof_deliveries_building_id", "proof_deliveries", ["building_id"])
    op.create_index("idx_proof_deliveries_target", "proof_deliveries", ["target_type", "target_id"])
    op.create_index("idx_proof_deliveries_status", "proof_deliveries", ["status"])
    op.create_index("idx_proof_deliveries_audience", "proof_deliveries", ["audience"])


def downgrade() -> None:
    op.drop_index("idx_proof_deliveries_audience", table_name="proof_deliveries")
    op.drop_index("idx_proof_deliveries_status", table_name="proof_deliveries")
    op.drop_index("idx_proof_deliveries_target", table_name="proof_deliveries")
    op.drop_index("idx_proof_deliveries_building_id", table_name="proof_deliveries")
    op.drop_table("proof_deliveries")
