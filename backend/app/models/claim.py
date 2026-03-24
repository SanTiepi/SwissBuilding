import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insurance_policy_id = Column(UUID(as_uuid=True), ForeignKey("insurance_policies.id"), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    claim_type = Column(
        String(30), nullable=False
    )  # water_damage | fire | natural_hazard | liability | theft | pollutant_related | other
    reference_number = Column(String(100), nullable=True)
    status = Column(
        String(20), nullable=False, default="open"
    )  # open | in_review | approved | rejected | settled | closed
    incident_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    claimed_amount_chf = Column(Float, nullable=True)
    approved_amount_chf = Column(Float, nullable=True)
    paid_amount_chf = Column(Float, nullable=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    insurance_policy = relationship("InsurancePolicy")
    building = relationship("Building")
    zone = relationship("Zone")
    intervention = relationship("Intervention")
