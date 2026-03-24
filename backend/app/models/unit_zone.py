import uuid

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class UnitZone(Base):
    __tablename__ = "unit_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False, index=True)

    unit = relationship("Unit", back_populates="unit_zones")
    zone = relationship("Zone")

    __table_args__ = (UniqueConstraint("unit_id", "zone_id", name="uq_unit_zone"),)
