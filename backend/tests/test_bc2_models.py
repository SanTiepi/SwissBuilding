"""BatiConnect BC2 — Property management model tests.

Tests CRUD operations for 9 new models + 3 existing model modifications.
Uses the standalone SQLite session pattern from test_backbone_models.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.claim import Claim
from app.models.contract import Contract
from app.models.document_link import DocumentLink
from app.models.financial_entry import FinancialEntry
from app.models.insurance_policy import InsurancePolicy
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease, LeaseEvent
from app.models.tax_context import TaxContext

# ---------------------------------------------------------------------------
# Lease + LeaseEvent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lease(db_session, sample_building):
    lease = Lease(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        lease_type="residential",
        reference_code="BAIL-001",
        tenant_type="contact",
        tenant_id=uuid.uuid4(),
        date_start=date(2023, 1, 1),
        date_end=date(2025, 12, 31),
        rent_monthly_chf=1800.0,
        charges_monthly_chf=250.0,
        deposit_chf=5400.0,
        surface_m2=75.0,
        rooms=3.5,
        status="active",
        source_type="manual",
        confidence="declared",
    )
    db_session.add(lease)
    await db_session.commit()

    result = await db_session.execute(select(Lease).where(Lease.id == lease.id))
    fetched = result.scalar_one()
    assert fetched.lease_type == "residential"
    assert fetched.rent_monthly_chf == 1800.0
    assert fetched.rooms == 3.5
    assert fetched.source_type == "manual"


@pytest.mark.asyncio
async def test_lease_type_values(db_session, sample_building):
    for i, lt in enumerate(["residential", "commercial", "mixed", "parking", "storage", "short_term"]):
        db_session.add(
            Lease(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                lease_type=lt,
                reference_code=f"LT-{i}",
                tenant_type="contact",
                tenant_id=uuid.uuid4(),
                date_start=date(2023, 1, 1),
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(Lease))
    assert len(result.scalars().all()) == 6


@pytest.mark.asyncio
async def test_lease_status_values(db_session, sample_building):
    for i, st in enumerate(["draft", "active", "terminated", "expired", "disputed"]):
        db_session.add(
            Lease(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                lease_type="residential",
                reference_code=f"LS-{i}",
                tenant_type="contact",
                tenant_id=uuid.uuid4(),
                date_start=date(2023, 1, 1),
                status=st,
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(Lease))
    assert len(result.scalars().all()) == 5


@pytest.mark.asyncio
async def test_create_lease_event(db_session, sample_building):
    lease = Lease(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        lease_type="residential",
        reference_code="LE-001",
        tenant_type="contact",
        tenant_id=uuid.uuid4(),
        date_start=date(2023, 1, 1),
    )
    db_session.add(lease)
    await db_session.flush()

    event = LeaseEvent(
        id=uuid.uuid4(),
        lease_id=lease.id,
        event_type="rent_adjustment",
        event_date=date(2024, 1, 1),
        description="Augmentation indice reference",
        old_value_json={"rent_monthly_chf": 1800},
        new_value_json={"rent_monthly_chf": 1850},
    )
    db_session.add(event)
    await db_session.commit()

    result = await db_session.execute(select(LeaseEvent).where(LeaseEvent.lease_id == lease.id))
    fetched = result.scalar_one()
    assert fetched.event_type == "rent_adjustment"


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contract(db_session, sample_building):
    contract = Contract(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        contract_type="maintenance",
        reference_code="CTR-001",
        title="Contrat entretien chauffage",
        counterparty_type="contact",
        counterparty_id=uuid.uuid4(),
        date_start=date(2023, 1, 1),
        annual_cost_chf=3600.0,
        payment_frequency="quarterly",
        auto_renewal=True,
        status="active",
        source_type="manual",
        confidence="verified",
    )
    db_session.add(contract)
    await db_session.commit()

    result = await db_session.execute(select(Contract).where(Contract.id == contract.id))
    fetched = result.scalar_one()
    assert fetched.contract_type == "maintenance"
    assert fetched.annual_cost_chf == 3600.0
    assert fetched.auto_renewal is True


@pytest.mark.asyncio
async def test_contract_type_values(db_session, sample_building):
    types = [
        "maintenance",
        "management_mandate",
        "concierge",
        "cleaning",
        "elevator",
        "heating",
        "insurance",
        "security",
        "energy",
        "other",
    ]
    for i, ct in enumerate(types):
        db_session.add(
            Contract(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                contract_type=ct,
                reference_code=f"CT-{i}",
                title=f"Contract {ct}",
                counterparty_type="organization",
                counterparty_id=uuid.uuid4(),
                date_start=date(2023, 1, 1),
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(Contract))
    assert len(result.scalars().all()) == 10


# ---------------------------------------------------------------------------
# InsurancePolicy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_insurance_policy(db_session, sample_building):
    policy = InsurancePolicy(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        policy_type="building_eca",
        policy_number="ECA-VD-2024-001",
        insurer_name="ECA Vaud",
        insured_value_chf=1200000.0,
        premium_annual_chf=850.0,
        deductible_chf=500.0,
        date_start=date(2024, 1, 1),
        status="active",
        source_type="official",
        confidence="verified",
    )
    db_session.add(policy)
    await db_session.commit()

    result = await db_session.execute(select(InsurancePolicy).where(InsurancePolicy.id == policy.id))
    fetched = result.scalar_one()
    assert fetched.policy_type == "building_eca"
    assert fetched.insured_value_chf == 1200000.0


@pytest.mark.asyncio
async def test_insurance_policy_type_values(db_session, sample_building):
    types = [
        "building_eca",
        "rc_owner",
        "rc_building",
        "natural_hazard",
        "construction_risk",
        "complementary",
        "contents",
    ]
    for i, pt in enumerate(types):
        db_session.add(
            InsurancePolicy(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                policy_type=pt,
                policy_number=f"POL-{i}",
                insurer_name=f"Insurer {i}",
                date_start=date(2024, 1, 1),
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(InsurancePolicy))
    assert len(result.scalars().all()) == 7


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_claim(db_session, sample_building):
    policy = InsurancePolicy(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        policy_type="building_eca",
        policy_number="CLAIM-POL-001",
        insurer_name="ECA Vaud",
        date_start=date(2024, 1, 1),
    )
    db_session.add(policy)
    await db_session.flush()

    claim = Claim(
        id=uuid.uuid4(),
        insurance_policy_id=policy.id,
        building_id=sample_building.id,
        claim_type="water_damage",
        status="open",
        incident_date=date(2024, 6, 15),
        description="Degat des eaux 3e etage",
        claimed_amount_chf=25000.0,
    )
    db_session.add(claim)
    await db_session.commit()

    result = await db_session.execute(select(Claim).where(Claim.id == claim.id))
    fetched = result.scalar_one()
    assert fetched.claim_type == "water_damage"
    assert fetched.claimed_amount_chf == 25000.0


@pytest.mark.asyncio
async def test_claim_status_values(db_session, sample_building):
    policy = InsurancePolicy(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        policy_type="rc_owner",
        policy_number="CLAIM-POL-ST",
        insurer_name="Zurich",
        date_start=date(2024, 1, 1),
    )
    db_session.add(policy)
    await db_session.flush()

    for i, st in enumerate(["open", "in_review", "approved", "rejected", "settled", "closed"]):
        db_session.add(
            Claim(
                id=uuid.uuid4(),
                insurance_policy_id=policy.id,
                building_id=sample_building.id,
                claim_type="other",
                status=st,
                incident_date=date(2024, 1, i + 1),
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(Claim))
    assert len(result.scalars().all()) == 6


# ---------------------------------------------------------------------------
# FinancialEntry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_financial_entry(db_session, sample_building):
    entry = FinancialEntry(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        entry_type="income",
        category="rent_income",
        amount_chf=1800.0,
        entry_date=date(2024, 3, 1),
        fiscal_year=2024,
        description="Loyer mars 2024",
        status="recorded",
        source_type="import",
        confidence="verified",
    )
    db_session.add(entry)
    await db_session.commit()

    result = await db_session.execute(select(FinancialEntry).where(FinancialEntry.id == entry.id))
    fetched = result.scalar_one()
    assert fetched.entry_type == "income"
    assert fetched.category == "rent_income"
    assert fetched.amount_chf == 1800.0


@pytest.mark.asyncio
async def test_financial_entry_type_values(db_session, sample_building):
    for i, et in enumerate(["expense", "income"]):
        db_session.add(
            FinancialEntry(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                entry_type=et,
                category="other_expense" if et == "expense" else "other_income",
                amount_chf=100.0,
                entry_date=date(2024, 1, i + 1),
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(FinancialEntry))
    assert len(result.scalars().all()) == 2


# ---------------------------------------------------------------------------
# TaxContext
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tax_context(db_session, sample_building):
    tc = TaxContext(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        tax_type="property_tax",
        fiscal_year=2024,
        official_value_chf=950000.0,
        taxable_value_chf=760000.0,
        tax_amount_chf=2280.0,
        canton="VD",
        municipality="Lausanne",
        status="assessed",
        source_type="official",
        confidence="verified",
    )
    db_session.add(tc)
    await db_session.commit()

    result = await db_session.execute(select(TaxContext).where(TaxContext.id == tc.id))
    fetched = result.scalar_one()
    assert fetched.tax_type == "property_tax"
    assert fetched.official_value_chf == 950000.0
    assert fetched.status == "assessed"


@pytest.mark.asyncio
async def test_tax_type_values(db_session, sample_building):
    for i, tt in enumerate(["property_tax", "impot_foncier", "valeur_locative", "tax_estimation"]):
        db_session.add(
            TaxContext(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                tax_type=tt,
                fiscal_year=2024 + i,
                canton="VD",
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(TaxContext))
    assert len(result.scalars().all()) == 4


# ---------------------------------------------------------------------------
# InventoryItem
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_inventory_item(db_session, sample_building):
    item = InventoryItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        item_type="elevator",
        name="Ascenseur principal",
        manufacturer="Schindler",
        model="S5500",
        serial_number="SCH-2020-1234",
        installation_date=date(2020, 6, 1),
        warranty_end_date=date(2025, 6, 1),
        condition="good",
        purchase_cost_chf=85000.0,
        replacement_cost_chf=120000.0,
        source_type="manual",
        confidence="declared",
    )
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(select(InventoryItem).where(InventoryItem.id == item.id))
    fetched = result.scalar_one()
    assert fetched.item_type == "elevator"
    assert fetched.manufacturer == "Schindler"
    assert fetched.condition == "good"


@pytest.mark.asyncio
async def test_inventory_item_type_values(db_session, sample_building):
    types = [
        "hvac",
        "boiler",
        "elevator",
        "fire_system",
        "electrical_panel",
        "solar_panel",
        "heat_pump",
        "ventilation",
        "water_heater",
        "garage_door",
        "intercom",
        "appliance",
        "furniture",
        "other",
    ]
    for _i, it in enumerate(types):
        db_session.add(
            InventoryItem(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                item_type=it,
                name=f"Item {it}",
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(InventoryItem))
    assert len(result.scalars().all()) == 14


# ---------------------------------------------------------------------------
# DocumentLink
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_document_link(db_session, sample_building, sample_document):
    dl = DocumentLink(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        entity_type="building",
        entity_id=sample_building.id,
        link_type="attachment",
    )
    db_session.add(dl)
    await db_session.commit()

    result = await db_session.execute(select(DocumentLink).where(DocumentLink.id == dl.id))
    fetched = result.scalar_one()
    assert fetched.entity_type == "building"
    assert fetched.link_type == "attachment"


@pytest.mark.asyncio
async def test_document_link_type_values(db_session, sample_document):
    for _i, lt in enumerate(["attachment", "report", "proof", "reference", "invoice", "certificate"]):
        db_session.add(
            DocumentLink(
                id=uuid.uuid4(),
                document_id=sample_document.id,
                entity_type="building",
                entity_id=uuid.uuid4(),
                link_type=lt,
            )
        )
    await db_session.commit()
    result = await db_session.execute(select(DocumentLink))
    assert len(result.scalars().all()) == 6


# ---------------------------------------------------------------------------
# Existing model modifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervention_has_contract_id(db_session, sample_building, sample_user):
    from app.models.intervention import Intervention

    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="maintenance",
        title="Test intervention",
        created_by=sample_user.id,
    )
    db_session.add(intervention)
    await db_session.commit()
    assert hasattr(intervention, "contract_id")
    assert intervention.contract_id is None


@pytest.mark.asyncio
async def test_zone_has_usage_type(db_session, sample_zone):
    assert hasattr(sample_zone, "usage_type")
    assert sample_zone.usage_type is None


@pytest.mark.asyncio
async def test_document_has_content_hash(db_session, sample_document):
    assert hasattr(sample_document, "content_hash")
    assert sample_document.content_hash is None


# ---------------------------------------------------------------------------
# Document identity: partial unique (content_hash, file_path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_document_same_file_path_null_hash_allowed(db_session, sample_building, sample_user):
    """Same file_path with content_hash=null is allowed (no constraint fires)."""
    from app.models.document import Document

    doc1 = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/shared/report.pdf",
        file_name="report.pdf",
        uploaded_by=sample_user.id,
        content_hash=None,
    )
    doc2 = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/shared/report.pdf",
        file_name="report.pdf",
        uploaded_by=sample_user.id,
        content_hash=None,
    )
    db_session.add_all([doc1, doc2])
    await db_session.commit()

    result = await db_session.execute(select(Document).where(Document.file_path == "/shared/report.pdf"))
    assert len(result.scalars().all()) == 2


@pytest.mark.asyncio
async def test_document_different_hash_same_path_allowed(db_session, sample_building, sample_user):
    """Different content_hash with same file_path is allowed (different file content)."""
    from app.models.document import Document

    doc1 = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/versioned/doc.pdf",
        file_name="doc.pdf",
        uploaded_by=sample_user.id,
        content_hash="aaa" + "0" * 61,
    )
    doc2 = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/versioned/doc.pdf",
        file_name="doc.pdf",
        uploaded_by=sample_user.id,
        content_hash="bbb" + "0" * 61,
    )
    db_session.add_all([doc1, doc2])
    await db_session.commit()

    result = await db_session.execute(select(Document).where(Document.file_path == "/versioned/doc.pdf"))
    assert len(result.scalars().all()) == 2


# ---------------------------------------------------------------------------
# Dual-path regression: document_id + DocumentLink coexistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dual_path_document_id_and_document_link(db_session, sample_building, sample_user):
    """Proves dual-path coexistence:
    - TaxContext.document_id = primary tax notice (convenience FK)
    - DocumentLink = additional attachments for the same TaxContext
    Both paths work simultaneously on the same entity.
    """
    from app.models.document import Document

    # Create primary document (tax notice)
    primary_doc = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/tax/notice-2024.pdf",
        file_name="notice-2024.pdf",
        uploaded_by=sample_user.id,
    )
    # Create supplementary document (assessment detail)
    supplementary_doc = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/tax/assessment-detail.pdf",
        file_name="assessment-detail.pdf",
        uploaded_by=sample_user.id,
    )
    db_session.add_all([primary_doc, supplementary_doc])
    await db_session.flush()

    # TaxContext uses document_id for the primary tax notice
    tc = TaxContext(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        tax_type="property_tax",
        fiscal_year=2024,
        canton="VD",
        document_id=primary_doc.id,  # dual-path: primary document
    )
    db_session.add(tc)
    await db_session.flush()

    # DocumentLink attaches the supplementary document
    dl_supplementary = DocumentLink(
        id=uuid.uuid4(),
        document_id=supplementary_doc.id,
        entity_type="tax_context",
        entity_id=tc.id,
        link_type="reference",
    )
    # DocumentLink can also reference the primary doc with a different link_type
    dl_primary_as_proof = DocumentLink(
        id=uuid.uuid4(),
        document_id=primary_doc.id,
        entity_type="tax_context",
        entity_id=tc.id,
        link_type="proof",
    )
    db_session.add_all([dl_supplementary, dl_primary_as_proof])
    await db_session.commit()

    # Verify: TaxContext.document_id points to primary doc
    result = await db_session.execute(select(TaxContext).where(TaxContext.id == tc.id))
    fetched_tc = result.scalar_one()
    assert fetched_tc.document_id == primary_doc.id

    # Verify: DocumentLink has 2 entries for this TaxContext
    result = await db_session.execute(
        select(DocumentLink).where(
            DocumentLink.entity_type == "tax_context",
            DocumentLink.entity_id == tc.id,
        )
    )
    links = result.scalars().all()
    assert len(links) == 2
    link_types = {dl.link_type for dl in links}
    assert link_types == {"reference", "proof"}
    doc_ids = {dl.document_id for dl in links}
    assert doc_ids == {primary_doc.id, supplementary_doc.id}


# ---------------------------------------------------------------------------
# DocumentLink entity_type extensibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_document_link_entity_type_extensible(db_session, sample_document):
    """DocumentLink.entity_type is String(50), not an enum — any valid string works.
    The blueprint lists common types but the field is extensible."""
    dl = DocumentLink(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        entity_type="tax_context",  # not in the original BC2 brief list but valid per blueprint
        entity_id=uuid.uuid4(),
        link_type="attachment",
    )
    db_session.add(dl)
    await db_session.commit()

    result = await db_session.execute(select(DocumentLink).where(DocumentLink.id == dl.id))
    fetched = result.scalar_one()
    assert fetched.entity_type == "tax_context"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sample_org(db_session):
    from app.models.organization import Organization

    org = Organization(id=uuid.uuid4(), name="BC2 Test Org", type="property_management")
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def sample_user(db_session, sample_org):
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"bc2-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfakeh",
        first_name="BC2",
        last_name="Test",
        role="admin",
        organization_id=sample_org.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def sample_building(db_session, sample_user):
    from app.models.building import Building

    building = Building(
        id=uuid.uuid4(),
        address="Rue BC2 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=sample_user.id,
    )
    db_session.add(building)
    await db_session.flush()
    return building


@pytest.fixture
async def sample_zone(db_session, sample_building):
    from app.models.zone import Zone

    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        zone_type="floor",
        name="RdC",
    )
    db_session.add(zone)
    await db_session.flush()
    return zone


@pytest.fixture
async def sample_document(db_session, sample_building, sample_user):
    from app.models.document import Document

    doc = Document(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        file_path="/test/doc.pdf",
        file_name="doc.pdf",
        uploaded_by=sample_user.id,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest.fixture
async def db_session():
    """Standalone async SQLite session for BC2 tests."""
    from geoalchemy2 import Geometry
    from sqlalchemy import MetaData, String, event
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    # Import ALL models so tables are registered
    import app.models.building
    import app.models.building_portfolio
    import app.models.claim
    import app.models.contact
    import app.models.contract
    import app.models.document
    import app.models.document_link
    import app.models.financial_entry
    import app.models.insurance_policy
    import app.models.intervention
    import app.models.inventory_item
    import app.models.lease
    import app.models.organization
    import app.models.ownership_record
    import app.models.party_role_assignment
    import app.models.portfolio
    import app.models.tax_context
    import app.models.unit
    import app.models.unit_zone
    import app.models.user
    import app.models.zone  # noqa: F401
    from app.database import Base

    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine.sync_engine, "connect")
    def _register_spatial_stubs(dbapi_conn, _):
        dbapi_conn.create_function("ST_AsText", 1, lambda x: str(x) if x else None)
        dbapi_conn.create_function("ST_GeomFromText", 2, lambda wkt, srid: wkt)
        dbapi_conn.create_function("ST_AsGeoJSON", 1, lambda x: '{"type":"Point","coordinates":[0,0]}')
        dbapi_conn.create_function("GeomFromEWKT", 1, lambda x: x)
        dbapi_conn.create_function("AsEWKB", 1, lambda x: x)
        dbapi_conn.create_function("ST_GeomFromEWKT", 1, lambda x: x)
        dbapi_conn.create_function("RecoverGeometryColumn", -1, lambda *a: None)
        dbapi_conn.create_function("CheckSpatialMetaData", 0, lambda: 1)
        dbapi_conn.create_function("AddGeometryColumn", -1, lambda *a: None)
        dbapi_conn.create_function("DiscardGeometryColumn", -1, lambda *a: None)

    meta = MetaData()
    for table in Base.metadata.sorted_tables:
        new_table = table.to_metadata(meta)
        for col in new_table.columns:
            if isinstance(table.columns[col.name].type, Geometry):
                col.type = String()
                col.nullable = True
        for idx in tuple(new_table.indexes):
            if "postgresql_using" in idx.dialect_kwargs:
                new_table.indexes.discard(idx)
            if "postgresql_where" in idx.dialect_kwargs:
                new_table.indexes.discard(idx)

    async with test_engine.begin() as conn:
        await conn.run_sync(meta.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(meta.drop_all)
    await test_engine.dispose()
