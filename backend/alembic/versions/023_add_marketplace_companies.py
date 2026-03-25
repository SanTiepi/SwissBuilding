"""Add company_profiles, company_verifications, company_subscriptions

Revision ID: 023_add_marketplace_co
Revises: 022_add_audience_packs
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "023_add_marketplace_co"
down_revision: str | None = "022_add_audience_packs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("legal_form", sa.String(50), nullable=True),
        sa.Column("uid_number", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("canton", sa.String(2), nullable=True),
        sa.Column("contact_email", sa.String(200), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("work_categories", JSON, nullable=False, server_default="[]"),
        sa.Column("certifications", JSON, nullable=True),
        sa.Column("regions_served", JSON, nullable=True),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("years_experience", sa.Integer, nullable=True),
        sa.Column("insurance_info", JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("profile_completeness", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_company_profiles_org", "company_profiles", ["organization_id"])
    op.create_index("idx_company_profiles_canton", "company_profiles", ["canton"])

    op.create_table(
        "company_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_profile_id", UUID(as_uuid=True), sa.ForeignKey("company_profiles.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("verified_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime, nullable=True),
        sa.Column("verification_type", sa.String(30), nullable=False, server_default="initial"),
        sa.Column("checks_performed", JSON, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_company_verifications_profile", "company_verifications", ["company_profile_id"])
    op.create_index("idx_company_verifications_status", "company_verifications", ["status"])

    op.create_table(
        "company_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_profile_id", UUID(as_uuid=True), sa.ForeignKey("company_profiles.id"), nullable=False, unique=True),
        sa.Column("plan_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("is_network_eligible", sa.Boolean, server_default=sa.text("false")),
        sa.Column("billing_reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_company_subscriptions_profile", "company_subscriptions", ["company_profile_id"])


def downgrade() -> None:
    op.drop_table("company_subscriptions")
    op.drop_table("company_verifications")
    op.drop_table("company_profiles")
