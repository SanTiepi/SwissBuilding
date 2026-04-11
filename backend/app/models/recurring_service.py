"""BatiConnect — RecurringService and WarrantyRecord models for everyday building memory."""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class RecurringService(ProvenanceMixin, Base):
    """A recurring service contract or vendor relationship for a building."""

    __tablename__ = "recurring_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    service_type = Column(
        String(30), nullable=False
    )  # maintenance | cleaning | security | elevator | heating | garden | pest_control | fire_inspection | chimney | energy_monitoring | waste | other

    provider_name = Column(String(255), nullable=False)
    provider_contact = Column(String(255), nullable=True)
    provider_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Contract
    contract_reference = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    renewal_type = Column(String(20), nullable=False, default="auto")  # auto | manual | fixed_term
    notice_period_days = Column(Integer, nullable=True)

    # Cost
    annual_cost_chf = Column(Float, nullable=True)
    payment_frequency = Column(String(20), nullable=True)  # monthly | quarterly | annual

    # Schedule
    frequency = Column(String(20), nullable=False)  # weekly | monthly | quarterly | semi_annual | annual | on_demand
    last_service_date = Column(Date, nullable=True)
    next_service_date = Column(Date, nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="active")  # active | paused | terminated | expired

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    organization = relationship("Organization", foreign_keys=[organization_id])
    provider_org = relationship("Organization", foreign_keys=[provider_org_id])

    __table_args__ = (
        Index("idx_recurring_services_status", "status"),
        Index("idx_recurring_services_next_date", "next_service_date"),
        Index("idx_recurring_services_type", "service_type"),
    )


class WarrantyRecord(ProvenanceMixin, Base):
    """A warranty or guarantee on building work or equipment."""

    __tablename__ = "warranty_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    warranty_type = Column(
        String(30), nullable=False
    )  # works | equipment | material | system | waterproofing | roof | facade | structural | other

    subject = Column(String(500), nullable=False)  # what is covered
    provider_name = Column(String(255), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_months = Column(Integer, nullable=True)

    # Coverage
    coverage_description = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)

    # Documents
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="active")  # active | expired | claimed | voided

    # Claim tracking
    claim_filed = Column(Boolean, default=False)
    claim_date = Column(Date, nullable=True)
    claim_description = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    case = relationship("BuildingCase")
    organization = relationship("Organization")
    document = relationship("Document")

    __table_args__ = (
        Index("idx_warranty_records_status", "status"),
        Index("idx_warranty_records_end_date", "end_date"),
        Index("idx_warranty_records_type", "warranty_type"),
    )
