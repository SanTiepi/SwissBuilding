"""
BatiConnect - CommuneProfile Model

Commune-level reference data for Swiss municipalities.
BFS number is the official federal identifier for communes.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class CommuneProfile(Base):
    __tablename__ = "commune_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commune_number = Column(Integer, unique=True, nullable=False, index=True)  # BFS/OFS number
    name = Column(String(150), nullable=False)
    canton = Column(String(2), nullable=False, index=True)
    population = Column(Integer, nullable=True)
    population_year = Column(Integer, nullable=True)
    tax_multiplier = Column(Float, nullable=True)  # e.g. 1.545 for Lausanne
    median_income = Column(Integer, nullable=True)  # CHF/year
    homeowner_rate_pct = Column(Float, nullable=True)
    vacancy_rate_pct = Column(Float, nullable=True)
    unemployment_rate_pct = Column(Float, nullable=True)
    population_growth_pct = Column(Float, nullable=True)  # 5-year growth
    dominant_age_group = Column(String(20), nullable=True)  # young | mixed | aging
    financial_health = Column(String(20), nullable=True)  # excellent | good | average | poor
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
