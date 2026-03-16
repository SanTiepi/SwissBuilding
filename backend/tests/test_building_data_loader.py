"""Tests for building_data_loader shared module."""

import uuid

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.building_data_loader import load_building_with_context, load_org_buildings
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(id=uuid.uuid4(), name="Loader Org", type="diagnostic_lab")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org2(db_session):
    o = Organization(id=uuid.uuid4(), name="Other Org", type="property_management")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    u = User(
        id=uuid.uuid4(),
        email="loader-user@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Loader",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def org2_user(db_session, org2):
    u = User(
        id=uuid.uuid4(),
        email="other-user@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Other",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org2.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def building_a(db_session, org_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Loader 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_b(db_session, org_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Loader 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1985,
        building_type="commercial",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_other_org(db_session, org2_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Other 1",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2000,
        building_type="residential",
        created_by=org2_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


# ---------------------------------------------------------------------------
# load_org_buildings tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_org_buildings_empty_org(db_session, org):
    """Org with no users returns empty list."""
    result = await load_org_buildings(db_session, org.id)
    assert result == []


@pytest.mark.asyncio
async def test_load_org_buildings_no_buildings(db_session, org_user):
    """Org with a user but no buildings returns empty list."""
    result = await load_org_buildings(db_session, org_user.organization_id)
    assert result == []


@pytest.mark.asyncio
async def test_load_org_buildings_with_buildings(db_session, org, org_user, building_a, building_b):
    """Returns all buildings created by org members."""
    result = await load_org_buildings(db_session, org.id)
    assert len(result) == 2
    ids = {b.id for b in result}
    assert building_a.id in ids
    assert building_b.id in ids


@pytest.mark.asyncio
async def test_load_org_buildings_filters_by_org(db_session, org, org_user, building_a, building_other_org):
    """Buildings from other orgs are not returned."""
    result = await load_org_buildings(db_session, org.id)
    assert len(result) == 1
    assert result[0].id == building_a.id


@pytest.mark.asyncio
async def test_load_org_buildings_nonexistent_org(db_session):
    """Non-existent org returns empty list."""
    result = await load_org_buildings(db_session, uuid.uuid4())
    assert result == []


# ---------------------------------------------------------------------------
# load_building_with_context tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_building_with_context_not_found(db_session):
    """Returns None when building does not exist."""
    result = await load_building_with_context(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_load_building_with_context_basic(db_session, building_a):
    """Basic load returns building only."""
    result = await load_building_with_context(db_session, building_a.id)
    assert result is not None
    assert result["building"].id == building_a.id
    # No optional keys should be present
    assert "diagnostics" not in result
    assert "samples" not in result
    assert "documents" not in result
    assert "zones" not in result
    assert "interventions" not in result
    assert "actions" not in result


@pytest.mark.asyncio
async def test_load_building_with_context_with_diagnostics(db_session, building_a):
    """Include diagnostics returns them in the result."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_a.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=building_a.created_by,
    )
    db_session.add(diag)
    await db_session.commit()

    result = await load_building_with_context(db_session, building_a.id, include_diagnostics=True)
    assert "diagnostics" in result
    assert len(result["diagnostics"]) == 1
    assert result["diagnostics"][0].id == diag.id


@pytest.mark.asyncio
async def test_load_building_with_context_with_samples(db_session, building_a):
    """Include samples fetches samples via diagnostics."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_a.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=building_a.created_by,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        risk_level="high",
        threshold_exceeded=True,
    )
    db_session.add(sample)
    await db_session.commit()

    result = await load_building_with_context(db_session, building_a.id, include_samples=True)
    assert "samples" in result
    assert len(result["samples"]) == 1
    assert result["samples"][0].id == sample.id


@pytest.mark.asyncio
async def test_load_building_with_context_with_documents(db_session, building_a):
    """Include documents returns them."""
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_a.id,
        file_path="/test/doc.pdf",
        file_name="doc.pdf",
        document_type="report",
    )
    db_session.add(doc)
    await db_session.commit()

    result = await load_building_with_context(db_session, building_a.id, include_documents=True)
    assert "documents" in result
    assert len(result["documents"]) == 1
    assert result["documents"][0].id == doc.id


@pytest.mark.asyncio
async def test_load_building_with_context_with_zones(db_session, building_a):
    """Include zones returns them."""
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building_a.id,
        name="Basement",
        zone_type="basement",
    )
    db_session.add(zone)
    await db_session.commit()

    result = await load_building_with_context(db_session, building_a.id, include_zones=True)
    assert "zones" in result
    assert len(result["zones"]) == 1
    assert result["zones"][0].id == zone.id


@pytest.mark.asyncio
async def test_load_building_with_context_all_includes(db_session, building_a):
    """All includes populated simultaneously."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_a.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=building_a.created_by,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        pollutant_type="asbestos",
    )
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_a.id,
        file_path="/test/all.pdf",
        file_name="all.pdf",
    )
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building_a.id,
        name="Floor 1",
        zone_type="floor",
    )
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_a.id,
        intervention_type="removal",
        title="Asbestos removal",
        status="planned",
        description="Remove asbestos",
    )
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building_a.id,
        title="Test action",
        source_type="diagnostic",
        action_type="remediation",
        priority="high",
        status="open",
    )
    db_session.add_all([sample, doc, zone, intervention, action])
    await db_session.commit()

    result = await load_building_with_context(
        db_session,
        building_a.id,
        include_diagnostics=True,
        include_samples=True,
        include_documents=True,
        include_zones=True,
        include_interventions=True,
        include_actions=True,
    )

    assert result["building"].id == building_a.id
    assert len(result["diagnostics"]) == 1
    assert len(result["samples"]) == 1
    assert len(result["documents"]) == 1
    assert len(result["zones"]) == 1
    assert len(result["interventions"]) == 1
    assert len(result["actions"]) == 1


@pytest.mark.asyncio
async def test_load_building_with_context_selective_includes(db_session, building_a):
    """Only requested includes appear in the result dict."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_a.id,
        diagnostic_type="pcb",
        status="draft",
        diagnostician_id=building_a.created_by,
    )
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_a.id,
        file_path="/test/selective.pdf",
        file_name="selective.pdf",
    )
    db_session.add_all([diag, doc])
    await db_session.commit()

    result = await load_building_with_context(
        db_session,
        building_a.id,
        include_diagnostics=True,
        include_documents=True,
    )

    assert "diagnostics" in result
    assert "documents" in result
    assert "samples" not in result
    assert "zones" not in result
    assert "interventions" not in result
    assert "actions" not in result
