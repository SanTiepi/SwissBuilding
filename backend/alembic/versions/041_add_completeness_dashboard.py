"""Add completeness dashboard tables.

Revision ID: 041_completeness
Revises: 040
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "041_completeness"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "completeness_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("score", sa.Float, nullable=False, server_default="0"),
        sa.Column("missing_items", sa.JSON, nullable=True),
        sa.Column("required_actions", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "completeness_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("overall_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("dimension_scores", sa.JSON, nullable=True),
        sa.Column("missing_items_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("urgent_actions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("recommended_actions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trend", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("completeness_reports")
    op.drop_table("completeness_scores")
