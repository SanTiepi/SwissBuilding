"""Schemas for data provenance tracking."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceRecord(BaseModel):
    """Single provenance entry for an entity."""

    entity_type: str
    entity_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: uuid.UUID | None = None
    created_by_email: str | None = None
    source: str = "manual"  # manual | import | api | automated
    source_dataset: str | None = None
    source_imported_at: datetime | None = None
    transformations: list[str] = Field(default_factory=list)
    parent_entity_type: str | None = None
    parent_entity_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class DataLineageNode(BaseModel):
    """A single node in the data lineage DAG."""

    entity_type: str
    entity_id: uuid.UUID
    label: str
    source: str = "manual"
    created_at: datetime | None = None
    created_by: uuid.UUID | None = None
    children: list["DataLineageNode"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DataLineageTree(BaseModel):
    """Full lineage tree rooted at a building."""

    building_id: uuid.UUID
    root: DataLineageNode
    total_nodes: int = 0
    entity_counts: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class IntegrityIssue(BaseModel):
    """A single data integrity issue."""

    issue_type: str  # orphan | missing_source | date_inconsistency | missing_samples | missing_creator
    severity: str = "warning"  # info | warning | error
    entity_type: str
    entity_id: uuid.UUID | None = None
    description: str
    field_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class IntegrityReport(BaseModel):
    """Full integrity report for a building."""

    building_id: uuid.UUID
    checked_at: datetime
    total_issues: int = 0
    issues_by_severity: dict[str, int] = Field(default_factory=dict)
    issues: list[IntegrityIssue] = Field(default_factory=list)
    is_clean: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProvenanceStatistics(BaseModel):
    """Organization-level provenance statistics."""

    organization_id: uuid.UUID | None = None
    total_buildings: int = 0
    total_diagnostics: int = 0
    total_samples: int = 0
    total_documents: int = 0
    total_actions: int = 0
    source_breakdown: dict[str, int] = Field(default_factory=dict)
    import_percentage: float = 0.0
    manual_percentage: float = 0.0
    avg_freshness_days: float | None = None
    traceability_coverage: float = 0.0
    data_quality_score: float = 0.0

    model_config = ConfigDict(from_attributes=True)
