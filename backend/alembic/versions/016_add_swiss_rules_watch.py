"""Add SwissRules Watch + Commune Adapter tables

Revision ID: 016_add_swiss_rules_watch
Revises: 015_add_proof_delivery
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "016_add_swiss_rules"
down_revision: str | None = "015_add_proof_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. rule_sources
    op.create_table(
        "rule_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_code", sa.String(50), unique=True, nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("watch_tier", sa.String(10), nullable=False),
        sa.Column("last_checked_at", sa.DateTime, nullable=True),
        sa.Column("last_changed_at", sa.DateTime, nullable=True),
        sa.Column("freshness_state", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("change_types_detected", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 2. rule_change_events
    op.create_table(
        "rule_change_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("rule_sources.id"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("impact_summary", sa.String(500), nullable=True),
        sa.Column("detected_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("reviewed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("affects_buildings", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 3. communal_adapter_profiles
    op.create_table(
        "communal_adapter_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("commune_code", sa.String(10), nullable=False),
        sa.Column("commune_name", sa.String(200), nullable=False),
        sa.Column("canton_code", sa.String(2), nullable=False),
        sa.Column("adapter_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("supports_procedure_projection", sa.Boolean, server_default=sa.text("false")),
        sa.Column("supports_rule_projection", sa.Boolean, server_default=sa.text("false")),
        sa.Column("fallback_mode", sa.String(20), nullable=False, server_default="canton_default"),
        sa.Column("source_ids", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 4. communal_rule_overrides
    op.create_table(
        "communal_rule_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("commune_code", sa.String(10), nullable=False),
        sa.Column("canton_code", sa.String(2), nullable=False),
        sa.Column("override_type", sa.String(30), nullable=False),
        sa.Column("rule_reference", sa.String(200), nullable=True),
        sa.Column("impact_summary", sa.String(500), nullable=False),
        sa.Column("review_required", sa.Boolean, server_default=sa.text("true")),
        sa.Column("confidence_level", sa.String(20), nullable=False, server_default="review_required"),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("rule_sources.id"), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=True),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("communal_rule_overrides")
    op.drop_table("communal_adapter_profiles")
    op.drop_table("rule_change_events")
    op.drop_table("rule_sources")
