"""Add post_works_links, domain_events, ai_feedback tables

Revision ID: 026_add_pw_truth
Revises: 025_add_mktplace_trust
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "026_add_pw_truth"
down_revision: str | None = "025_add_mktplace_trust"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostWorksLink
    op.create_table(
        "post_works_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "completion_confirmation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("completion_confirmations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("intervention_id", UUID(as_uuid=True), sa.ForeignKey("interventions.id"), nullable=False),
        sa.Column("before_snapshot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("after_snapshot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("grade_delta", sa.JSON, nullable=True),
        sa.Column("trust_delta", sa.JSON, nullable=True),
        sa.Column("completeness_delta", sa.JSON, nullable=True),
        sa.Column("residual_risks", sa.JSON, nullable=True),
        sa.Column("drafted_at", sa.DateTime, nullable=True),
        sa.Column("finalized_at", sa.DateTime, nullable=True),
        sa.Column("reviewed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_post_works_links_completion", "post_works_links", ["completion_confirmation_id"])
    op.create_index("idx_post_works_links_intervention", "post_works_links", ["intervention_id"])
    op.create_index("idx_post_works_links_status", "post_works_links", ["status"])

    # DomainEvent
    op.create_table(
        "domain_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_domain_events_aggregate", "domain_events", ["aggregate_type", "aggregate_id"])
    op.create_index("idx_domain_events_type", "domain_events", ["event_type"])
    op.create_index("idx_domain_events_occurred", "domain_events", ["occurred_at"])

    # AIFeedback
    op.create_table(
        "ai_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("feedback_type", sa.String(30), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("original_output", sa.JSON, nullable=True),
        sa.Column("corrected_output", sa.JSON, nullable=True),
        sa.Column("ai_model", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_feedback_entity", "ai_feedback", ["entity_type", "entity_id"])
    op.create_index("idx_ai_feedback_type", "ai_feedback", ["feedback_type"])
    op.create_index("idx_ai_feedback_user", "ai_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_table("ai_feedback")
    op.drop_table("domain_events")
    op.drop_table("post_works_links")
