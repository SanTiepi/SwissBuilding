import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["S3_ENDPOINT"] = "http://localhost:9000"
os.environ["S3_ACCESS_KEY"] = "test"
os.environ["S3_SECRET_KEY"] = "test"
os.environ["S3_BUCKET"] = "test"
os.environ["CLAMAV_ENABLED"] = "false"
os.environ["OCRMYPDF_ENABLED"] = "false"
os.environ["MEILISEARCH_ENABLED"] = "false"

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import MetaData, String, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app

# Disable rate limiting in tests
limiter.enabled = False
from datetime import UTC, datetime, timedelta  # noqa: E402

from jose import jwt  # noqa: E402
from passlib.context import CryptContext  # noqa: E402

from app.models.building import Building  # noqa: E402
from app.models.building_portfolio import BuildingPortfolio as _BP  # noqa: E402, F401

# BC2 property management models
from app.models.claim import Claim as _Claim  # noqa: E402, F401

# BC1 backbone models — must be imported before _build_sqlite_metadata()
# so their tables are registered in Base.metadata.
# Use from-imports to avoid shadowing the FastAPI `app` instance.
from app.models.contact import Contact as _Contact  # noqa: E402, F401
from app.models.contract import Contract as _Contract2  # noqa: E402, F401
from app.models.document_link import DocumentLink as _DL  # noqa: E402, F401
from app.models.financial_entry import FinancialEntry as _FE  # noqa: E402, F401
from app.models.insurance_policy import InsurancePolicy as _IP  # noqa: E402, F401
from app.models.inventory_item import InventoryItem as _II  # noqa: E402, F401
from app.models.lease import Lease as _Lease  # noqa: E402, F401
from app.models.ownership_record import OwnershipRecord as _OR  # noqa: E402, F401
from app.models.party_role_assignment import PartyRoleAssignment as _PRA  # noqa: E402, F401
from app.models.portfolio import Portfolio as _Portfolio  # noqa: E402, F401
from app.models.tax_context import TaxContext as _TC  # noqa: E402, F401
from app.models.unit import Unit as _Unit  # noqa: E402, F401
from app.models.document_inbox import DocumentInboxItem as _DII  # noqa: E402, F401
from app.models.unit_zone import UnitZone as _UZ  # noqa: E402, F401
from app.models.obligation import Obligation as _Obligation  # noqa: E402, F401
from app.models.intake_request import IntakeRequest as _IR  # noqa: E402, F401
from app.models.user import User  # noqa: E402
from app.models.workspace_membership import WorkspaceMembership as _WM  # noqa: E402, F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pre-hash passwords once at import time (~175ms each instead of per-test)
_HASH_ADMIN = pwd_context.hash("admin123")
_HASH_DIAG = pwd_context.hash("diag123")
_HASH_OWNER = pwd_context.hash("owner123")


def _build_sqlite_metadata():
    """Build a SQLite-safe copy of Base.metadata, replacing Geometry with String
    and skipping PostgreSQL-specific indexes (GiST)."""
    from geoalchemy2 import Geometry

    meta = MetaData()
    for table in Base.metadata.sorted_tables:
        new_table = table.to_metadata(meta)
        for col in new_table.columns:
            if isinstance(table.columns[col.name].type, Geometry):
                col.type = String()
                col.nullable = True
        # Skip postgresql_using='gist' indexes
        for idx in tuple(new_table.indexes):
            if "postgresql_using" in idx.dialect_kwargs:
                new_table.indexes.discard(idx)
    return meta


# Build once at import time
_sqlite_meta = _build_sqlite_metadata()


@pytest.fixture(scope="session")
async def _engine():
    """Session-scoped engine — schema created once for all tests."""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Register SQLite stubs for PostGIS functions
    @event.listens_for(engine.sync_engine, "connect")
    def register_functions(dbapi_conn, _):
        def noop(*args):
            return None

        def identity(x):
            return x

        dbapi_conn.create_function("ST_AsText", 1, lambda x: str(x) if x else None)
        dbapi_conn.create_function("ST_GeomFromText", 2, lambda wkt, srid: wkt)
        dbapi_conn.create_function("ST_AsGeoJSON", 1, lambda x: '{"type":"Point","coordinates":[0,0]}')
        dbapi_conn.create_function("GeomFromEWKT", 1, identity)
        dbapi_conn.create_function("AsEWKB", 1, identity)
        dbapi_conn.create_function("ST_GeomFromEWKT", 1, identity)
        dbapi_conn.create_function("RecoverGeometryColumn", -1, noop)
        dbapi_conn.create_function("CheckSpatialMetaData", 0, lambda: 1)
        dbapi_conn.create_function("AddGeometryColumn", -1, noop)
        dbapi_conn.create_function("DiscardGeometryColumn", -1, noop)

    async with engine.begin() as conn:
        await conn.run_sync(_sqlite_meta.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_engine(_engine):
    """Function-scoped alias that cleans data between tests via DELETE."""
    yield _engine
    # Clean all tables after each test (faster than drop/create)
    async with _engine.begin() as conn:
        for table in reversed(_sqlite_meta.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture(scope="function")
async def db_session(test_engine):
    TestSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_engine):
    TestSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="admin@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Admin",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def diagnostician_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="diag@test.ch",
        password_hash=_HASH_DIAG,
        first_name="Jean",
        last_name="Test",
        role="diagnostician",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def owner_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="owner@test.ch",
        password_hash=_HASH_OWNER,
        first_name="Sophie",
        last_name="Test",
        role="owner",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(admin_user):
    payload = {
        "sub": str(admin_user.id),
        "email": admin_user.email,
        "role": admin_user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def diag_headers(diagnostician_user):
    payload = {
        "sub": str(diagnostician_user.id),
        "email": diagnostician_user.email,
        "role": diagnostician_user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner_headers(owner_user):
    payload = {
        "sub": str(owner_user.id),
        "email": owner_user.email,
        "role": owner_user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_building(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building
