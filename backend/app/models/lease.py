import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class Lease(ProvenanceMixin, Base):
    __tablename__ = "leases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    lease_type = Column(String(30), nullable=False)  # residential | commercial | mixed | parking | storage | short_term
    reference_code = Column(String(50), nullable=False)
    tenant_type = Column(String(30), nullable=False)  # contact | user | organization
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    date_start = Column(Date, nullable=False)
    date_end = Column(Date, nullable=True)
    notice_period_months = Column(Integer, nullable=True)
    rent_monthly_chf = Column(Float, nullable=True)
    charges_monthly_chf = Column(Float, nullable=True)
    deposit_chf = Column(Float, nullable=True)
    surface_m2 = Column(Float, nullable=True)
    rooms = Column(Float, nullable=True)
    status = Column(String(20), default="active")  # draft | active | terminated | expired | disputed
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    unit = relationship("Unit")
    zone = relationship("Zone")

    __table_args__ = (UniqueConstraint("reference_code", "building_id", name="uq_lease_reference_building"),)


class LeaseEvent(Base):
    __tablename__ = "lease_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lease_id = Column(UUID(as_uuid=True), ForeignKey("leases.id"), nullable=False, index=True)
    event_type = Column(
        String(30), nullable=False
    )  # creation | renewal | rent_adjustment | notice_sent | notice_received | termination | dispute | deposit_return
    event_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    old_value_json = Column(JSON, nullable=True)
    new_value_json = Column(JSON, nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    lease = relationship("Lease")
    document = relationship("Document")
