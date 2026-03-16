"""Initial schema — all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import geoalchemy2


revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. organizations (no FKs)
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("canton", sa.String(2), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("suva_recognized", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("fach_approved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ------------------------------------------------------------------
    # 2. users (FK -> organizations)
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("language", sa.String(2), server_default=sa.text("'fr'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # 3. buildings (FK -> users)
    # ------------------------------------------------------------------
    op.create_table(
        "buildings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("egrid", sa.String(14), nullable=True, unique=True),
        sa.Column("official_id", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("postal_code", sa.String(4), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("canton", sa.String(2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("parcel_number", sa.String(50), nullable=True),
        sa.Column("construction_year", sa.Integer(), nullable=True),
        sa.Column("renovation_year", sa.Integer(), nullable=True),
        sa.Column("building_type", sa.String(50), nullable=False),
        sa.Column("floors_above", sa.Integer(), nullable=True),
        sa.Column("floors_below", sa.Integer(), nullable=True),
        sa.Column("surface_area_m2", sa.Float(), nullable=True),
        sa.Column("volume_m3", sa.Float(), nullable=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_buildings_egrid", "buildings", ["egrid"], unique=True)
    op.create_index("idx_buildings_canton", "buildings", ["canton"])
    op.create_index("idx_buildings_postal_code", "buildings", ["postal_code"])
    op.create_index("idx_buildings_construction_year", "buildings", ["construction_year"])
    op.create_index("idx_buildings_geom", "buildings", ["geom"], postgresql_using="gist")

    # ------------------------------------------------------------------
    # 4. diagnostics (FK -> buildings, users)
    # ------------------------------------------------------------------
    op.create_table(
        "diagnostics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("diagnostic_type", sa.String(50), nullable=False),
        sa.Column("diagnostic_context", sa.String(10), server_default=sa.text("'AvT'")),
        sa.Column("status", sa.String(20), server_default=sa.text("'draft'")),
        sa.Column("diagnostician_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("laboratory", sa.String(255), nullable=True),
        sa.Column("laboratory_report_number", sa.String(100), nullable=True),
        sa.Column("date_inspection", sa.Date(), nullable=True),
        sa.Column("date_report", sa.Date(), nullable=True),
        sa.Column("report_file_path", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.String(50), nullable=True),
        sa.Column("methodology", sa.String(100), nullable=True),
        sa.Column("suva_notification_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("suva_notification_date", sa.Date(), nullable=True),
        sa.Column("canton_notification_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnostics_building_id", "diagnostics", ["building_id"])

    # ------------------------------------------------------------------
    # 5. samples (FK -> diagnostics)
    # ------------------------------------------------------------------
    op.create_table(
        "samples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("diagnostic_id", UUID(as_uuid=True), sa.ForeignKey("diagnostics.id"), nullable=False),
        sa.Column("sample_number", sa.String(50), nullable=False),
        sa.Column("location_floor", sa.String(50), nullable=True),
        sa.Column("location_room", sa.String(100), nullable=True),
        sa.Column("location_detail", sa.String(255), nullable=True),
        sa.Column("material_category", sa.String(100), nullable=True),
        sa.Column("material_description", sa.String(255), nullable=True),
        sa.Column("material_state", sa.String(50), nullable=True),
        sa.Column("pollutant_type", sa.String(50), nullable=True),
        sa.Column("pollutant_subtype", sa.String(100), nullable=True),
        sa.Column("concentration", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("threshold_exceeded", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("cfst_work_category", sa.String(20), nullable=True),
        sa.Column("action_required", sa.String(50), nullable=True),
        sa.Column("waste_disposal_type", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_samples_diagnostic_id", "samples", ["diagnostic_id"])

    # ------------------------------------------------------------------
    # 6. events (FK -> buildings, users)
    # ------------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_events_building_id", "events", ["building_id"])

    # ------------------------------------------------------------------
    # 7. documents (FK -> buildings, users)
    # ------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_building_id", "documents", ["building_id"])

    # ------------------------------------------------------------------
    # 8. pollutant_rules (no FKs)
    # ------------------------------------------------------------------
    op.create_table(
        "pollutant_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pollutant", sa.String(50), nullable=False),
        sa.Column("material_category", sa.String(100), nullable=True),
        sa.Column("risk_start_year", sa.Integer(), nullable=True),
        sa.Column("risk_end_year", sa.Integer(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("threshold_unit", sa.String(20), nullable=True),
        sa.Column("diagnostic_required", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("legal_reference", sa.String(255), nullable=True),
        sa.Column("action_if_exceeded", sa.String(500), nullable=True),
        sa.Column("waste_disposal_type", sa.String(20), nullable=True),
        sa.Column("cfst_default_category", sa.String(20), nullable=True),
        sa.Column("canton_specific", sa.String(2), nullable=True),
        sa.Column("description_fr", sa.Text(), nullable=True),
        sa.Column("description_de", sa.Text(), nullable=True),
    )
    op.create_index("ix_pollutant_rules_pollutant", "pollutant_rules", ["pollutant"])

    # ------------------------------------------------------------------
    # 9. building_risk_scores (FK -> buildings, unique)
    # ------------------------------------------------------------------
    op.create_table(
        "building_risk_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False, unique=True),
        sa.Column("asbestos_probability", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("pcb_probability", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("lead_probability", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("hap_probability", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("radon_probability", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("overall_risk_level", sa.String(20), server_default=sa.text("'unknown'")),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("factors_json", sa.JSON(), nullable=True),
        sa.Column("data_source", sa.String(50), server_default=sa.text("'model'")),
        sa.Column("last_updated", sa.DateTime(), server_default=sa.func.now()),
    )

    # ------------------------------------------------------------------
    # 10. audit_logs (FK -> users)
    # ------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("building_risk_scores")
    op.drop_table("pollutant_rules")
    op.drop_table("documents")
    op.drop_table("events")
    op.drop_table("samples")
    op.drop_table("diagnostics")
    op.drop_table("buildings")
    op.drop_table("users")
    op.drop_table("organizations")
