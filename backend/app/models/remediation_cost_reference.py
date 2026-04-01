"""
RemediationCostReference — Lookup table for pollutant remediation cost estimation.

Stores Swiss market average costs per pollutant/material/condition/method combination.
Used by the cost_predictor_service to compute fourchette estimates (min/median/max).
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class RemediationCostReference(Base):
    __tablename__ = "remediation_cost_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Dimensions
    pollutant_type = Column(String(20), nullable=False, index=True)  # asbestos, pcb, lead, hap, radon, pfas
    material_type = Column(
        String(50), nullable=False, index=True
    )  # flocage, dalle_vinyle, joint, peinture, enduit, isolation, colle, revetement, other
    condition = Column(String(20), nullable=False)  # bon, degrade, friable
    method = Column(String(30), nullable=False)  # depose, encapsulation, ventilation, decapage, confinement

    # Per-m² cost range (CHF)
    cost_per_m2_min = Column(Numeric(10, 2), nullable=True)
    cost_per_m2_median = Column(Numeric(10, 2), nullable=True)
    cost_per_m2_max = Column(Numeric(10, 2), nullable=True)

    # Forfait cost range (CHF) — used for radon or fixed-price interventions
    is_forfait = Column(Boolean, default=False, nullable=False)
    forfait_min = Column(Numeric(12, 2), nullable=True)
    forfait_median = Column(Numeric(12, 2), nullable=True)
    forfait_max = Column(Numeric(12, 2), nullable=True)

    # Estimation metadata
    duration_days_estimate = Column(Integer, nullable=True)
    complexity = Column(String(20), nullable=False, default="moyenne")  # simple, moyenne, complexe

    # Description and status
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
