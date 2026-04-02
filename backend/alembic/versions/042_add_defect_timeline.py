"""Add DefectTimeline model for tracking construction defect notifications per art. 367 CO.

Revision ID: 042_defect_timeline
Revises: 041_ai_feedback_v1
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "042_defect_timeline"
down_revision = "041_ai_feedback_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "defect_timelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("defect_type", sa.String(100), nullable=False),
        sa.Column("discovery_date", sa.Date, nullable=False),
        sa.Column("notification_deadline", sa.Date, nullable=False),
        sa.Column("notification_sent_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("responsible_party", sa.String(200), nullable=True),
        sa.Column("legal_reference", sa.String(100), nullable=False, server_default="art. 367 al. 1bis CO"),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_defect_timelines_building_id", "defect_timelines", ["building_id"])
    op.create_index("idx_defect_timelines_status", "defect_timelines", ["status"])
    op.create_index("idx_defect_timelines_deadline", "defect_timelines", ["notification_deadline"])


def downgrade() -> None:
    op.drop_index("idx_defect_timelines_deadline", table_name="defect_timelines")
    op.drop_index("idx_defect_timelines_status", table_name="defect_timelines")
    op.drop_index("idx_defect_timelines_building_id", table_name="defect_timelines")
    op.drop_table("defect_timelines")
