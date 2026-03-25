"""BatiConnect — Expansion signal models for adoption loop tracking.

AccountExpansionTrigger: signals that an org is ready to expand usage.
DistributionLoopSignal: signals that content is being shared/viewed externally.
ExpansionOpportunity: qualified opportunities derived from triggers/signals.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class AccountExpansionTrigger(Base):
    __tablename__ = "account_expansion_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    trigger_type = Column(
        String(50), nullable=False
    )  # second_actor_active | second_building_active | pack_consulted | proof_reused | blocker_resolved | external_embed_viewed | authority_pack_acknowledged
    source_entity_type = Column(String(50), nullable=True)
    source_entity_id = Column(UUID(as_uuid=True), nullable=True)
    evidence_summary = Column(String(500), nullable=False)
    detected_at = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (Index("idx_expansion_trigger_org_type", "organization_id", "trigger_type"),)


class DistributionLoopSignal(Base):
    __tablename__ = "distribution_loop_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    signal_type = Column(
        String(50), nullable=False
    )  # embed_created | embed_viewed | pack_shared | pack_acknowledged | viewer_returned | second_audience_reached
    audience_type = Column(String(30), nullable=True)
    source_entity_type = Column(String(50), nullable=True)
    source_entity_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (Index("idx_distribution_signal_building", "building_id", "signal_type"),)


class ExpansionOpportunity(Base):
    __tablename__ = "expansion_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    opportunity_type = Column(
        String(50), nullable=False
    )  # add_building | add_actor | upgrade_preset | extend_audience | deepen_proof
    status = Column(String(20), nullable=False, default="detected")  # detected | qualified | acted | dismissed
    recommended_action = Column(String(500), nullable=False)
    evidence = Column(JSON, nullable=True)  # [{signal_type, entity, date}]
    priority = Column(String(10), nullable=False, default="medium")  # high | medium | low
    detected_at = Column(DateTime, nullable=False, default=func.now())
    acted_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_expansion_opp_org_status", "organization_id", "status"),)
