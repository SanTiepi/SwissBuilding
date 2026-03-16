"""Pydantic v2 schemas for the Constraint Graph service."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConstraintNode(BaseModel):
    """A single node in the constraint graph."""

    node_id: str
    node_type: str  # diagnostic|intervention|action|compliance_check|readiness_gate|evidence_requirement
    label: str
    status: str  # blocked|ready|in_progress|completed|not_applicable
    priority: int | None = None
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class ConstraintEdge(BaseModel):
    """A directed edge between two constraint nodes."""

    from_node: str
    to_node: str
    edge_type: str  # blocks|requires|enables|triggers
    description: str | None = None
    is_hard: bool = True

    model_config = ConfigDict(from_attributes=True)


class ConstraintGraph(BaseModel):
    """Full constraint graph for a building."""

    building_id: UUID
    nodes: list[ConstraintNode]
    edges: list[ConstraintEdge]
    total_nodes: int
    total_edges: int
    blocked_count: int
    ready_count: int

    model_config = ConfigDict(from_attributes=True)


class CriticalPath(BaseModel):
    """The longest chain of blocked dependencies to full readiness."""

    building_id: UUID
    path: list[ConstraintNode]
    total_steps: int
    blocked_steps: int
    estimated_unlock_value: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UnlockAnalysis(BaseModel):
    """Analysis of what completing a node would unblock."""

    building_id: UUID
    node_id: str
    label: str
    unlocks: list[str]
    unlock_count: int
    priority_score: float

    model_config = ConfigDict(from_attributes=True)


class ReadinessBlocker(BaseModel):
    """A human-readable blocker preventing readiness."""

    building_id: UUID
    blocker_type: str
    description: str
    blocked_by: list[str]
    can_unblock: list[str]

    model_config = ConfigDict(from_attributes=True)


class SimulateCompletionRequest(BaseModel):
    """Request body for simulate-completion endpoint."""

    node_ids: list[str]
