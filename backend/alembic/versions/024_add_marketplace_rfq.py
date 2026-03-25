"""Add client_requests, request_documents, request_invitations, quotes

Revision ID: 024_add_mktplace_rfq
Revises: 023_add_marketplace_co
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "024_add_mktplace_rfq"
down_revision: str | None = "023_add_marketplace_co"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("requester_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requester_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("pollutant_types", JSON, nullable=True),
        sa.Column("work_category", sa.String(50), nullable=False),
        sa.Column("estimated_area_m2", sa.Float, nullable=True),
        sa.Column("deadline", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "diagnostic_publication_id",
            UUID(as_uuid=True),
            sa.ForeignKey("diagnostic_report_publications.id"),
            nullable=True,
        ),
        sa.Column("budget_indication", sa.String(50), nullable=True),
        sa.Column("site_access_notes", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("closed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_client_requests_building", "client_requests", ["building_id"])
    op.create_index("idx_client_requests_status", "client_requests", ["status"])

    op.create_table(
        "request_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_request_id", UUID(as_uuid=True), sa.ForeignKey("client_requests.id"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("uploaded_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_request_documents_request", "request_documents", ["client_request_id"])

    op.create_table(
        "request_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_request_id", UUID(as_uuid=True), sa.ForeignKey("client_requests.id"), nullable=False),
        sa.Column("company_profile_id", UUID(as_uuid=True), sa.ForeignKey("company_profiles.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("viewed_at", sa.DateTime, nullable=True),
        sa.Column("responded_at", sa.DateTime, nullable=True),
        sa.Column("decline_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_request_invitations_request", "request_invitations", ["client_request_id"])
    op.create_index("idx_request_invitations_company", "request_invitations", ["company_profile_id"])

    op.create_table(
        "quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_request_id", UUID(as_uuid=True), sa.ForeignKey("client_requests.id"), nullable=False),
        sa.Column("company_profile_id", UUID(as_uuid=True), sa.ForeignKey("company_profiles.id"), nullable=False),
        sa.Column("invitation_id", UUID(as_uuid=True), sa.ForeignKey("request_invitations.id"), nullable=True),
        sa.Column("amount_chf", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CHF"),
        sa.Column("validity_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("work_plan", sa.Text, nullable=True),
        sa.Column("timeline_weeks", sa.Integer, nullable=True),
        sa.Column("includes", JSON, nullable=True),
        sa.Column("excludes", JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_quotes_request", "quotes", ["client_request_id"])
    op.create_index("idx_quotes_company", "quotes", ["company_profile_id"])


def downgrade() -> None:
    op.drop_table("quotes")
    op.drop_table("request_invitations")
    op.drop_table("request_documents")
    op.drop_table("client_requests")
