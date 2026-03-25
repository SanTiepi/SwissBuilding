"""Add exchange contract, passport publication, import receipt, and partner trust tables

Revision ID: 017_exchange_trust
Revises: 015_add_proof_delivery
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "017_exchange_trust"
down_revision: str | None = "015_add_proof_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. exchange_contract_versions
    op.create_table(
        "exchange_contract_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("contract_code", sa.String(50), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("audience_type", sa.String(30), nullable=False),
        sa.Column("payload_type", sa.String(50), nullable=False),
        sa.Column("schema_reference", sa.String(500), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("compatibility_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 2. passport_publications
    op.create_table(
        "passport_publications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column(
            "contract_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("exchange_contract_versions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("audience_type", sa.String(30), nullable=False),
        sa.Column("publication_type", sa.String(50), nullable=False),
        sa.Column("pack_id", UUID(as_uuid=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("published_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("published_by_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("published_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("delivery_state", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "superseded_by_id", UUID(as_uuid=True), sa.ForeignKey("passport_publications.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 3. passport_import_receipts
    op.create_table(
        "passport_import_receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True, index=True),
        sa.Column("source_system", sa.String(100), nullable=False),
        sa.Column("contract_code", sa.String(50), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False),
        sa.Column("import_reference", sa.String(200), nullable=True),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "matched_publication_id",
            UUID(as_uuid=True),
            sa.ForeignKey("passport_publications.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 4. partner_trust_profiles
    op.create_table(
        "partner_trust_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "partner_org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("delivery_reliability_score", sa.Float(), nullable=True),
        sa.Column("evidence_quality_score", sa.Float(), nullable=True),
        sa.Column("responsiveness_score", sa.Float(), nullable=True),
        sa.Column("overall_trust_level", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_evaluated_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 5. partner_trust_signals
    op.create_table(
        "partner_trust_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "partner_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True
        ),
        sa.Column("signal_type", sa.String(30), nullable=False),
        sa.Column("source_entity_type", sa.String(50), nullable=True),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("partner_trust_signals")
    op.drop_table("partner_trust_profiles")
    op.drop_table("passport_import_receipts")
    op.drop_table("passport_publications")
    op.drop_table("exchange_contract_versions")
