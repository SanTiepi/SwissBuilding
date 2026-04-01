"""Add defect_timelines table for DefectShield module.

Art. 367 al. 1bis CO: 60 calendar days from discovery to notify.

Revision ID: 037_defect_timelines
Revises: 036_swissbuildings3d
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "037_defect_timelines"
down_revision: str | None = "036_swissbuildings3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "defect_timelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("diagnostic_id", UUID(as_uuid=True), sa.ForeignKey("diagnostics.id"), nullable=True),
        sa.Column("defect_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("discovery_date", sa.Date, nullable=False),
        sa.Column("purchase_date", sa.Date, nullable=True),
        sa.Column("notification_deadline", sa.Date, nullable=False),
        sa.Column("guarantee_type", sa.String(30), nullable=False, server_default="standard"),
        sa.Column("prescription_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("notified_at", sa.DateTime, nullable=True),
        sa.Column("notification_pdf_url", sa.String(500), nullable=True),
        # ProvenanceMixin columns
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_defect_timelines_building", "defect_timelines", ["building_id"])
    op.create_index("idx_defect_timelines_status", "defect_timelines", ["status"])
    op.create_index("idx_defect_timelines_deadline", "defect_timelines", ["notification_deadline"])
    op.create_index("idx_defect_timelines_type", "defect_timelines", ["defect_type"])


def downgrade() -> None:
    op.drop_index("idx_defect_timelines_type", table_name="defect_timelines")
    op.drop_index("idx_defect_timelines_deadline", table_name="defect_timelines")
    op.drop_index("idx_defect_timelines_status", table_name="defect_timelines")
    op.drop_index("idx_defect_timelines_building", table_name="defect_timelines")
    op.drop_table("defect_timelines")
