"""BatiConnect -- PublicLawRestriction (RDPPF) model.

Tracks restrictions de droit public a la propriete fonciere that impact
renovation feasibility: zone affectation, heritage protection, danger zones,
contaminated sites, water protection, alignements, servitudes, etc.
"""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PublicLawRestriction(Base):
    __tablename__ = "public_law_restrictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Restriction classification
    restriction_type = Column(
        String(50),
        nullable=False,
    )  # zone_affectation | alignement | distance | servitude_publique | protection_patrimoine | zone_danger | zone_protection_eaux | site_contamine | zone_bruit | other

    description = Column(Text, nullable=True)
    legal_reference = Column(String(200), nullable=True)  # e.g. "LAT Art. 15"
    authority = Column(String(50), nullable=True)  # commune | canton | federation

    # Temporal scope
    applies_since = Column(Date, nullable=True)
    expires_at = Column(Date, nullable=True)

    # Renovation impact
    impact_on_renovation = Column(
        String(20),
        nullable=False,
        default="none",
    )  # none | minor | major | blocking

    # Data source
    source = Column(
        String(30),
        nullable=False,
        default="manual",
    )  # rdppf | cadastre | enrichment | manual

    active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", foreign_keys=[building_id])

    __table_args__ = (
        Index("idx_plr_type", "restriction_type"),
        Index("idx_plr_impact", "impact_on_renovation"),
        Index("idx_plr_active", "building_id", "active"),
    )
