"""Add subscription_changes, ai_extraction_logs tables

Revision ID: 027_add_growth_stack
Revises: 026_add_pw_truth
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "027_add_growth_stack"
down_revision: str | None = "026_add_pw_truth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SubscriptionChange
    op.create_table(
        "subscription_changes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "subscription_id",
            UUID(as_uuid=True),
            sa.ForeignKey("company_subscriptions.id"),
            nullable=False,
        ),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("old_plan", sa.String(30), nullable=True),
        sa.Column("new_plan", sa.String(30), nullable=True),
        sa.Column(
            "changed_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_sub_changes_sub_id", "subscription_changes", ["subscription_id"])

    # AIExtractionLog
    op.create_table(
        "ai_extraction_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("extraction_type", sa.String(50), nullable=False),
        sa.Column(
            "source_document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column("source_filename", sa.String(500), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_data", sa.JSON, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("ai_model", sa.String(50), nullable=True),
        sa.Column("ambiguous_fields", sa.JSON, nullable=True),
        sa.Column("unknown_fields", sa.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "confirmed_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_extraction_logs_type", "ai_extraction_logs", ["extraction_type"])
    op.create_index("idx_ai_extraction_logs_status", "ai_extraction_logs", ["status"])
    op.create_index("idx_ai_extraction_logs_hash", "ai_extraction_logs", ["input_hash"])


def downgrade() -> None:
    op.drop_table("ai_extraction_logs")
    op.drop_table("subscription_changes")
