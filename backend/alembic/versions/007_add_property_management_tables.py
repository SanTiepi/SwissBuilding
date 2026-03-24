"""Add property management tables (BC2)

Revision ID: 007_add_property_mgmt_tables
Revises: 006_add_backbone_fks
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "007_add_property_mgmt_tables"
down_revision: str | None = "006_add_backbone_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. leases
    # ------------------------------------------------------------------
    op.create_table(
        "leases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column(
            "unit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("units.id"),
            nullable=True,
        ),
        sa.Column(
            "zone_id",
            UUID(as_uuid=True),
            sa.ForeignKey("zones.id"),
            nullable=True,
        ),
        sa.Column("lease_type", sa.String(30), nullable=False),
        sa.Column("reference_code", sa.String(50), nullable=False),
        sa.Column("tenant_type", sa.String(30), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=True),
        sa.Column("notice_period_months", sa.Integer(), nullable=True),
        sa.Column("rent_monthly_chf", sa.Float(), nullable=True),
        sa.Column("charges_monthly_chf", sa.Float(), nullable=True),
        sa.Column("deposit_chf", sa.Float(), nullable=True),
        sa.Column("surface_m2", sa.Float(), nullable=True),
        sa.Column("rooms", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
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
        sa.UniqueConstraint("reference_code", "building_id", name="uq_lease_reference_building"),
    )
    op.create_index("idx_leases_building_id", "leases", ["building_id"])

    # ------------------------------------------------------------------
    # 2. lease_events
    # ------------------------------------------------------------------
    op.create_table(
        "lease_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lease_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leases.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_value_json", sa.JSON(), nullable=True),
        sa.Column("new_value_json", sa.JSON(), nullable=True),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
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
    )
    op.create_index("idx_lease_events_lease_id", "lease_events", ["lease_id"])

    # ------------------------------------------------------------------
    # 3. contracts
    # ------------------------------------------------------------------
    op.create_table(
        "contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column("contract_type", sa.String(30), nullable=False),
        sa.Column("reference_code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("counterparty_type", sa.String(30), nullable=False),
        sa.Column("counterparty_id", UUID(as_uuid=True), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=True),
        sa.Column("annual_cost_chf", sa.Float(), nullable=True),
        sa.Column("payment_frequency", sa.String(20), nullable=True),
        sa.Column(
            "auto_renewal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("notice_period_months", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
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
        sa.UniqueConstraint("reference_code", "building_id", name="uq_contract_reference_building"),
    )
    op.create_index("idx_contracts_building_id", "contracts", ["building_id"])

    # ------------------------------------------------------------------
    # 4. insurance_policies
    # ------------------------------------------------------------------
    op.create_table(
        "insurance_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column(
            "contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
            nullable=True,
        ),
        sa.Column("policy_type", sa.String(30), nullable=False),
        sa.Column("policy_number", sa.String(100), nullable=False, unique=True),
        sa.Column("insurer_name", sa.String(255), nullable=False),
        sa.Column(
            "insurer_contact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
            nullable=True,
        ),
        sa.Column("insured_value_chf", sa.Float(), nullable=True),
        sa.Column("premium_annual_chf", sa.Float(), nullable=True),
        sa.Column("deductible_chf", sa.Float(), nullable=True),
        sa.Column("coverage_details_json", sa.JSON(), nullable=True),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
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
    op.create_index("idx_insurance_policies_building_id", "insurance_policies", ["building_id"])

    # ------------------------------------------------------------------
    # 5. claims
    # ------------------------------------------------------------------
    op.create_table(
        "claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "insurance_policy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("insurance_policies.id"),
            nullable=False,
        ),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column("claim_type", sa.String(30), nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("claimed_amount_chf", sa.Float(), nullable=True),
        sa.Column("approved_amount_chf", sa.Float(), nullable=True),
        sa.Column("paid_amount_chf", sa.Float(), nullable=True),
        sa.Column(
            "zone_id",
            UUID(as_uuid=True),
            sa.ForeignKey("zones.id"),
            nullable=True,
        ),
        sa.Column(
            "intervention_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interventions.id"),
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
    )
    op.create_index("idx_claims_insurance_policy_id", "claims", ["insurance_policy_id"])
    op.create_index("idx_claims_building_id", "claims", ["building_id"])

    # ------------------------------------------------------------------
    # 6. financial_entries
    # ------------------------------------------------------------------
    op.create_table(
        "financial_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column("entry_type", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("amount_chf", sa.Float(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
            nullable=True,
        ),
        sa.Column(
            "lease_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leases.id"),
            nullable=True,
        ),
        sa.Column(
            "intervention_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interventions.id"),
            nullable=True,
        ),
        sa.Column(
            "insurance_policy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("insurance_policies.id"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column("external_ref", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'recorded'"),
            nullable=True,
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
    op.create_index(
        "idx_financial_entries_building_fiscal",
        "financial_entries",
        ["building_id", "fiscal_year"],
    )
    op.create_index(
        "idx_financial_entries_building_category",
        "financial_entries",
        ["building_id", "category"],
    )
    op.create_index("idx_financial_entries_entry_date", "financial_entries", ["entry_date"])

    # ------------------------------------------------------------------
    # 7. tax_contexts
    # ------------------------------------------------------------------
    op.create_table(
        "tax_contexts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column("tax_type", sa.String(30), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("official_value_chf", sa.Float(), nullable=True),
        sa.Column("taxable_value_chf", sa.Float(), nullable=True),
        sa.Column("tax_amount_chf", sa.Float(), nullable=True),
        sa.Column("canton", sa.String(2), nullable=False),
        sa.Column("municipality", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'estimated'"),
            nullable=True,
        ),
        sa.Column("assessment_date", sa.Date(), nullable=True),
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
        sa.UniqueConstraint("building_id", "tax_type", "fiscal_year", name="uq_tax_context_building"),
    )
    op.create_index("idx_tax_contexts_building_id", "tax_contexts", ["building_id"])

    # ------------------------------------------------------------------
    # 8. inventory_items
    # ------------------------------------------------------------------
    op.create_table(
        "inventory_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column(
            "zone_id",
            UUID(as_uuid=True),
            sa.ForeignKey("zones.id"),
            nullable=True,
        ),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("installation_date", sa.Date(), nullable=True),
        sa.Column("warranty_end_date", sa.Date(), nullable=True),
        sa.Column("condition", sa.String(20), nullable=True),
        sa.Column("purchase_cost_chf", sa.Float(), nullable=True),
        sa.Column("replacement_cost_chf", sa.Float(), nullable=True),
        sa.Column(
            "maintenance_contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
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
    op.create_index("idx_inventory_items_building_id", "inventory_items", ["building_id"])

    # ------------------------------------------------------------------
    # 9. document_links
    # ------------------------------------------------------------------
    op.create_table(
        "document_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.String(30), nullable=False),
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
        sa.UniqueConstraint(
            "document_id",
            "entity_type",
            "entity_id",
            "link_type",
            name="uq_document_link",
        ),
    )
    op.create_index(
        "idx_document_links_entity",
        "document_links",
        ["entity_type", "entity_id"],
    )
    op.create_index("idx_document_links_document_id", "document_links", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_links")
    op.drop_table("inventory_items")
    op.drop_table("tax_contexts")
    op.drop_table("financial_entries")
    op.drop_table("claims")
    op.drop_table("insurance_policies")
    op.drop_table("contracts")
    op.drop_table("lease_events")
    op.drop_table("leases")
