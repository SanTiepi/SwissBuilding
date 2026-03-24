"""Add BatiConnect canonical backbone tables

Revision ID: 005_add_backbone_tables
Revises: 004_passport_dossier_version
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "005_add_backbone_tables"
down_revision: str | None = "004_passport_dossier_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. contacts (Party)
    # ------------------------------------------------------------------
    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("contact_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("canton", sa.String(2), nullable=True),
        sa.Column("external_ref", sa.String(100), nullable=True),
        sa.Column(
            "linked_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index("idx_contacts_email", "contacts", ["email"])
    op.create_index("idx_contacts_contact_type", "contacts", ["contact_type"])
    # Partial unique: (email, organization_id) when email IS NOT NULL
    op.create_index(
        "uq_contacts_email_org",
        "contacts",
        ["email", "organization_id"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    # Partial unique: (external_ref, organization_id) when external_ref IS NOT NULL
    op.create_index(
        "uq_contacts_external_ref_org",
        "contacts",
        ["external_ref", "organization_id"],
        unique=True,
        postgresql_where=sa.text("external_ref IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # 2. party_role_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "party_role_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("party_type", sa.String(30), nullable=False),
        sa.Column("party_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("share_pct", sa.Float(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "party_type",
            "party_id",
            "entity_type",
            "entity_id",
            "role",
            name="uq_party_role_assignment",
        ),
    )
    op.create_index(
        "idx_party_roles_entity",
        "party_role_assignments",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "idx_party_roles_party",
        "party_role_assignments",
        ["party_type", "party_id"],
    )
    op.create_index("idx_party_roles_role", "party_role_assignments", ["role"])

    # ------------------------------------------------------------------
    # 3. portfolios
    # ------------------------------------------------------------------
    op.create_table(
        "portfolios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("portfolio_type", sa.String(30), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint("name", "organization_id", name="uq_portfolio_name_org"),
    )
    op.create_index("idx_portfolios_organization_id", "portfolios", ["organization_id"])

    # ------------------------------------------------------------------
    # 4. building_portfolios (junction)
    # ------------------------------------------------------------------
    op.create_table(
        "building_portfolios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "added_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.UniqueConstraint("building_id", "portfolio_id", name="uq_building_portfolio"),
    )
    op.create_index("idx_building_portfolios_building_id", "building_portfolios", ["building_id"])
    op.create_index("idx_building_portfolios_portfolio_id", "building_portfolios", ["portfolio_id"])

    # ------------------------------------------------------------------
    # 5. units
    # ------------------------------------------------------------------
    op.create_table(
        "units",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column("unit_type", sa.String(30), nullable=False),
        sa.Column("reference_code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("surface_m2", sa.Float(), nullable=True),
        sa.Column("rooms", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint("reference_code", "building_id", name="uq_unit_reference_building"),
    )
    op.create_index("idx_units_building_id", "units", ["building_id"])

    # ------------------------------------------------------------------
    # 6. unit_zones (junction)
    # ------------------------------------------------------------------
    op.create_table(
        "unit_zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "unit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("units.id"),
            nullable=False,
        ),
        sa.Column(
            "zone_id",
            UUID(as_uuid=True),
            sa.ForeignKey("zones.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("unit_id", "zone_id", name="uq_unit_zone"),
    )
    op.create_index("idx_unit_zones_unit_id", "unit_zones", ["unit_id"])
    op.create_index("idx_unit_zones_zone_id", "unit_zones", ["zone_id"])

    # ------------------------------------------------------------------
    # 7. ownership_records
    # ------------------------------------------------------------------
    op.create_table(
        "ownership_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column("owner_type", sa.String(30), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("share_pct", sa.Float(), nullable=True),
        sa.Column("ownership_type", sa.String(30), nullable=False),
        sa.Column("acquisition_type", sa.String(30), nullable=True),
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("disposal_date", sa.Date(), nullable=True),
        sa.Column("acquisition_price_chf", sa.Float(), nullable=True),
        sa.Column("land_register_ref", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index("idx_ownership_building_id", "ownership_records", ["building_id"])
    op.create_index("idx_ownership_owner", "ownership_records", ["owner_type", "owner_id"])
    op.create_index("idx_ownership_status", "ownership_records", ["status"])


def downgrade() -> None:
    op.drop_table("ownership_records")
    op.drop_table("unit_zones")
    op.drop_table("units")
    op.drop_table("building_portfolios")
    op.drop_table("portfolios")
    op.drop_table("party_role_assignments")
    op.drop_table("contacts")
