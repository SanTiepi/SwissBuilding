"""Tests for the Data Provenance Tracker service and API."""

import uuid
from datetime import date

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.data_provenance_service import (
    get_building_data_lineage,
    get_data_provenance,
    get_provenance_statistics,
    verify_data_integrity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="TestOrg",
        type="diagnostic_lab",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def user_with_org(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
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
async def building(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def imported_building(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Import 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1980,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
        source_dataset="vd-public-rcb",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def diagnostic(db_session, building, admin_user):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def sample(db_session, diagnostic):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        location_floor="1er",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def document(db_session, building, admin_user):
    d = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/test.pdf",
        file_name="test.pdf",
        uploaded_by=admin_user.id,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def action(db_session, building, diagnostic, admin_user):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_id=diagnostic.id,
        source_type="diagnostic",
        action_type="removal",
        title="Remove asbestos",
        priority="high",
        status="open",
        created_by=admin_user.id,
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


# ---------------------------------------------------------------------------
# get_data_provenance tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provenance_building(db_session, building, admin_user):
    record = await get_data_provenance(db_session, "building", building.id)
    assert record is not None
    assert record.entity_type == "building"
    assert record.entity_id == building.id
    assert record.source == "manual"
    assert record.created_by == admin_user.id
    assert record.created_by_email == admin_user.email


@pytest.mark.asyncio
async def test_provenance_imported_building(db_session, imported_building):
    record = await get_data_provenance(db_session, "building", imported_building.id)
    assert record is not None
    assert record.source == "import"
    assert record.source_dataset == "vd-public-rcb"
    assert "imported_from:vd-public-rcb" in record.transformations


@pytest.mark.asyncio
async def test_provenance_diagnostic(db_session, diagnostic, building, admin_user):
    record = await get_data_provenance(db_session, "diagnostic", diagnostic.id)
    assert record is not None
    assert record.entity_type == "diagnostic"
    assert record.parent_entity_type == "building"
    assert record.parent_entity_id == building.id
    assert record.created_by == admin_user.id


@pytest.mark.asyncio
async def test_provenance_sample(db_session, sample, diagnostic):
    record = await get_data_provenance(db_session, "sample", sample.id)
    assert record is not None
    assert record.entity_type == "sample"
    assert record.parent_entity_type == "diagnostic"
    assert record.parent_entity_id == diagnostic.id


@pytest.mark.asyncio
async def test_provenance_document(db_session, document, building, admin_user):
    record = await get_data_provenance(db_session, "document", document.id)
    assert record is not None
    assert record.entity_type == "document"
    assert record.parent_entity_type == "building"
    assert record.parent_entity_id == building.id
    assert record.created_by == admin_user.id


@pytest.mark.asyncio
async def test_provenance_action(db_session, action, building, admin_user):
    record = await get_data_provenance(db_session, "action", action.id)
    assert record is not None
    assert record.entity_type == "action"
    assert record.parent_entity_type == "building"
    assert record.parent_entity_id == building.id


@pytest.mark.asyncio
async def test_provenance_not_found(db_session):
    record = await get_data_provenance(db_session, "building", uuid.uuid4())
    assert record is None


@pytest.mark.asyncio
async def test_provenance_invalid_type(db_session):
    record = await get_data_provenance(db_session, "invalid_type", uuid.uuid4())
    assert record is None


# ---------------------------------------------------------------------------
# get_building_data_lineage tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lineage_empty_building(db_session, building):
    tree = await get_building_data_lineage(db_session, building.id)
    assert tree is not None
    assert tree.building_id == building.id
    assert tree.root.entity_type == "building"
    assert tree.total_nodes == 1
    assert tree.entity_counts["building"] == 1


@pytest.mark.asyncio
async def test_lineage_with_children(db_session, building, diagnostic, sample, document, action):
    tree = await get_building_data_lineage(db_session, building.id)
    assert tree is not None
    assert tree.total_nodes == 5  # building + diagnostic + sample + document + action
    assert tree.entity_counts["diagnostic"] == 1
    assert tree.entity_counts["sample"] == 1
    assert tree.entity_counts["document"] == 1
    assert tree.entity_counts["action"] == 1

    # Check that diagnostic has sample as child
    diag_nodes = [c for c in tree.root.children if c.entity_type == "diagnostic"]
    assert len(diag_nodes) == 1
    assert len(diag_nodes[0].children) == 1
    assert diag_nodes[0].children[0].entity_type == "sample"


@pytest.mark.asyncio
async def test_lineage_not_found(db_session):
    tree = await get_building_data_lineage(db_session, uuid.uuid4())
    assert tree is None


# ---------------------------------------------------------------------------
# verify_data_integrity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integrity_clean_building(db_session, building, diagnostic, sample):
    report = await verify_data_integrity(db_session, building.id)
    assert report is not None
    assert report.building_id == building.id
    assert report.is_clean


@pytest.mark.asyncio
async def test_integrity_completed_diag_no_samples(db_session, building, admin_user):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="pcb",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(d)
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    assert not report.is_clean
    missing_samples = [i for i in report.issues if i.issue_type == "missing_samples"]
    assert len(missing_samples) == 1


@pytest.mark.asyncio
async def test_integrity_diag_no_diagnostician(db_session, building):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="lead",
        status="draft",
    )
    db_session.add(d)
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    missing_src = [i for i in report.issues if i.issue_type == "missing_source" and i.entity_type == "diagnostic"]
    assert len(missing_src) == 1


@pytest.mark.asyncio
async def test_integrity_date_inconsistency(db_session, building, admin_user):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="draft",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 6, 15),
        date_report=date(2024, 6, 10),
    )
    db_session.add(d)
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    date_issues = [i for i in report.issues if i.issue_type == "date_inconsistency"]
    assert len(date_issues) == 1


@pytest.mark.asyncio
async def test_integrity_doc_no_uploader(db_session, building):
    d = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/orphan.pdf",
        file_name="orphan.pdf",
        uploaded_by=None,
    )
    db_session.add(d)
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    doc_issues = [i for i in report.issues if i.entity_type == "document"]
    assert len(doc_issues) == 1


