"""Add building_enrichment_runs and building_source_snapshots tables.

Revision ID: 032_enrichment_track
Revises: 031_artifact_custody
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision = "032_enrichment_track"
down_revision = "031_artifact_custody"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "building_enrichment_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True, index=True),
        sa.Column("address_input", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sources_attempted", sa.Integer, server_default="0"),
        sa.Column("sources_succeeded", sa.Integer, server_default="0"),
        sa.Column("sources_failed", sa.Integer, server_default="0"),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "building_source_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True, index=True),
        sa.Column(
            "enrichment_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("building_enrichment_runs.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("source_name", sa.String(100), nullable=False, index=True),
        sa.Column("source_category", sa.String(50), nullable=False),
        sa.Column("raw_data", JSON, nullable=True),
        sa.Column("normalized_data", JSON, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("freshness_state", sa.String(20), nullable=False, server_default="current"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("building_source_snapshots")
    op.drop_table("building_enrichment_runs")
