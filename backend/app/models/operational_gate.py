"""BatiConnect - Operational Gate model.

A blocking gate that requires specific conditions before an operation can proceed.
SwissBuilding doesn't just measure — it BLOCKS. Impossible to launch an RFQ without
proof, close a lot without confirmation, or transfer without chain.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base
from app.models.mixins import ProvenanceMixin


class OperationalGate(Base, ProvenanceMixin):
    """A blocking gate that requires specific conditions before an operation can proceed."""

    __tablename__ = "operational_gates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # Gate identity
    gate_type = Column(
        String(50), nullable=False
    )  # launch_rfq | close_lot | transfer_dossier | start_works | submit_authority | deliver_pack | change_management | refinance | sell | reopen_after_works

    gate_label = Column(String(300), nullable=False)  # French human-readable

    # Gate status
    status = Column(
        String(30), nullable=False, default="blocked"
    )  # blocked | conditions_pending | clearable | cleared | overridden | expired

    # What blocks it — list of prerequisite dicts
    prerequisites = Column(JSON, nullable=False, default=list)
    # Each: {"type": "engagement|document|proof_chain|diagnostic|obligation|procedure|pack|safe_to_start",
    #         "subject_type": "...", "engagement_type": "...", "label": "...",
    #         "satisfied": bool, "item_id": uuid|null}

    # Override (admin bypass with audit trail)
    overridden_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    override_reason = Column(Text, nullable=True)
    overridden_at = Column(DateTime, nullable=True)

    # Cleared (all prerequisites satisfied)
    cleared_at = Column(DateTime, nullable=True)
    cleared_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Auto-evaluate prerequisites on query
    auto_evaluate = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_op_gate_building_id", "building_id"),
        Index("idx_op_gate_type", "gate_type"),
        Index("idx_op_gate_status", "status"),
        Index("idx_op_gate_building_type", "building_id", "gate_type", unique=True),
    )
