"""BatiConnect - Ecosystem Engagement schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
class EcosystemEngagementCreate(BaseModel):
    actor_type: str
    actor_org_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID | None = None
    actor_name: str | None = None
    actor_email: str | None = None
    subject_type: str
    subject_id: uuid.UUID
    subject_label: str | None = None
    engagement_type: str
    comment: str | None = None
    conditions: dict | None = None
    content_hash: str | None = None
    content_version: int | None = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
class EcosystemEngagementRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    actor_type: str
    actor_org_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    actor_name: str | None
    actor_email: str | None
    subject_type: str
    subject_id: uuid.UUID
    subject_label: str | None
    engagement_type: str
    status: str
    comment: str | None
    conditions: dict | None
    content_hash: str | None
    content_version: int | None
    engaged_at: datetime
    expires_at: datetime | None
    ip_address: str | None
    user_agent: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# List (paginated)
# ---------------------------------------------------------------------------
class EcosystemEngagementList(BaseModel):
    items: list[EcosystemEngagementRead]
    count: int


# ---------------------------------------------------------------------------
# Engagement Summary (per building)
# ---------------------------------------------------------------------------
class EngagementCountByType(BaseModel):
    engagement_type: str
    count: int


class EngagementCountByActor(BaseModel):
    actor_type: str
    count: int


class EngagementSummary(BaseModel):
    building_id: uuid.UUID
    total: int
    by_actor_type: list[EngagementCountByActor]
    by_engagement_type: list[EngagementCountByType]
    latest: list[EcosystemEngagementRead]


# ---------------------------------------------------------------------------
# Engagement Timeline
# ---------------------------------------------------------------------------
class EngagementTimeline(BaseModel):
    building_id: uuid.UUID
    engagements: list[EcosystemEngagementRead]
    count: int


# ---------------------------------------------------------------------------
# Actor Engagement Profile
# ---------------------------------------------------------------------------
class ActorBuildingEngagement(BaseModel):
    building_id: uuid.UUID
    engagement_type: str
    subject_type: str
    engaged_at: datetime


class ActorEngagementProfile(BaseModel):
    actor_org_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    total: int
    engagements: list[ActorBuildingEngagement]


# ---------------------------------------------------------------------------
# Engagement Depth
# ---------------------------------------------------------------------------
class EngagementDepth(BaseModel):
    building_id: uuid.UUID
    unique_actors: int
    unique_orgs: int
    engagement_type_coverage: int  # How many distinct engagement types
    total_engagements: int
    depth_score: float  # 0.0 - 1.0 normalized score


# ---------------------------------------------------------------------------
# Contest payload
# ---------------------------------------------------------------------------
class EngagementContestCreate(BaseModel):
    comment: str
