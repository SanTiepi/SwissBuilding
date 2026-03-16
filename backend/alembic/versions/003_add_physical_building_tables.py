"""Add physical building tables (zones, elements, materials, interventions,
technical_plans, evidence_links, action_items, assignments, invitations,
notifications, notification_preferences, export_jobs)

Revision ID: 003_add_physical_building_tables
Revises: 002_add_ingestion_fields
Create Date: 2026-03-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "003_add_physical_building_tables"
down_revision: Union[str, None] = "002_add_ingestion_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. zones (FK -> buildings, users, self-referential)
    # ------------------------------------------------------------------
    op.create_table(
        "zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("parent_zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=True),
        sa.Column("zone_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("floor_number", sa.Integer(), nullable=True),
        sa.Column("surface_area_m2", sa.Float(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_zones_building_id", "zones", ["building_id"])
    op.create_index("idx_zones_building_id_zone_type", "zones", ["building_id", "zone_type"])

    # ------------------------------------------------------------------
    # 2. building_elements (FK -> zones, users)
    # ------------------------------------------------------------------
    op.create_table(
        "building_elements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("element_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("condition", sa.String(20), nullable=True),
        sa.Column("installation_year", sa.Integer(), nullable=True),
        sa.Column("last_inspected_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_building_elements_zone_id", "building_elements", ["zone_id"])
    op.create_index("idx_building_elements_zone_id_element_type", "building_elements", ["zone_id", "element_type"])

    # ------------------------------------------------------------------
    # 3. materials (FK -> building_elements, samples, users)
    # ------------------------------------------------------------------
    op.create_table(
        "materials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("element_id", UUID(as_uuid=True), sa.ForeignKey("building_elements.id"), nullable=False),
        sa.Column("material_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("installation_year", sa.Integer(), nullable=True),
        sa.Column("contains_pollutant", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("pollutant_type", sa.String(50), nullable=True),
        sa.Column("pollutant_confirmed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("sample_id", UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_materials_element_id", "materials", ["element_id"])
    op.create_index("idx_materials_element_id_contains_pollutant", "materials", ["element_id", "contains_pollutant"])

    # ------------------------------------------------------------------
    # 4. interventions (FK -> buildings, users, diagnostics)
    # ------------------------------------------------------------------
    op.create_table(
        "interventions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("intervention_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'completed'")),
        sa.Column("date_start", sa.Date(), nullable=True),
        sa.Column("date_end", sa.Date(), nullable=True),
        sa.Column("contractor_name", sa.String(255), nullable=True),
        sa.Column("contractor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cost_chf", sa.Float(), nullable=True),
        sa.Column("zones_affected", sa.JSON(), nullable=True),
        sa.Column("materials_used", sa.JSON(), nullable=True),
        sa.Column("diagnostic_id", UUID(as_uuid=True), sa.ForeignKey("diagnostics.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_interventions_building_id", "interventions", ["building_id"])
    op.create_index(
        "idx_interventions_building_id_intervention_type", "interventions", ["building_id", "intervention_type"]
    )
    op.create_index("idx_interventions_status", "interventions", ["status"])

    # ------------------------------------------------------------------
    # 5. technical_plans (FK -> buildings, zones, users)
    # ------------------------------------------------------------------
    op.create_table(
        "technical_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("plan_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("floor_number", sa.Integer(), nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_technical_plans_building_id", "technical_plans", ["building_id"])
    op.create_index("idx_technical_plans_building_id_plan_type", "technical_plans", ["building_id", "plan_type"])

    # ------------------------------------------------------------------
    # 6. evidence_links (FK -> users)
    # ------------------------------------------------------------------
    op.create_table(
        "evidence_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("relationship", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("legal_reference", sa.String(255), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_evidence_links_source", "evidence_links", ["source_type", "source_id"])
    op.create_index("idx_evidence_links_target", "evidence_links", ["target_type", "target_id"])
    op.create_index("idx_evidence_links_relationship", "evidence_links", ["relationship"])

    # ------------------------------------------------------------------
    # 7. action_items (FK -> buildings, diagnostics, samples, users)
    # ------------------------------------------------------------------
    op.create_table(
        "action_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("diagnostic_id", UUID(as_uuid=True), sa.ForeignKey("diagnostics.id"), nullable=True),
        sa.Column("sample_id", UUID(as_uuid=True), sa.ForeignKey("samples.id"), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_action_items_building_id", "action_items", ["building_id"])
    op.create_index("idx_action_items_status", "action_items", ["status"])
    op.create_index("idx_action_items_priority", "action_items", ["priority"])

    # ------------------------------------------------------------------
    # 8. assignments (FK -> users)
    # ------------------------------------------------------------------
    op.create_table(
        "assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_assignments_target", "assignments", ["target_type", "target_id"])
    op.create_index("idx_assignments_user", "assignments", ["user_id"])

    # ------------------------------------------------------------------
    # 9. invitations (FK -> organizations, users)
    # ------------------------------------------------------------------
    op.create_table(
        "invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_invitations_token", "invitations", ["token"], unique=True)
    op.create_index("idx_invitations_email", "invitations", ["email"])
    op.create_index("idx_invitations_status", "invitations", ["status"])

    # ------------------------------------------------------------------
    # 10. notifications (FK -> users)
    # ------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'unread'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_notifications_user_status", "notifications", ["user_id", "status"])

    # ------------------------------------------------------------------
    # 11. notification_preferences (FK -> users)
    # ------------------------------------------------------------------
    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("in_app_actions", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("in_app_invitations", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("in_app_exports", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("digest_enabled", sa.Boolean(), server_default=sa.text("false")),
    )

    # ------------------------------------------------------------------
    # 12. export_jobs (FK -> buildings, organizations, users)
    # ------------------------------------------------------------------
    op.create_table(
        "export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("requested_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_export_jobs_status", "export_jobs", ["status"])
    op.create_index("idx_export_jobs_requested_by", "export_jobs", ["requested_by"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("export_jobs")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
    op.drop_table("invitations")
    op.drop_table("assignments")
    op.drop_table("action_items")
    op.drop_table("evidence_links")
    op.drop_table("technical_plans")
    op.drop_table("interventions")
    op.drop_table("materials")
    op.drop_table("building_elements")
    op.drop_table("zones")
