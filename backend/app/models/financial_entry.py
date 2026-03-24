import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class FinancialEntry(ProvenanceMixin, Base):
    __tablename__ = "financial_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    entry_type = Column(String(10), nullable=False)  # expense | income
    category = Column(
        String(50), nullable=False
    )  # rent_income | charges_income | maintenance | repair | renovation | insurance_premium | tax | energy | cleaning | elevator | management_fee | concierge | legal | audit | reserve_fund | interest | mortgage | depreciation | capital_gain | other_income | other_expense
    amount_chf = Column(Float, nullable=False)
    entry_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    fiscal_year = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    lease_id = Column(UUID(as_uuid=True), ForeignKey("leases.id"), nullable=True)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=True)
    insurance_policy_id = Column(UUID(as_uuid=True), ForeignKey("insurance_policies.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    external_ref = Column(String(100), nullable=True)
    status = Column(String(20), default="recorded")  # draft | recorded | validated | cancelled
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    contract = relationship("Contract")
    lease = relationship("Lease")
    intervention = relationship("Intervention")
    insurance_policy = relationship("InsurancePolicy")
    document = relationship("Document")

    __table_args__ = (
        Index("idx_financial_entries_building_fiscal_year", "building_id", "fiscal_year"),
        Index("idx_financial_entries_building_category", "building_id", "category"),
        Index("idx_financial_entries_entry_date", "entry_date"),
    )
