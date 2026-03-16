"""
SwissBuildingOS - Zone Classification Schemas

Pydantic v2 schemas for zone contamination classification, hierarchy roll-up,
boundary zone identification, and transition history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ContaminationStatus(StrEnum):
    clean = "clean"
    suspected = "suspected"
    confirmed_low = "confirmed_low"
    confirmed_high = "confirmed_high"
    remediated = "remediated"
    under_monitoring = "under_monitoring"


# Severity order for worst-status roll-up
CONTAMINATION_SEVERITY: dict[ContaminationStatus, int] = {
    ContaminationStatus.clean: 0,
    ContaminationStatus.remediated: 1,
    ContaminationStatus.under_monitoring: 2,
    ContaminationStatus.suspected: 3,
    ContaminationStatus.confirmed_low: 4,
    ContaminationStatus.confirmed_high: 5,
}


# --------------------------------------------------------------------------
# FN1 -classify_zones
# --------------------------------------------------------------------------


class ZoneClassification(BaseModel):
    zone_id: uuid.UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    contamination_status: ContaminationStatus
    pollutants_found: list[str] = []
    sample_count: int = 0
    threshold_exceeded_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ZoneClassificationResult(BaseModel):
    building_id: uuid.UUID
    total_zones: int
    classified_zones: list[ZoneClassification]
    summary: dict[str, int]  # status -> count

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# FN2 -get_zone_hierarchy
# --------------------------------------------------------------------------


class ZoneHierarchyNode(BaseModel):
    zone_id: uuid.UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    own_status: ContaminationStatus
    rolled_up_status: ContaminationStatus
    children: list[ZoneHierarchyNode] = []

    model_config = ConfigDict(from_attributes=True)


class FloorSummary(BaseModel):
    floor_number: int | None
    worst_status: ContaminationStatus
    zone_count: int


class ZoneHierarchyResult(BaseModel):
    building_id: uuid.UUID
    building_status: ContaminationStatus
    floor_summaries: list[FloorSummary]
    tree: list[ZoneHierarchyNode]

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# FN3 -identify_boundary_zones
# --------------------------------------------------------------------------


class BoundaryZone(BaseModel):
    zone_id: uuid.UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    own_status: ContaminationStatus
    adjacent_contaminated_zones: list[uuid.UUID]
    recommended_measures: list[str]

    model_config = ConfigDict(from_attributes=True)


class BoundaryZoneResult(BaseModel):
    building_id: uuid.UUID
    boundary_zones: list[BoundaryZone]
    total_boundary_zones: int

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# FN4 -get_zone_transition_history
# --------------------------------------------------------------------------


class StatusTransition(BaseModel):
    from_status: ContaminationStatus | None = None
    to_status: ContaminationStatus
    timestamp: datetime
    reason: str | None = None


class ZoneTransitionHistory(BaseModel):
    zone_id: uuid.UUID
    zone_name: str
    current_status: ContaminationStatus
    transitions: list[StatusTransition]

    model_config = ConfigDict(from_attributes=True)


class ZoneTransitionHistoryResult(BaseModel):
    building_id: uuid.UUID
    zone_histories: list[ZoneTransitionHistory]

    model_config = ConfigDict(from_attributes=True)
