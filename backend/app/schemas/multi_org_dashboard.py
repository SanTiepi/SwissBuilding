from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrgSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: UUID
    org_name: str
    org_type: str
    building_count: int
    risk_distribution: dict[str, int]
    completeness_avg: float
    actions_pending: int
    actions_critical: int


class MultiOrgDashboard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organizations: list[OrgSummary]
    total_buildings: int
    total_organizations: int
    global_risk_distribution: dict[str, int]
    global_completeness_avg: float


class OrgComparisonItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: UUID
    org_name: str
    metric_name: str
    metric_value: float


class MultiOrgComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[OrgComparisonItem]
    metric_names: list[str]
