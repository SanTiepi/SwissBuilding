import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class FormTemplate(Base):
    """A regulatory form template (e.g., SUVA notification, cantonal declaration, waste plan)."""

    __tablename__ = "form_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    form_type = Column(String(50), nullable=False)  # suva_notification, cantonal_declaration, waste_plan, etc.
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    canton = Column(String(2), nullable=True)
    fields_schema = Column(JSON, nullable=True)  # list of field definitions with name, type, required, source_mapping
    required_attachments = Column(JSON, nullable=True)  # list of document types to attach
    version = Column(String(20), default="1.0")
    source_url = Column(String(500), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    jurisdiction = relationship("Jurisdiction")
    instances = relationship("FormInstance", back_populates="template")

    __table_args__ = (Index("idx_form_templates_type_canton", "form_type", "canton"),)


class FormInstance(Base):
    """A specific form being filled for a building/project."""

    __tablename__ = "form_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("form_templates.id"), nullable=False)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=True)

    # Status lifecycle: draft → prefilled → reviewed → submitted → complement_requested → resubmitted → acknowledged | rejected
    status = Column(String(30), nullable=False, default="draft")

    field_values = Column(JSON, nullable=True)  # filled field values with provenance per field
    attached_document_ids = Column(JSON, nullable=True)  # list of document IDs attached
    missing_fields = Column(JSON, nullable=True)  # list of fields that couldn't be pre-filled
    missing_attachments = Column(JSON, nullable=True)  # list of required attachments not yet available
    prefill_confidence = Column(Float, nullable=True)  # 0.0-1.0

    submitted_at = Column(DateTime, nullable=True)
    submission_reference = Column(String(255), nullable=True)
    complement_details = Column(Text, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    template = relationship("FormTemplate", back_populates="instances")
    building = relationship("Building")

    __table_args__ = (
        Index("idx_form_instances_building_id", "building_id"),
        Index("idx_form_instances_status", "status"),
    )
