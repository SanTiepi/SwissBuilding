"""add permit_procedures, permit_steps, authority_requests tables

Revision ID: 014_permit_procs
Revises: 013_add_intake_reqs
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014_permit_procs"
down_revision = "013_add_intake_reqs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- permit_procedures --
    op.create_table(
        "permit_procedures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("procedure_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("authority_name", sa.String(200), nullable=True),
        sa.Column("authority_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("rejected_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("assigned_org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        # ProvenanceMixin
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_permit_procedures_building", "permit_procedures", ["building_id"])
    op.create_index("idx_permit_procedures_status", "permit_procedures", ["status"])
    op.create_index("idx_permit_procedures_type", "permit_procedures", ["procedure_type"])

    # -- permit_steps --
    op.create_table(
        "permit_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permit_procedures.id"), nullable=False),
        sa.Column("step_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("assigned_org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("required_documents", postgresql.JSON, nullable=True),
        sa.Column(
            "compliance_artefact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compliance_artefacts.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("step_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_permit_steps_procedure", "permit_steps", ["procedure_id"])
    op.create_index("idx_permit_steps_status", "permit_steps", ["status"])
    op.create_index("idx_permit_steps_order", "permit_steps", ["procedure_id", "step_order"])

    # -- authority_requests --
    op.create_table(
        "authority_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permit_procedures.id"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permit_steps.id"), nullable=True),
        sa.Column("request_type", sa.String(30), nullable=False),
        sa.Column("from_authority", sa.Boolean, server_default="true"),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("response_due_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("responded_at", sa.DateTime, nullable=True),
        sa.Column("linked_document_ids", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_authority_requests_procedure", "authority_requests", ["procedure_id"])
    op.create_index("idx_authority_requests_status", "authority_requests", ["status"])
    op.create_index("idx_authority_requests_type", "authority_requests", ["request_type"])


def downgrade() -> None:
    op.drop_index("idx_authority_requests_type")
    op.drop_index("idx_authority_requests_status")
    op.drop_index("idx_authority_requests_procedure")
    op.drop_table("authority_requests")
    op.drop_index("idx_permit_steps_order")
    op.drop_index("idx_permit_steps_status")
    op.drop_index("idx_permit_steps_procedure")
    op.drop_table("permit_steps")
    op.drop_index("idx_permit_procedures_type")
    op.drop_index("idx_permit_procedures_status")
    op.drop_index("idx_permit_procedures_building")
    op.drop_table("permit_procedures")
