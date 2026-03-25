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

# Artifact Custody models
from app.models.artifact_version import ArtifactVersion as _AV  # noqa: E402, F401

# Finance Surfaces models
from app.models.audience_pack import AudiencePack as _AP  # noqa: E402, F401
from app.models.authority_request import AuthorityRequest as _AR  # noqa: E402, F401
from app.models.bounded_embed import BoundedEmbedToken as _BET  # noqa: E402, F401
from app.models.bounded_embed import ExternalViewerProfile as _EVP  # noqa: E402, F401
from app.models.building import Building  # noqa: E402
from app.models.building_portfolio import BuildingPortfolio as _BP  # noqa: E402, F401
from app.models.case_study_template import CaseStudyTemplate as _CST  # noqa: E402, F401

# BC2 property management models
from app.models.claim import Claim as _Claim  # noqa: E402, F401

# Public Sector models
from app.models.committee_decision import CommitteeDecisionPack as _CDP  # noqa: E402, F401
from app.models.committee_decision import ReviewDecisionTrace as _RDT  # noqa: E402, F401
from app.models.communal_adapter import CommunalAdapterProfile as _CAP  # noqa: E402, F401
from app.models.communal_override import CommunalRuleOverride as _CRO  # noqa: E402, F401

# BC1 backbone models — must be imported before _build_sqlite_metadata()
# so their tables are registered in Base.metadata.
# Use from-imports to avoid shadowing the FastAPI `app` instance.
from app.models.contact import Contact as _Contact  # noqa: E402, F401
from app.models.contract import Contract as _Contract2  # noqa: E402, F401
from app.models.custody_event import CustodyEvent as _CE  # noqa: E402, F401
from app.models.customer_success import CustomerSuccessMilestone as _CSM  # noqa: E402, F401
from app.models.delegated_access import DelegatedAccessGrant as _DAG  # noqa: E402, F401
from app.models.delegated_access import PrivilegedAccessEvent as _PAE  # noqa: E402, F401
from app.models.delegated_access import TenantBoundary as _TB  # noqa: E402, F401
from app.models.demo_scenario import DemoScenario as _DS  # noqa: E402, F401
from app.models.document_inbox import DocumentInboxItem as _DII  # noqa: E402, F401
from app.models.document_link import DocumentLink as _DL  # noqa: E402, F401
from app.models.exchange_contract import ExchangeContractVersion as _ECV  # noqa: E402, F401
from app.models.expansion_signal import AccountExpansionTrigger as _AET  # noqa: E402, F401
from app.models.expansion_signal import DistributionLoopSignal as _DLS  # noqa: E402, F401
from app.models.expansion_signal import ExpansionOpportunity as _EO  # noqa: E402, F401
from app.models.financial_entry import FinancialEntry as _FE  # noqa: E402, F401
from app.models.governance_signal import PublicAssetGovernanceSignal as _PAGS  # noqa: E402, F401
from app.models.import_receipt import PassportImportReceipt as _PIR  # noqa: E402, F401
from app.models.insurance_policy import InsurancePolicy as _IP  # noqa: E402, F401
from app.models.intake_request import IntakeRequest as _IR  # noqa: E402, F401
from app.models.inventory_item import InventoryItem as _II  # noqa: E402, F401
from app.models.lease import Lease as _Lease  # noqa: E402, F401
from app.models.municipality_review_pack import MunicipalityReviewPack as _MRP  # noqa: E402, F401
from app.models.obligation import Obligation as _Obligation  # noqa: E402, F401
from app.models.ownership_record import OwnershipRecord as _OR  # noqa: E402, F401
from app.models.package_preset import PackagePreset as _PPr  # noqa: E402, F401
from app.models.partner_trust import PartnerTrustProfile as _PTP  # noqa: E402, F401
from app.models.partner_trust import PartnerTrustSignal as _PTS  # noqa: E402, F401
from app.models.party_role_assignment import PartyRoleAssignment as _PRA  # noqa: E402, F401
from app.models.passport_publication import PassportPublication as _PPub  # noqa: E402, F401
from app.models.permit_procedure import PermitProcedure as _PP  # noqa: E402, F401
from app.models.permit_step import PermitStep as _PS  # noqa: E402, F401
from app.models.pilot_scorecard import PilotScorecard as _PSc  # noqa: E402, F401
from app.models.portfolio import Portfolio as _Portfolio  # noqa: E402, F401
from app.models.proof_delivery import ProofDelivery as _PD  # noqa: E402, F401
from app.models.public_owner_mode import PublicOwnerOperatingMode as _POOM  # noqa: E402, F401
from app.models.redaction_profile import DecisionCaveatProfile as _DCP  # noqa: E402, F401
from app.models.redaction_profile import ExternalAudienceRedactionProfile as _EARP  # noqa: E402, F401
from app.models.rule_change_event import RuleChangeEvent as _RCE  # noqa: E402, F401
from app.models.swiss_rules_source import RuleSource as _RS  # noqa: E402, F401
from app.models.tax_context import TaxContext as _TC  # noqa: E402, F401
from app.models.unit import Unit as _Unit  # noqa: E402, F401
from app.models.unit_zone import UnitZone as _UZ  # noqa: E402, F401
from app.models.user import User  # noqa: E402
from app.models.workspace_membership import WorkspaceMembership as _WM  # noqa: E402, F401

