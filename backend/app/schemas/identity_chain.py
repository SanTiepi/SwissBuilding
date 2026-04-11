"""Schemas for building identity chain (address -> EGID -> EGRID -> RDPPF)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IdentityEgidDetail(BaseModel):
    value: int | None = None
    source: str | None = None
    confidence: float | None = None
    resolved_at: str | None = None


class IdentityEgridDetail(BaseModel):
    value: str | None = None
    parcel_number: str | None = None
    area_m2: float | None = None
    source: str | None = None
    resolved_at: str | None = None


class RdppfRestriction(BaseModel):
    type: str
    layer: str | None = None
    description: str | None = None
    authority: str | None = None
    in_force_since: str | None = None
    raw_attributes: dict | None = None


class IdentityRdppfDetail(BaseModel):
    restrictions: list[RdppfRestriction] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    source: str | None = None
    resolved_at: str | None = None


class IdentityChainResponse(BaseModel):
    egid: IdentityEgidDetail = Field(default_factory=IdentityEgidDetail)
    egrid: IdentityEgridDetail = Field(default_factory=IdentityEgridDetail)
    rdppf: IdentityRdppfDetail = Field(default_factory=IdentityRdppfDetail)
    chain_complete: bool = False
    chain_gaps: list[str] = Field(default_factory=list)
    cached: bool = False


class RdppfResponse(BaseModel):
    restrictions: list[RdppfRestriction] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    source: str | None = None
    resolved_at: str | None = None
