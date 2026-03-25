"""Add exchange hardening + contributor gateway tables

Revision ID: 030_add_xchange_hard
Revises: 029_add_consumer_brdg
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "030_add_xchange_hard"
down_revision: str | None = "029_add_consumer_brdg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. passport_state_diffs
    op.create_table(
        "passport_state_diffs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("publication_id", sa.Uuid(), sa.ForeignKey("passport_publications.id"), nullable=False, index=True),
        sa.Column("prior_publication_id", sa.Uuid(), sa.ForeignKey("passport_publications.id"), nullable=True),
        sa.Column("diff_summary", sa.JSON(), nullable=True),
        sa.Column("sections_changed_count", sa.Integer(), default=0),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 2. exchange_validation_reports
    op.create_table(
        "exchange_validation_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "import_receipt_id", sa.Uuid(), sa.ForeignKey("passport_import_receipts.id"), nullable=False, index=True
        ),
        sa.Column("schema_valid", sa.Boolean(), nullable=True),
        sa.Column("contract_valid", sa.Boolean(), nullable=True),
        sa.Column("version_valid", sa.Boolean(), nullable=True),
        sa.Column("hash_valid", sa.Boolean(), nullable=True),
        sa.Column("identity_safe", sa.Boolean(), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("overall_status", sa.String(20), nullable=False, server_default="review_required"),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
        sa.Column("validated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 3. external_reliance_signals
    op.create_table(
        "external_reliance_signals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "publication_id", sa.Uuid(), sa.ForeignKey("passport_publications.id"), nullable=True, index=True
        ),
        sa.Column(
            "import_receipt_id", sa.Uuid(), sa.ForeignKey("passport_import_receipts.id"), nullable=True, index=True
        ),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("partner_org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 4. partner_webhook_subscriptions
    op.create_table(
        "partner_webhook_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("partner_org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("endpoint_url", sa.String(500), nullable=False),
        sa.Column("hmac_secret", sa.String(100), nullable=False),
        sa.Column("subscribed_events", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 5. partner_delivery_attempts
    op.create_table(
        "partner_delivery_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "subscription_id",
            sa.Uuid(),
            sa.ForeignKey("partner_webhook_subscriptions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(100), unique=True, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 6. contributor_gateway_requests
    op.create_table(
        "contributor_gateway_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("building_id", sa.Uuid(), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("contributor_type", sa.String(20), nullable=False),
        sa.Column("scope_description", sa.Text(), nullable=True),
        sa.Column("access_token", sa.String(100), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("linked_procedure_id", sa.Uuid(), nullable=True),
        sa.Column("linked_remediation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 7. contributor_submissions
    op.create_table(
        "contributor_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "request_id",
            sa.Uuid(),
            sa.ForeignKey("contributor_gateway_requests.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("contributor_org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("contributor_name", sa.String(200), nullable=True),
        sa.Column("submission_type", sa.String(50), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("reviewed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 8. contributor_receipts
    op.create_table(
        "contributor_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "submission_id", sa.Uuid(), sa.ForeignKey("contributor_submissions.id"), nullable=False, unique=True
        ),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("evidence_link_id", sa.Uuid(), nullable=True),
        sa.Column("proof_delivery_id", sa.Uuid(), nullable=True),
        sa.Column("receipt_hash", sa.String(64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("contributor_receipts")
    op.drop_table("contributor_submissions")
    op.drop_table("contributor_gateway_requests")
    op.drop_table("partner_delivery_attempts")
    op.drop_table("partner_webhook_subscriptions")
    op.drop_table("external_reliance_signals")
    op.drop_table("exchange_validation_reports")
    op.drop_table("passport_state_diffs")
