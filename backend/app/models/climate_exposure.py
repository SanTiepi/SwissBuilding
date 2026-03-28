"""Climate exposure and opportunity window models for buildings.

ClimateExposureProfile: long-term climate and environmental profile (one per building).
OpportunityWindow: a detected favorable window for building action.
"""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ClimateExposureProfile(Base):
    """Long-term climate and environmental exposure profile for a building."""

    __tablename__ = "climate_exposure_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, unique=True, index=True)

    # From geo.admin overlays (cached/enriched)
    radon_zone = Column(String(50), nullable=True)
    noise_exposure_day_db = Column(Float, nullable=True)
    noise_exposure_night_db = Column(Float, nullable=True)
    solar_potential_kwh = Column(Float, nullable=True)
    natural_hazard_zones = Column(JSON, nullable=True)  # [{type, level}]
    groundwater_zone = Column(String(100), nullable=True)
    contaminated_site = Column(Boolean, nullable=True)
    heritage_status = Column(String(100), nullable=True)

    # Climate context
    heating_degree_days = Column(Float, nullable=True)
    avg_annual_precipitation_mm = Column(Float, nullable=True)
    freeze_thaw_cycles_per_year = Column(Integer, nullable=True)
    wind_exposure = Column(String(20), nullable=True)  # sheltered, moderate, exposed
    altitude_m = Column(Float, nullable=True)

    # Stress indicators
    moisture_stress = Column(String(20), nullable=False, default="unknown")  # low, moderate, high, unknown
    thermal_stress = Column(String(20), nullable=False, default="unknown")  # low, moderate, high, unknown
    uv_exposure = Column(String(20), nullable=False, default="unknown")  # low, moderate, high, unknown

    # Metadata
    data_sources = Column(JSON, nullable=True)  # [{source, fetched_at}]
    last_updated = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    building = relationship("Building", foreign_keys=[building_id])


class OpportunityWindow(Base):
    """A detected favorable window for building action."""

    __tablename__ = "opportunity_windows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), nullable=True)

    window_type = Column(
        String(30), nullable=False
    )  # weather, subsidy, permit, service, insurance, occupancy, seasonal, maintenance, market, regulatory

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Temporal
    window_start = Column(Date, nullable=False)
    window_end = Column(Date, nullable=False)
    optimal_date = Column(Date, nullable=True)

    # Why this is a good window
    advantage = Column(String(500), nullable=True)  # "saison seche", "echeance subvention", "faible occupation"

    # Risk of missing
    expiry_risk = Column(String(20), nullable=False, default="low")  # low, medium, high
    cost_of_missing = Column(String(500), nullable=True)

    # Source
    detected_by = Column(String(30), nullable=False, default="system")  # system, user, source_refresh
    confidence = Column(Float, nullable=True)  # 0-1

    # Status
    status = Column(String(20), nullable=False, default="active")  # active, used, expired, dismissed

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    building = relationship("Building", foreign_keys=[building_id])
