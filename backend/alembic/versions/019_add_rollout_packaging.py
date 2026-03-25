"""Add rollout + packaging tables (tenant_boundaries, delegated_access_grants, privileged_access_events, package_presets, external_viewer_profiles, bounded_embed_tokens).

Revision ID: 019_rollout_packaging
Revises: 018_demo_pilot
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019_rollout_packaging"
down_revision = "018_demo_pilot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Tenant Boundaries ---
    op.create_table(
        "tenant_boundaries",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("boundary_name", sa.String(200), nullable=False),
        sa.Column("allowed_building_ids", sa.JSON(), nullable=True),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("max_external_viewers", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- Delegated Access Grants ---
    op.create_table(
        "delegated_access_grants",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("granted_to_org_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("granted_to_email", sa.String(200), nullable=True),
        sa.Column("grant_type", sa.String(30), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=True),
        sa.Column("granted_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("granted_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # --- Privileged Access Events ---
    op.create_table(
        "privileged_access_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("building_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_entity_type", sa.String(50), nullable=True),
        sa.Column("target_entity_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- Package Presets ---
    op.create_table(
        "package_presets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("preset_code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("audience_type", sa.String(30), nullable=False),
        sa.Column("included_sections", sa.JSON(), nullable=True),
        sa.Column("excluded_sections", sa.JSON(), nullable=True),
        sa.Column("unknown_sections", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- External Viewer Profiles ---
    op.create_table(
        "external_viewer_profiles",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("viewer_type", sa.String(30), nullable=False),
        sa.Column("allowed_sections", sa.JSON(), nullable=True),
        sa.Column("requires_acknowledgement", sa.Boolean(), server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- Bounded Embed Tokens ---
    op.create_table(
        "bounded_embed_tokens",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("token", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("viewer_profile_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("external_viewer_profiles.id"), nullable=True),
        sa.Column("scope", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("view_count", sa.Integer(), server_default="0"),
        sa.Column("last_viewed_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("bounded_embed_tokens")
    op.drop_table("external_viewer_profiles")
    op.drop_table("package_presets")
    op.drop_table("privileged_access_events")
    op.drop_table("delegated_access_grants")
    op.drop_table("tenant_boundaries")
