import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class OwnershipRecord(ProvenanceMixin, Base):
    __tablename__ = "ownership_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    owner_type = Column(String(30), nullable=False)  # contact | user | organization
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    share_pct = Column(Float, nullable=True)
    ownership_type = Column(String(30), nullable=False)  # full | co_ownership | usufruct | bare_ownership | ppe_unit
    acquisition_type = Column(String(30), nullable=True)  # purchase | inheritance | donation | construction | exchange
    acquisition_date = Column(Date, nullable=True)
    disposal_date = Column(Date, nullable=True)
    acquisition_price_chf = Column(Float, nullable=True)
    land_register_ref = Column(String(100), nullable=True)
    status = Column(String(20), default="active")  # active | transferred | disputed | archived
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="ownership_records")
    document = relationship("Document")

    __table_args__ = (
        Index("idx_ownership_building_id", "building_id"),
        Index("idx_ownership_owner", "owner_type", "owner_id"),
        Index("idx_ownership_status", "status"),
    )
