import uuid

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    egrid = Column(String(14), unique=True, nullable=True, index=True)
    egid = Column(Integer, unique=True, nullable=True, index=True)
    official_id = Column(String(20), nullable=True)
    address = Column(String(500), nullable=False)
    postal_code = Column(String(4), nullable=False)
    city = Column(String(100), nullable=False)
    canton = Column(String(2), nullable=False)
    municipality_ofs = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geom = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    parcel_number = Column(String(50), nullable=True)
    construction_year = Column(Integer, nullable=True)
    renovation_year = Column(Integer, nullable=True)
    building_type = Column(String(50), nullable=False)
    floors_above = Column(Integer, nullable=True)
    floors_below = Column(Integer, nullable=True)
    surface_area_m2 = Column(Float, nullable=True)
    volume_m3 = Column(Float, nullable=True)
    footprint_wkt = Column(Text, nullable=True)
    building_height = Column(Float, nullable=True)
    roof_type = Column(String(100), nullable=True)
    floor_count_3d = Column(Integer, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="active")
    source_dataset = Column(String(50), nullable=True)
    source_imported_at = Column(DateTime(timezone=True), nullable=True)
    source_metadata_json = Column(JSON, nullable=True)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    jurisdiction = relationship("Jurisdiction", backref="buildings")
    organization = relationship("Organization", foreign_keys=[organization_id])
    units = relationship("Unit", back_populates="building", cascade="all, delete-orphan")
    ownership_records = relationship("OwnershipRecord", back_populates="building", cascade="all, delete-orphan")
    diagnostics = relationship("Diagnostic", back_populates="building", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="building", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="building", cascade="all, delete-orphan")
    risk_scores = relationship("BuildingRiskScore", back_populates="building", uselist=False)
    action_items = relationship("ActionItem", back_populates="building", cascade="all, delete-orphan")
    zones = relationship("Zone", back_populates="building", cascade="all, delete-orphan")
    interventions = relationship("Intervention", back_populates="building", cascade="all, delete-orphan")
    technical_plans = relationship("TechnicalPlan", back_populates="building", cascade="all, delete-orphan")
    diagnostic_publications = relationship("DiagnosticReportPublication", back_populates="building")
    diagnostic_mission_orders = relationship("DiagnosticMissionOrder", back_populates="building")

    __table_args__ = (
        Index("idx_buildings_canton", "canton"),
        Index("idx_buildings_postal_code", "postal_code"),
        Index("idx_buildings_construction_year", "construction_year"),
        Index("idx_buildings_geom", "geom", postgresql_using="gist"),
    )
