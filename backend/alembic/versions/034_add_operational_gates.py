"""Add operational_gates table.

Revision ID: 034_op_gates
Revises: 033_eco_engagements
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "034_op_gates"
down_revision = "033_eco_engagements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_gates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        # Gate identity
        sa.Column("gate_type", sa.String(50), nullable=False),
        sa.Column("gate_label", sa.String(300), nullable=False),
        # Status
        sa.Column("status", sa.String(30), nullable=False, server_default="blocked"),
        # Prerequisites (JSON array)
        sa.Column("prerequisites", sa.JSON, nullable=False, server_default="[]"),
        # Override
        sa.Column("overridden_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("override_reason", sa.Text, nullable=True),
        sa.Column("overridden_at", sa.DateTime, nullable=True),
        # Cleared
        sa.Column("cleared_at", sa.DateTime, nullable=True),
        sa.Column("cleared_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        # Config
        sa.Column("auto_evaluate", sa.Boolean, server_default=sa.text("true")),
        # ProvenanceMixin
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_op_gate_building_id", "operational_gates", ["building_id"])
    op.create_index("idx_op_gate_type", "operational_gates", ["gate_type"])
    op.create_index("idx_op_gate_status", "operational_gates", ["status"])
    op.create_index(
        "idx_op_gate_building_type",
        "operational_gates",
        ["building_id", "gate_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_op_gate_building_type", table_name="operational_gates")
    op.drop_index("idx_op_gate_status", table_name="operational_gates")
    op.drop_index("idx_op_gate_type", table_name="operational_gates")
    op.drop_index("idx_op_gate_building_id", table_name="operational_gates")
    op.drop_table("operational_gates")
