"""Add audience_packs, external_audience_redaction_profiles, decision_caveat_profiles

Revision ID: 022_add_audience_packs
Revises: 021_add_public_sector
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "022_add_audience_packs"
down_revision: str | None = "021_add_public_sector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # External Audience Redaction Profiles
    op.create_table(
        "external_audience_redaction_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_code", sa.String(50), unique=True, nullable=False),
        sa.Column("audience_type", sa.String(30), nullable=False),
        sa.Column("allowed_sections", JSON, nullable=False),
        sa.Column("blocked_sections", JSON, nullable=False),
        sa.Column("redacted_fields", JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Decision Caveat Profiles
    op.create_table(
        "decision_caveat_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("audience_type", sa.String(30), nullable=False),
        sa.Column("caveat_type", sa.String(30), nullable=False),
        sa.Column("template_text", sa.Text, nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("applies_when", JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Audience Packs
    op.create_table(
        "audience_packs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("pack_type", sa.String(30), nullable=False),
        sa.Column("pack_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("generated_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sections", JSON, nullable=False),
        sa.Column("unknowns_summary", JSON, nullable=True),
        sa.Column("contradictions_summary", JSON, nullable=True),
        sa.Column("residual_risk_summary", JSON, nullable=True),
        sa.Column("trust_refs", JSON, nullable=True),
        sa.Column("proof_refs", JSON, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("generated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("superseded_by_id", UUID(as_uuid=True), sa.ForeignKey("audience_packs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("idx_audience_packs_building_id", "audience_packs", ["building_id"])
    op.create_index("idx_audience_packs_type", "audience_packs", ["pack_type"])
    op.create_index("idx_audience_packs_status", "audience_packs", ["status"])
    op.create_index("idx_audience_packs_building_type", "audience_packs", ["building_id", "pack_type"])


def downgrade() -> None:
    op.drop_index("idx_audience_packs_building_type", table_name="audience_packs")
    op.drop_index("idx_audience_packs_status", table_name="audience_packs")
    op.drop_index("idx_audience_packs_type", table_name="audience_packs")
    op.drop_index("idx_audience_packs_building_id", table_name="audience_packs")
    op.drop_table("audience_packs")
    op.drop_table("decision_caveat_profiles")
    op.drop_table("external_audience_redaction_profiles")
