"""Add award_confirmations, completion_confirmations, reviews

Revision ID: 025_add_mktplace_trust
Revises: 024_add_mktplace_rfq
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "025_add_mktplace_trust"
down_revision: str | None = "024_add_mktplace_rfq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "award_confirmations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_request_id", UUID(as_uuid=True), sa.ForeignKey("client_requests.id"), nullable=False),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("quotes.id"), nullable=False),
        sa.Column("company_profile_id", UUID(as_uuid=True), sa.ForeignKey("company_profiles.id"), nullable=False),
        sa.Column("awarded_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("award_amount_chf", sa.Numeric(12, 2), nullable=True),
        sa.Column("conditions", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("awarded_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_award_confirmations_request", "award_confirmations", ["client_request_id"])
    op.create_index("idx_award_confirmations_quote", "award_confirmations", ["quote_id"])
    op.create_index("idx_award_confirmations_company", "award_confirmations", ["company_profile_id"])

    op.create_table(
        "completion_confirmations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "award_confirmation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("award_confirmations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("client_confirmed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("client_confirmed_at", sa.DateTime, nullable=True),
        sa.Column("client_confirmed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("company_confirmed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("company_confirmed_at", sa.DateTime, nullable=True),
        sa.Column("company_confirmed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("completion_notes", sa.Text, nullable=True),
        sa.Column("final_amount_chf", sa.Numeric(12, 2), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_completion_confirmations_award", "completion_confirmations", ["award_confirmation_id"])

    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "completion_confirmation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("completion_confirmations.id"),
            nullable=False,
        ),
        sa.Column("client_request_id", UUID(as_uuid=True), sa.ForeignKey("client_requests.id"), nullable=False),
        sa.Column("company_profile_id", UUID(as_uuid=True), sa.ForeignKey("company_profiles.id"), nullable=False),
        sa.Column("reviewer_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_type", sa.String(20), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("quality_score", sa.Integer, nullable=True),
        sa.Column("timeliness_score", sa.Integer, nullable=True),
        sa.Column("communication_score", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("moderated_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("moderated_at", sa.DateTime, nullable=True),
        sa.Column("moderation_notes", sa.Text, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_reviews_completion", "reviews", ["completion_confirmation_id"])
    op.create_index("idx_reviews_request", "reviews", ["client_request_id"])
    op.create_index("idx_reviews_company", "reviews", ["company_profile_id"])
    op.create_index("idx_reviews_status", "reviews", ["status"])


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("completion_confirmations")
    op.drop_table("award_confirmations")
