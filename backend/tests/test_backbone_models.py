"""BatiConnect BC1 — Backbone model tests.

Tests CRUD operations and constraints for the 7 new canonical backbone models.
Uses SQLite in-memory (same pattern as conftest.py).
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select

# Import new models so SQLAlchemy registers their tables
from app.models.building_portfolio import BuildingPortfolio
from app.models.contact import Contact
from app.models.ownership_record import OwnershipRecord
from app.models.party_role_assignment import PartyRoleAssignment
from app.models.portfolio import Portfolio
from app.models.unit import Unit
from app.models.unit_zone import UnitZone

# ---------------------------------------------------------------------------
# Contact (= Party)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contact(db_session, sample_org):
    contact = Contact(
        id=uuid.uuid4(),
        organization_id=sample_org.id,
        contact_type="person",
        name="Jean Dupont",
        email="jean@example.ch",
        phone="+41 21 123 45 67",
        city="Lausanne",
        canton="VD",
        is_active=True,
        source_type="manual",
        confidence="declared",
    )
    db_session.add(contact)
    await db_session.commit()

    result = await db_session.execute(select(Contact).where(Contact.id == contact.id))
    fetched = result.scalar_one()
    assert fetched.contact_type == "person"
    assert fetched.name == "Jean Dupont"
    assert fetched.source_type == "manual"
    assert fetched.confidence == "declared"


@pytest.mark.asyncio
async def test_contact_type_values(db_session, sample_org):
    for ct in ["person", "company", "authority", "notary", "insurer", "syndic", "supplier"]:
        c = Contact(
            id=uuid.uuid4(),
            organization_id=sample_org.id,
            contact_type=ct,
            name=f"Test {ct}",
        )
        db_session.add(c)
    await db_session.commit()

    result = await db_session.execute(select(Contact))
    contacts = result.scalars().all()
    assert len(contacts) == 7


# ---------------------------------------------------------------------------
# PartyRoleAssignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_party_role_assignment(db_session, sample_building):
    contact_id = uuid.uuid4()
    pra = PartyRoleAssignment(
        id=uuid.uuid4(),
        party_type="contact",
        party_id=contact_id,
        entity_type="building",
        entity_id=sample_building.id,
        role="legal_owner",
        share_pct=50.0,
        valid_from=date(2020, 1, 1),
        is_primary=True,
    )
    db_session.add(pra)
    await db_session.commit()

    result = await db_session.execute(select(PartyRoleAssignment).where(PartyRoleAssignment.id == pra.id))
    fetched = result.scalar_one()
    assert fetched.party_type == "contact"
    assert fetched.entity_type == "building"
    assert fetched.role == "legal_owner"
    assert fetched.share_pct == 50.0
    assert fetched.is_primary is True


@pytest.mark.asyncio
async def test_party_role_all_entity_types(db_session, sample_building):
    entity_types = ["building", "unit", "portfolio", "lease", "contract", "intervention", "diagnostic"]
    for et in entity_types:
        pra = PartyRoleAssignment(
            id=uuid.uuid4(),
            party_type="user",
            party_id=uuid.uuid4(),
            entity_type=et,
            entity_id=uuid.uuid4(),
            role="manager",
        )
        db_session.add(pra)
    await db_session.commit()

    result = await db_session.execute(select(PartyRoleAssignment))
    all_pra = result.scalars().all()
    assert len(all_pra) == 7


@pytest.mark.asyncio
async def test_party_role_all_roles(db_session):
    roles = [
        "legal_owner",
        "co_owner",
        "tenant",
        "manager",
        "insurer",
        "contractor",
        "notary",
        "trustee",
        "syndic",
        "architect",
        "diagnostician",
        "reviewer",
    ]
    for role in roles:
        pra = PartyRoleAssignment(
            id=uuid.uuid4(),
            party_type="contact",
            party_id=uuid.uuid4(),
            entity_type="building",
            entity_id=uuid.uuid4(),
            role=role,
        )
        db_session.add(pra)
    await db_session.commit()

    result = await db_session.execute(select(PartyRoleAssignment))
    all_pra = result.scalars().all()
    assert len(all_pra) == 12


# ---------------------------------------------------------------------------
# Portfolio + BuildingPortfolio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_portfolio(db_session, sample_org):
    portfolio = Portfolio(
        id=uuid.uuid4(),
        organization_id=sample_org.id,
        name="Immeubles VD",
        description="Portefeuille vaudois",
        portfolio_type="management",
        is_default=False,
    )
    db_session.add(portfolio)
    await db_session.commit()

    result = await db_session.execute(select(Portfolio).where(Portfolio.id == portfolio.id))
    fetched = result.scalar_one()
    assert fetched.name == "Immeubles VD"
    assert fetched.portfolio_type == "management"


@pytest.mark.asyncio
async def test_portfolio_type_values(db_session, sample_org):
    for pt in ["management", "ownership", "diagnostic", "campaign", "custom"]:
        p = Portfolio(
            id=uuid.uuid4(),
            organization_id=sample_org.id,
            name=f"Portfolio {pt}",
            portfolio_type=pt,
        )
        db_session.add(p)
    await db_session.commit()

    result = await db_session.execute(select(Portfolio))
    assert len(result.scalars().all()) == 5


@pytest.mark.asyncio
async def test_building_portfolio_junction(db_session, sample_org, sample_building):
    portfolio = Portfolio(
        id=uuid.uuid4(),
        organization_id=sample_org.id,
        name="Test Portfolio",
    )
    db_session.add(portfolio)
    await db_session.flush()

    bp = BuildingPortfolio(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        portfolio_id=portfolio.id,
    )
    db_session.add(bp)
    await db_session.commit()

    result = await db_session.execute(select(BuildingPortfolio).where(BuildingPortfolio.portfolio_id == portfolio.id))
    fetched = result.scalar_one()
    assert fetched.building_id == sample_building.id


# ---------------------------------------------------------------------------
# Unit + UnitZone
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_unit(db_session, sample_building):
    unit = Unit(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        unit_type="residential",
        reference_code="Apt 3.1",
        name="Appartement 3.1",
        floor=3,
        surface_m2=85.5,
        rooms=3.5,
        status="active",
    )
    db_session.add(unit)
    await db_session.commit()

    result = await db_session.execute(select(Unit).where(Unit.id == unit.id))
    fetched = result.scalar_one()
    assert fetched.unit_type == "residential"
    assert fetched.reference_code == "Apt 3.1"
    assert fetched.rooms == 3.5
    assert fetched.status == "active"


@pytest.mark.asyncio
async def test_unit_type_values(db_session, sample_building):
    for i, ut in enumerate(["residential", "commercial", "parking", "storage", "office", "common_area"]):
        u = Unit(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            unit_type=ut,
            reference_code=f"U-{i}",
        )
        db_session.add(u)
    await db_session.commit()

    result = await db_session.execute(select(Unit))
    assert len(result.scalars().all()) == 6


@pytest.mark.asyncio
async def test_unit_status_values(db_session, sample_building):
    for i, st in enumerate(["active", "vacant", "renovating", "decommissioned"]):
        u = Unit(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            unit_type="residential",
            reference_code=f"S-{i}",
            status=st,
        )
        db_session.add(u)
    await db_session.commit()

    result = await db_session.execute(select(Unit))
    assert len(result.scalars().all()) == 4


@pytest.mark.asyncio
async def test_unit_zone_junction(db_session, sample_building, sample_zone):
    unit = Unit(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        unit_type="residential",
        reference_code="UZ-1",
    )
    db_session.add(unit)
    await db_session.flush()

    uz = UnitZone(
        id=uuid.uuid4(),
        unit_id=unit.id,
        zone_id=sample_zone.id,
    )
    db_session.add(uz)
    await db_session.commit()

    result = await db_session.execute(select(UnitZone).where(UnitZone.unit_id == unit.id))
    fetched = result.scalar_one()
    assert fetched.zone_id == sample_zone.id


# ---------------------------------------------------------------------------
# OwnershipRecord
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_ownership_record(db_session, sample_building):
    ownership = OwnershipRecord(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        owner_type="contact",
        owner_id=uuid.uuid4(),
        share_pct=100.0,
        ownership_type="full",
        acquisition_type="purchase",
        acquisition_date=date(2015, 6, 15),
        acquisition_price_chf=850000.0,
        land_register_ref="VD-1234-5678",
        status="active",
        source_type="official",
        confidence="verified",
    )
    db_session.add(ownership)
    await db_session.commit()

    result = await db_session.execute(select(OwnershipRecord).where(OwnershipRecord.id == ownership.id))
    fetched = result.scalar_one()
    assert fetched.ownership_type == "full"
    assert fetched.acquisition_price_chf == 850000.0
    assert fetched.land_register_ref == "VD-1234-5678"
    assert fetched.source_type == "official"
    assert fetched.confidence == "verified"


@pytest.mark.asyncio
async def test_ownership_type_values(db_session, sample_building):
    for ot in ["full", "co_ownership", "usufruct", "bare_ownership", "ppe_unit"]:
        o = OwnershipRecord(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            owner_type="contact",
            owner_id=uuid.uuid4(),
            ownership_type=ot,
        )
        db_session.add(o)
    await db_session.commit()

    result = await db_session.execute(select(OwnershipRecord))
    assert len(result.scalars().all()) == 5


@pytest.mark.asyncio
async def test_ownership_status_values(db_session, sample_building):
    for st in ["active", "transferred", "disputed", "archived"]:
        o = OwnershipRecord(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            owner_type="user",
            owner_id=uuid.uuid4(),
            ownership_type="full",
            status=st,
        )
        db_session.add(o)
    await db_session.commit()

    result = await db_session.execute(select(OwnershipRecord))
    assert len(result.scalars().all()) == 4


# ---------------------------------------------------------------------------
# Existing model modifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_building_has_organization_id(db_session, sample_building):
    """Building.organization_id exists and is nullable."""
    assert hasattr(sample_building, "organization_id")
    assert sample_building.organization_id is None  # nullable, not set


@pytest.mark.asyncio
async def test_organization_has_contact_person_id(db_session, sample_org):
    """Organization.contact_person_id exists and is nullable."""
    assert hasattr(sample_org, "contact_person_id")
    assert sample_org.contact_person_id is None


@pytest.mark.asyncio
async def test_user_has_linked_contact_id(db_session, sample_user):
    """User.linked_contact_id exists and is nullable."""
    assert hasattr(sample_user, "linked_contact_id")
    assert sample_user.linked_contact_id is None


# ---------------------------------------------------------------------------
# Bidirectional relationship regression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_building_units_bidirectional(db_session, sample_building):
    """Building.units ↔ Unit.building back_populates works both ways."""
    unit = Unit(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        unit_type="residential",
        reference_code="BiDir-1",
    )
    db_session.add(unit)
    await db_session.flush()

    # Forward: building → units
    await db_session.refresh(sample_building, ["units"])
    assert len(sample_building.units) == 1
    assert sample_building.units[0].id == unit.id

    # Reverse: unit → building
    await db_session.refresh(unit, ["building"])
    assert unit.building.id == sample_building.id


@pytest.mark.asyncio
async def test_building_ownership_bidirectional(db_session, sample_building):
    """Building.ownership_records ↔ OwnershipRecord.building back_populates works both ways."""
    ownership = OwnershipRecord(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        owner_type="contact",
        owner_id=uuid.uuid4(),
        ownership_type="full",
    )
    db_session.add(ownership)
    await db_session.flush()

    # Forward: building → ownership_records
    await db_session.refresh(sample_building, ["ownership_records"])
    assert len(sample_building.ownership_records) == 1
    assert sample_building.ownership_records[0].id == ownership.id

    # Reverse: ownership → building
    await db_session.refresh(ownership, ["building"])
    assert ownership.building.id == sample_building.id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sample_org(db_session):
    from app.models.organization import Organization

    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def sample_user(db_session, sample_org):
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfakeh",
        first_name="Test",
        last_name="User",
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
        address="Rue de Test 1",
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
        name="1er etage",
    )
    db_session.add(zone)
    await db_session.flush()
    return zone


@pytest.fixture
async def db_session():
    """Standalone async SQLite session for backbone tests."""
    from geoalchemy2 import Geometry
    from sqlalchemy import MetaData, String, event
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    # Force import of all backbone models so tables are registered
    import app.models.building
    import app.models.building_portfolio
    import app.models.contact
    import app.models.organization
    import app.models.ownership_record
    import app.models.party_role_assignment
    import app.models.portfolio
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

    # Build SQLite-safe metadata
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

    async with test_engine.begin() as conn:
        await conn.run_sync(meta.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(meta.drop_all)
    await test_engine.dispose()
