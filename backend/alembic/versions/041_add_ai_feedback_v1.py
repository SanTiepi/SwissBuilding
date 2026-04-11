"""Add AI feedback loop v1 — field-level corrections + metrics aggregation.

Revision ID: 041_ai_feedback_v1
Revises: 040_building_passport
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "041_ai_feedback_v1"
down_revision = "040_building_passport"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend ai_feedback table with field-level columns
    op.add_column("ai_feedback", sa.Column("field_name", sa.String(100), nullable=True))
    op.add_column("ai_feedback", sa.Column("original_value", sa.String(1000), nullable=True))
    op.add_column("ai_feedback", sa.Column("corrected_value", sa.String(1000), nullable=True))
    op.add_column("ai_feedback", sa.Column("confidence_delta", sa.Float, nullable=True))
    op.add_column("ai_feedback", sa.Column("model_version", sa.String(50), nullable=True))
    op.create_index("idx_ai_feedback_field", "ai_feedback", ["entity_type", "field_name"])

    # Add ai_generated + ai_version to diagnostics
    op.add_column("diagnostics", sa.Column("ai_generated", sa.Boolean, server_default="false"))
    op.add_column("diagnostics", sa.Column("ai_version", sa.String(50), nullable=True))

    # Add ai_version to materials
    op.add_column("materials", sa.Column("ai_version", sa.String(50), nullable=True))

    # Create ai_metrics table
    op.create_table(
        "ai_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("total_extractions", sa.Integer, server_default="0"),
        sa.Column("total_corrections", sa.Integer, server_default="0"),
        sa.Column("error_rate", sa.Float, server_default="0.0"),
        sa.Column("common_errors", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_metrics_entity_field", "ai_metrics", ["entity_type", "field_name"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_ai_metrics_entity_field", table_name="ai_metrics")
    op.drop_table("ai_metrics")
    op.drop_column("materials", "ai_version")
    op.drop_column("diagnostics", "ai_version")
    op.drop_column("diagnostics", "ai_generated")
    op.drop_index("idx_ai_feedback_field", table_name="ai_feedback")
    op.drop_column("ai_feedback", "model_version")
    op.drop_column("ai_feedback", "confidence_delta")
    op.drop_column("ai_feedback", "corrected_value")
    op.drop_column("ai_feedback", "original_value")
    op.drop_column("ai_feedback", "field_name")
