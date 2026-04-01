"""BuildingIdentityChain — cached canonical identity chain for a building.

Stores the resolved address -> EGID -> EGRID -> RDPPF chain with provenance.
"""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingIdentityChain(Base):
    __tablename__ = "building_identity_chains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # EGID
    egid = Column(Integer, nullable=True)
    egid_source = Column(String(50), nullable=True)  # "madd", "gwr", "regbl", "manual"
    egid_confidence = Column(Float, nullable=True)
    egid_resolved_at = Column(DateTime(timezone=True), nullable=True)

    # EGRID
    egrid = Column(String(14), nullable=True)
    parcel_number = Column(String(50), nullable=True)
    parcel_area_m2 = Column(Float, nullable=True)
    egrid_source = Column(String(50), nullable=True)  # "cadastre", "regbl", "manual"
    egrid_resolved_at = Column(DateTime(timezone=True), nullable=True)

    # RDPPF
    rdppf_data = Column(JSON, nullable=True)  # {restrictions: [...], themes: [...]}
    rdppf_source = Column(String(50), nullable=True)
    rdppf_resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Chain status
    chain_complete = Column(Boolean, default=False)
    chain_gaps = Column(JSON, nullable=True)  # ["egrid_missing", "rdppf_unavailable", ...]

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    building = relationship("Building", foreign_keys=[building_id])