@pytest.mark.asyncio
async def test_integrity_action_orphan_diagnostic(db_session, building, admin_user):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_id=uuid.uuid4(),  # non-existent
        source_type="diagnostic",
        action_type="removal",
        title="Orphan action",
        priority="medium",
        status="open",
        created_by=admin_user.id,
    )
    db_session.add(a)
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    orphans = [i for i in report.issues if i.issue_type == "orphan"]
    assert len(orphans) == 1


@pytest.mark.asyncio
async def test_integrity_action_no_creator(db_session, building):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="manual",
        action_type="inspection",
        title="No creator action",
        priority="low",
        status="open",
        created_by=None,
    )
    db_session.add(a)
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    creator_issues = [i for i in report.issues if i.issue_type == "missing_creator" and i.entity_type == "action"]
    assert len(creator_issues) == 1


@pytest.mark.asyncio
async def test_integrity_not_found(db_session):
    report = await verify_data_integrity(db_session, uuid.uuid4())
    assert report is None


@pytest.mark.asyncio
async def test_integrity_severity_counts(db_session, building, admin_user):
    # Create a completed diag with no samples (error) + no-uploader doc (info)
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="hap",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/x.pdf",
        file_name="x.pdf",
        uploaded_by=None,
    )
    db_session.add_all([d, doc])
    await db_session.commit()
    report = await verify_data_integrity(db_session, building.id)
    assert report.total_issues >= 2
    assert "error" in report.issues_by_severity
    assert "info" in report.issues_by_severity


# ---------------------------------------------------------------------------
# get_provenance_statistics tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_statistics_no_data(db_session):
    stats = await get_provenance_statistics(db_session)
    assert stats.total_buildings == 0
    assert stats.import_percentage == 0.0
    assert stats.manual_percentage == 0.0


@pytest.mark.asyncio
async def test_statistics_with_data(db_session, building, imported_building, diagnostic, sample, document, action):
    stats = await get_provenance_statistics(db_session)
    assert stats.total_buildings == 2
    assert stats.total_diagnostics >= 1
    assert stats.total_samples >= 1
    assert stats.total_documents >= 1
    assert stats.total_actions >= 1
    assert stats.import_percentage == 50.0
    assert stats.manual_percentage == 50.0
    assert stats.source_breakdown["import"] == 1
    assert stats.source_breakdown["manual"] == 1
    assert stats.traceability_coverage == 100.0


@pytest.mark.asyncio
async def test_statistics_org_filter(db_session, user_with_org, org):
    # Building created by org user
    b = Building(
        id=uuid.uuid4(),
        address="Org building",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=user_with_org.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    stats = await get_provenance_statistics(db_session, org_id=org.id)
    assert stats.total_buildings == 1
    assert stats.organization_id == org.id


@pytest.mark.asyncio
async def test_statistics_org_no_buildings(db_session, org):
    stats = await get_provenance_statistics(db_session, org_id=org.id)
    assert stats.total_buildings == 0
    assert stats.data_quality_score == 0.0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_provenance_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/provenance/building/{sample_building.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_type"] == "building"


@pytest.mark.asyncio
async def test_api_provenance_invalid_type(client, auth_headers):
    resp = await client.get(
        f"/api/v1/provenance/invalid/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_provenance_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/provenance/building/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_lineage_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/lineage",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["root"]["entity_type"] == "building"


@pytest.mark.asyncio
async def test_api_integrity_endpoint(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/integrity",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "issues" in data
    assert "is_clean" in data


@pytest.mark.asyncio
async def test_api_statistics_endpoint(client, auth_headers):
    resp = await client.get(
        "/api/v1/provenance/statistics",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "data_quality_score" in data


@pytest.mark.asyncio
async def test_api_statistics_with_org(client, auth_headers):
    resp = await client.get(
        f"/api/v1/provenance/statistics?org_id={uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sample_no_pollutant_type(db_session, building, admin_user):
    """Sample without pollutant_type should trigger missing_source issue."""
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="draft",
        diagnostician_id=admin_user.id,
    )
    db_session.add(d)
    await db_session.commit()

    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=d.id,
        sample_number="S-NO-POLL",
        pollutant_type=None,
    )
    db_session.add(s)
    await db_session.commit()

    report = await verify_data_integrity(db_session, building.id)
    sample_issues = [i for i in report.issues if i.entity_type == "sample"]
    assert len(sample_issues) == 1
    assert sample_issues[0].issue_type == "missing_source"
