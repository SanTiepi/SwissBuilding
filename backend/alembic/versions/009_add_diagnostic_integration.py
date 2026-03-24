"""Add diagnostic integration tables (publications, versions, mission orders)

Revision ID: 009_add_diag_integration
Revises: 008_add_property_mgmt_fks
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "009_add_diag_integration"
down_revision: str | None = "008_add_property_mgmt_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. diagnostic_report_publications
    # ------------------------------------------------------------------
    op.create_table(
        "diagnostic_report_publications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=True,
        ),
        sa.Column("source_system", sa.String(50), server_default="batiscan"),
        sa.Column("source_mission_id", sa.String(100), nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="1"),
        sa.Column("match_state", sa.String(20), nullable=False),
        sa.Column("match_key", sa.String(100), nullable=True),
        sa.Column("match_key_type", sa.String(20), nullable=False),
        sa.Column("report_pdf_url", sa.String(500), nullable=True),
        sa.Column("structured_summary", sa.JSON(), nullable=True),
        sa.Column("annexes", sa.JSON(), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("mission_type", sa.String(50), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_immutable",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        # ProvenanceMixin columns
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
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
        "idx_drp_building_id",
        "diagnostic_report_publications",
        ["building_id"],
    )
    op.create_index(
        "idx_drp_source_mission_id",
        "diagnostic_report_publications",
        ["source_mission_id"],
    )
    op.create_index(
        "idx_drp_match_state",
        "diagnostic_report_publications",
        ["match_state"],
    )
    op.create_index(
        "idx_drp_payload_hash",
        "diagnostic_report_publications",
        ["payload_hash"],
    )

    # ------------------------------------------------------------------
    # 2. diagnostic_publication_versions
    # ------------------------------------------------------------------
    op.create_table(
        "diagnostic_publication_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "publication_id",
            UUID(as_uuid=True),
            sa.ForeignKey("diagnostic_report_publications.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("report_pdf_url", sa.String(500), nullable=True),
        sa.Column("structured_summary", sa.JSON(), nullable=True),
        sa.Column("annexes", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_dpv_publication_id",
        "diagnostic_publication_versions",
        ["publication_id"],
    )

    # ------------------------------------------------------------------
    # 3. diagnostic_mission_orders
    # ------------------------------------------------------------------
    op.create_table(
        "diagnostic_mission_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "building_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=False,
        ),
        sa.Column(
            "requester_org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("mission_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("context_notes", sa.Text(), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("building_identifiers", sa.JSON(), nullable=True),
        sa.Column("external_mission_id", sa.String(100), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        # ProvenanceMixin columns
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
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
        "idx_dmo_building_id",
        "diagnostic_mission_orders",
        ["building_id"],
    )


def downgrade() -> None:
    op.drop_table("diagnostic_mission_orders")
    op.drop_table("diagnostic_publication_versions")
    op.drop_table("diagnostic_report_publications")
