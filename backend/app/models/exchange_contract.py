"""BatiConnect — Exchange Contract Version model.

Defines versioned contracts that govern passport/pack publication and import formats.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class ExchangeContractVersion(Base):
    __tablename__ = "exchange_contract_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_code = Column(
        String(50), nullable=False, index=True
    )  # diagnostic_report_v1 | authority_pack_v1 | building_passport_v1
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft")  # draft | active | deprecated | retired
    audience_type = Column(
        String(30), nullable=False
    )  # authority | insurer | lender | fiduciary | contractor | buyer | other
    payload_type = Column(
        String(50), nullable=False
    )  # diagnostic_report | authority_pack | transfer_package | passport_summary | building_dossier
    schema_reference = Column(String(500), nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    compatibility_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
