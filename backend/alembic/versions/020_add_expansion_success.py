"""Add account_expansion_triggers, distribution_loop_signals, expansion_opportunities, customer_success_milestones

Revision ID: 020_add_expansion_succ
Revises: 018_add_demo_pilot
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "020_add_expansion_succ"
down_revision: str | None = "018_add_demo_pilot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Account Expansion Triggers
    op.create_table(
        "account_expansion_triggers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("source_entity_type", sa.String(50), nullable=True),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_summary", sa.String(500), nullable=False),
        sa.Column("detected_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_expansion_trigger_org_type", "account_expansion_triggers", ["organization_id", "trigger_type"])

    # Distribution Loop Signals
    op.create_table(
        "distribution_loop_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("audience_type", sa.String(30), nullable=True),
        sa.Column("source_entity_type", sa.String(50), nullable=True),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_distribution_signal_building", "distribution_loop_signals", ["building_id", "signal_type"])

    # Expansion Opportunities
    op.create_table(
        "expansion_opportunities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("opportunity_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="detected"),
        sa.Column("recommended_action", sa.String(500), nullable=False),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("detected_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("acted_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_expansion_opp_org_status", "expansion_opportunities", ["organization_id", "status"])

    # Customer Success Milestones
    op.create_table(
        "customer_success_milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("milestone_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("achieved_at", sa.DateTime, nullable=True),
        sa.Column("evidence_entity_type", sa.String(50), nullable=True),
        sa.Column("evidence_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_summary", sa.String(500), nullable=True),
        sa.Column("blocker_description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_cs_milestone_org_type", "customer_success_milestones", ["organization_id", "milestone_type"])
    op.create_index("idx_cs_milestone_status", "customer_success_milestones", ["status"])


def downgrade() -> None:
    op.drop_table("customer_success_milestones")
    op.drop_table("expansion_opportunities")
    op.drop_table("distribution_loop_signals")
    op.drop_table("account_expansion_triggers")
