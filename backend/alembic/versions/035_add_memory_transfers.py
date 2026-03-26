"""Add memory_transfers table.

Revision ID: 035_memory_transfers
Revises: 033_eco_engagements
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "035_memory_transfers"
down_revision = "033_eco_engagements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_transfers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        # Transfer type
        sa.Column("transfer_type", sa.String(50), nullable=False),
        sa.Column("transfer_label", sa.String(500), nullable=False),
        # Parties
        sa.Column("from_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("from_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("to_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("to_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        # Status
        sa.Column("status", sa.String(30), nullable=False, server_default="initiated"),
        # Memory snapshot
        sa.Column("memory_snapshot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("transfer_package_hash", sa.String(64), nullable=True),
        # Content
        sa.Column("memory_sections", sa.JSON, nullable=True),
        sa.Column("sections_count", sa.Integer, server_default="0"),
        sa.Column("documents_count", sa.Integer, server_default="0"),
        sa.Column("engagements_count", sa.Integer, server_default="0"),
        sa.Column("timeline_events_count", sa.Integer, server_default="0"),
        # Verification
        sa.Column("integrity_verified", sa.Boolean, server_default="false"),
        sa.Column("integrity_verified_at", sa.DateTime, nullable=True),
        # Acceptance
        sa.Column("accepted_at", sa.DateTime, nullable=True),
        sa.Column("accepted_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("acceptance_comment", sa.Text, nullable=True),
        # Contest
        sa.Column("contested_at", sa.DateTime, nullable=True),
        sa.Column("contested_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("contest_comment", sa.Text, nullable=True),
        # Timestamps
        sa.Column("initiated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        # Provenance mixin
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
    )

    op.create_index("idx_mem_transfer_building", "memory_transfers", ["building_id"])
    op.create_index("idx_mem_transfer_status", "memory_transfers", ["status"])
    op.create_index("idx_mem_transfer_type", "memory_transfers", ["transfer_type"])
    op.create_index("idx_mem_transfer_from_org", "memory_transfers", ["from_org_id"])
    op.create_index("idx_mem_transfer_to_org", "memory_transfers", ["to_org_id"])
    op.create_index("idx_mem_transfer_initiated", "memory_transfers", ["initiated_at"])


def downgrade() -> None:
    op.drop_index("idx_mem_transfer_initiated", table_name="memory_transfers")
    op.drop_index("idx_mem_transfer_to_org", table_name="memory_transfers")
    op.drop_index("idx_mem_transfer_from_org", table_name="memory_transfers")
    op.drop_index("idx_mem_transfer_type", table_name="memory_transfers")
    op.drop_index("idx_mem_transfer_status", table_name="memory_transfers")
    op.drop_index("idx_mem_transfer_building", table_name="memory_transfers")
    op.drop_table("memory_transfers")