# Marketplace models
from app.models.company_profile import CompanyProfile as _CP  # noqa: E402, F401
from app.models.company_subscription import CompanySubscription as _CS  # noqa: E402, F401
from app.models.company_verification import CompanyVerification as _CV  # noqa: E402, F401

# Marketplace RFQ models
from app.models.client_request import ClientRequest as _CR  # noqa: E402, F401
from app.models.quote import Quote as _Q  # noqa: E402, F401
from app.models.request_document import RequestDocument as _RD  # noqa: E402, F401
from app.models.request_invitation import RequestInvitation as _RI  # noqa: E402, F401

# Marketplace Trust models
from app.models.award_confirmation import AwardConfirmation as _AC  # noqa: E402, F401
from app.models.completion_confirmation import CompletionConfirmation as _CC  # noqa: E402, F401
from app.models.review import Review as _Rev  # noqa: E402, F401

# Lot 4: Post-Works Truth models
from app.models.ai_feedback import AIFeedback as _AFB  # noqa: E402, F401
from app.models.domain_event import DomainEvent as _DE  # noqa: E402, F401
from app.models.post_works_link import PostWorksLink as _PWL  # noqa: E402, F401

# Growth Stack models
from app.models.ai_extraction_log import AIExtractionLog as _AEL  # noqa: E402, F401
from app.models.subscription_change import SubscriptionChange as _SC  # noqa: E402, F401

# Intelligence Stack models
from app.models.ai_rule_pattern import AIRulePattern as _ARP  # noqa: E402, F401

# Exchange Hardening + Contributor Gateway models
from app.models.contributor_gateway import ContributorGatewayRequest as _CGR  # noqa: E402, F401
from app.models.contributor_gateway import ContributorReceipt as _CRcpt  # noqa: E402, F401
from app.models.contributor_gateway import ContributorSubmission as _CSub  # noqa: E402, F401
from app.models.exchange_validation import ExchangeValidationReport as _EVR  # noqa: E402, F401
from app.models.exchange_validation import ExternalRelianceSignal as _ERS  # noqa: E402, F401
from app.models.partner_webhook import PartnerDeliveryAttempt as _PDA  # noqa: E402, F401
from app.models.partner_webhook import PartnerWebhookSubscription as _PWS  # noqa: E402, F401
from app.models.passport_state_diff import PassportStateDiff as _PSD  # noqa: E402, F401

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
