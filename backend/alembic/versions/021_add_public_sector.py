"""Add public_owner_operating_modes, municipality_review_packs, committee_decision_packs,
review_decision_traces, public_asset_governance_signals

Revision ID: 021_add_public_sector
Revises: 020_add_expansion_succ
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "021_add_public_sector"
down_revision: str | None = "020_add_expansion_succ"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Public Owner Operating Modes
    op.create_table(
        "public_owner_operating_modes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("mode_type", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("governance_level", sa.String(20), server_default="standard"),
        sa.Column("requires_committee_review", sa.Boolean, server_default=sa.text("false")),
        sa.Column("requires_review_pack", sa.Boolean, server_default=sa.text("true")),
        sa.Column("default_review_audience", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("activated_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_public_owner_mode_org",
        "public_owner_operating_modes",
        ["organization_id"],
        unique=True,
    )

    # Municipality Review Packs
    op.create_table(
        "municipality_review_packs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("generated_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("pack_version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("sections", sa.JSON, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("review_deadline", sa.Date, nullable=True),
        sa.Column("circulated_to", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_review_pack_building", "municipality_review_packs", ["building_id"])

    # Committee Decision Packs
    op.create_table(
        "committee_decision_packs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("committee_name", sa.String(200), nullable=False),
        sa.Column("committee_type", sa.String(30), nullable=False),
        sa.Column("pack_version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("sections", sa.JSON, nullable=True),
        sa.Column("procurement_clauses", sa.JSON, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("decision_deadline", sa.Date, nullable=True),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_committee_pack_building", "committee_decision_packs", ["building_id"])

    # Review Decision Traces
    op.create_table(
        "review_decision_traces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_type", sa.String(30), nullable=False),
        sa.Column("pack_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_name", sa.String(200), nullable=False),
        sa.Column("reviewer_role", sa.String(100), nullable=True),
        sa.Column("reviewer_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("conditions", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("evidence_refs", sa.JSON, nullable=True),
        sa.Column("confidence_level", sa.String(20), nullable=True),
        sa.Column("decided_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_decision_trace_pack", "review_decision_traces", ["pack_type", "pack_id"])

    # Public Asset Governance Signals
    op.create_table(
        "public_asset_governance_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False, server_default="info"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_entity_type", sa.String(50), nullable=True),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resolved", sa.Boolean, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_governance_signal_org", "public_asset_governance_signals", ["organization_id"])
    op.create_index(
        "idx_governance_signal_building",
        "public_asset_governance_signals",
        ["building_id"],
    )


def downgrade() -> None:
    op.drop_table("public_asset_governance_signals")
    op.drop_table("review_decision_traces")
    op.drop_table("committee_decision_packs")
    op.drop_table("municipality_review_packs")
    op.drop_table("public_owner_operating_modes")
