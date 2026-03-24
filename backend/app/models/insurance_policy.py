import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class InsurancePolicy(ProvenanceMixin, Base):
    __tablename__ = "insurance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    policy_type = Column(
        String(30), nullable=False
    )  # building_eca | rc_owner | rc_building | natural_hazard | construction_risk | complementary | contents
    policy_number = Column(String(100), nullable=False, unique=True)
    insurer_name = Column(String(255), nullable=False)
    insurer_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    insured_value_chf = Column(Float, nullable=True)
    premium_annual_chf = Column(Float, nullable=True)
    deductible_chf = Column(Float, nullable=True)
    coverage_details_json = Column(JSON, nullable=True)
    date_start = Column(Date, nullable=False)
    date_end = Column(Date, nullable=True)
    status = Column(String(20), default="active")  # draft | active | suspended | expired | cancelled
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    contract = relationship("Contract")
    insurer_contact = relationship("Contact")
