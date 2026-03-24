import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class TaxContext(ProvenanceMixin, Base):
    __tablename__ = "tax_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    tax_type = Column(String(30), nullable=False)  # property_tax | impot_foncier | valeur_locative | tax_estimation
    fiscal_year = Column(Integer, nullable=False)
    official_value_chf = Column(Float, nullable=True)
    taxable_value_chf = Column(Float, nullable=True)
    tax_amount_chf = Column(Float, nullable=True)
    canton = Column(String(2), nullable=False)
    municipality = Column(String(100), nullable=True)
    status = Column(String(20), default="estimated")  # estimated | assessed | contested | final
    assessment_date = Column(Date, nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    document = relationship("Document")

    __table_args__ = (
        UniqueConstraint("building_id", "tax_type", "fiscal_year", name="uq_tax_context_building_type_year"),
    )
