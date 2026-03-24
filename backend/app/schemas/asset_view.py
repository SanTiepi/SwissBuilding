from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.ownership import OwnershipRecordListRead
from app.schemas.portfolio import PortfolioListRead
from app.schemas.unit import UnitListRead


class AssetView(BaseModel):
    """Compatibility adapter: composes BuildingRead with canonical backbone relations.

    This schema enables future canonical consumers to read Building as Asset
    without changing the underlying Building model or existing API.
    """

    id: UUID
    egrid: str | None
    egid: int | None
    official_id: str | None
    address: str
    postal_code: str
    city: str
    canton: str
    building_type: str
    construction_year: int | None
    status: str
    created_at: datetime
    updated_at: datetime

    # Canonical backbone relations
    organization_id: UUID | None = None
    ownership_records: list[OwnershipRecordListRead] = []
    units: list[UnitListRead] = []
    portfolios: list[PortfolioListRead] = []

    model_config = ConfigDict(from_attributes=True)
