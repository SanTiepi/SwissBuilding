import uuid

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingPortfolio(Base):
    __tablename__ = "building_portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    added_at = Column(DateTime, default=func.now())
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    building = relationship("Building")
    portfolio = relationship("Portfolio", back_populates="building_portfolios")

    __table_args__ = (UniqueConstraint("building_id", "portfolio_id", name="uq_building_portfolio"),)
