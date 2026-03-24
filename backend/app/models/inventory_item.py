import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class InventoryItem(ProvenanceMixin, Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    item_type = Column(
        String(50), nullable=False
    )  # hvac | boiler | elevator | fire_system | electrical_panel | solar_panel | heat_pump | ventilation | water_heater | garage_door | intercom | appliance | furniture | other
    name = Column(String(255), nullable=False)
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    serial_number = Column(String(100), nullable=True)
    installation_date = Column(Date, nullable=True)
    warranty_end_date = Column(Date, nullable=True)
    condition = Column(String(20), nullable=True)  # good | fair | poor | critical | unknown
    purchase_cost_chf = Column(Float, nullable=True)
    replacement_cost_chf = Column(Float, nullable=True)
    maintenance_contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    zone = relationship("Zone")
    maintenance_contract = relationship("Contract")
