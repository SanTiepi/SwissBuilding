"""Add ecosystem_engagements table.

Revision ID: 033_eco_engagements
Revises: 032_enrichment_track
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "033_eco_engagements"
down_revision = "032_enrichment_track"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ecosystem_engagements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        # Who engaged
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_name", sa.String(200), nullable=True),
        sa.Column("actor_email", sa.String(200), nullable=True),
        # What they engaged on
        sa.Column("subject_type", sa.String(50), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column("subject_label", sa.String(500), nullable=True),
        # The engagement
        sa.Column("engagement_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        # Content
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("conditions", sa.JSON, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("content_version", sa.Integer, nullable=True),
        # Timestamps
        sa.Column("engaged_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        # Metadata
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        # ProvenanceMixin
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        # Standard timestamps
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_eco_eng_building_id", "ecosystem_engagements", ["building_id"])
    op.create_index("idx_eco_eng_actor", "ecosystem_engagements", ["actor_type", "actor_org_id"])
    op.create_index("idx_eco_eng_subject", "ecosystem_engagements", ["subject_type", "subject_id"])
    op.create_index("idx_eco_eng_type", "ecosystem_engagements", ["engagement_type"])
    op.create_index("idx_eco_eng_status", "ecosystem_engagements", ["status"])
    op.create_index("idx_eco_eng_engaged_at", "ecosystem_engagements", ["engaged_at"])


def downgrade() -> None:
    op.drop_index("idx_eco_eng_engaged_at", table_name="ecosystem_engagements")
    op.drop_index("idx_eco_eng_status", table_name="ecosystem_engagements")
    op.drop_index("idx_eco_eng_type", table_name="ecosystem_engagements")
    op.drop_index("idx_eco_eng_subject", table_name="ecosystem_engagements")
    op.drop_index("idx_eco_eng_actor", table_name="ecosystem_engagements")
    op.drop_index("idx_eco_eng_building_id", table_name="ecosystem_engagements")
    op.drop_table("ecosystem_engagements")
