"""Evidence graph traversal schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceNode(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    label: str | None = None
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceEdge(BaseModel):
    source_type: str
    source_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relationship: str
    confidence: float | None = None
    legal_reference: str | None = None
    explanation: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceGraph(BaseModel):
    building_id: uuid.UUID
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]
    total_nodes: int
    total_edges: int
    connected_components: int


class EvidencePathStep(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    relationship: str | None = None


class EvidencePath(BaseModel):
    steps: list[EvidencePathStep]
    total_hops: int
    min_confidence: float | None = None


class EntityNeighbors(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    incoming: list[EvidenceEdge]
    outgoing: list[EvidenceEdge]
    total_connections: int


class EvidenceGraphStats(BaseModel):
    building_id: uuid.UUID
    total_links: int
    by_relationship: dict[str, int]
    by_entity_type: dict[str, int]
    avg_confidence: float | None = None
    weakest_links: list[EvidenceEdge]
    orphan_entities: list[EvidenceNode]
