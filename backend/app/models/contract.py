import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class Contract(ProvenanceMixin, Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    contract_type = Column(
        String(30), nullable=False
    )  # maintenance | management_mandate | concierge | cleaning | elevator | heating | insurance | security | energy | other
    reference_code = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    counterparty_type = Column(String(30), nullable=False)  # contact | user | organization
    counterparty_id = Column(UUID(as_uuid=True), nullable=False)
    date_start = Column(Date, nullable=False)
    date_end = Column(Date, nullable=True)
    annual_cost_chf = Column(Float, nullable=True)
    payment_frequency = Column(String(20), nullable=True)  # monthly | quarterly | semi_annual | annual
    auto_renewal = Column(Boolean, default=False)
    notice_period_months = Column(Integer, nullable=True)
    status = Column(String(20), default="active")  # draft | active | suspended | terminated | expired
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")

    __table_args__ = (UniqueConstraint("reference_code", "building_id", name="uq_contract_reference_building"),)
