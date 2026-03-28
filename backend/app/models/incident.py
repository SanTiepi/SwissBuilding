"""
BatiConnect - Incident & Damage Memory

Explicit memory for leaks, mold, flooding, fire, subsidence, breakage,
recurring failures. Critical for insurer readiness, recurring risk memory,
and transfer truth.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class IncidentEpisode(Base):
    """An incident or damage event in the building's lifecycle."""

    __tablename__ = "incident_episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # Type
    incident_type = Column(
        String(30), nullable=False
    )  # leak | mold | flooding | fire | subsidence | movement | breakage | equipment_failure | vandalism | storm_damage | pest | contamination | structural | other

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Temporal
    discovered_at = Column(DateTime, nullable=False, default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # Location
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)
    location_description = Column(String(500), nullable=True)

    # Severity
    severity = Column(String(20), nullable=False, default="minor")  # minor | moderate | major | critical

    # Impact
    affected_units = Column(JSON, nullable=True)  # which units/spaces affected
    occupant_impact = Column(Boolean, nullable=False, default=False)
    service_disruption = Column(Boolean, nullable=False, default=False)

    # Cause
    cause_description = Column(Text, nullable=True)
    cause_category = Column(
        String(20), nullable=False, default="unknown"
    )  # wear | defect | external | accident | negligence | unknown
    recurring = Column(Boolean, nullable=False, default=False)
    previous_incident_id = Column(UUID(as_uuid=True), ForeignKey("incident_episodes.id"), nullable=True)

    # Response
    response_description = Column(Text, nullable=True)
    repair_cost_chf = Column(Float, nullable=True)

    # Insurance
    insurance_claim_filed = Column(Boolean, nullable=False, default=False)
    insurance_claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)

    # Evidence
    evidence_document_ids = Column(JSON, nullable=True)  # photos, reports

    # Status
    status = Column(
        String(30), nullable=False, default="reported"
    )  # reported | investigating | repair_in_progress | resolved | monitoring | recurring_unresolved

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    organization = relationship("Organization")
    zone = relationship("Zone")
    element = relationship("BuildingElement")
    insurance_claim = relationship("Claim", foreign_keys=[insurance_claim_id])
    previous_incident = relationship("IncidentEpisode", remote_side=[id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    damage_observations = relationship("DamageObservation", back_populates="incident")

    __table_args__ = (
        Index("idx_incident_episodes_building_id", "building_id"),
        Index("idx_incident_episodes_status", "status"),
        Index("idx_incident_episodes_incident_type", "incident_type"),
        Index("idx_incident_episodes_building_status", "building_id", "status"),
        Index("idx_incident_episodes_building_type", "building_id", "incident_type"),
    )


class DamageObservation(Base):
    """A specific damage observation linked to an incident or routine inspection."""

    __tablename__ = "damage_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incident_episodes.id"), nullable=True)

    # Type
    damage_type = Column(
        String(30), nullable=False
    )  # crack | stain | corrosion | deformation | efflorescence | peeling | rot | erosion | displacement | other

    location_description = Column(String(500), nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)

    # Assessment
    severity = Column(String(20), nullable=False, default="cosmetic")  # cosmetic | functional | structural | safety
    progression = Column(String(20), nullable=False, default="unknown")  # stable | slow | rapid | unknown

    # Observation
    observed_at = Column(DateTime, nullable=False, default=func.now())
    observed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Evidence
    photo_document_ids = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    building = relationship("Building")
    incident = relationship("IncidentEpisode", back_populates="damage_observations")
    zone = relationship("Zone")
    element = relationship("BuildingElement")
    observed_by = relationship("User", foreign_keys=[observed_by_id])

    __table_args__ = (
        Index("idx_damage_observations_building_id", "building_id"),
        Index("idx_damage_observations_incident_id", "incident_id"),
        Index("idx_damage_observations_damage_type", "damage_type"),
    )
