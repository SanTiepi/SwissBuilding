"""Tests for document completeness assessment service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from app.services.document_completeness_service import (
    REQUIRED_DOCUMENT_TYPES,
    assess_document_completeness,
    get_missing_documents,
    get_portfolio_document_status,
    validate_document_currency,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Régie SA",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    user = User(
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
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def org_building(db_session, org_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Org 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


def _make_document(building_id, doc_type, filename="test.pdf", created_at=None):
    return Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path=f"/files/{filename}",
        file_name=filename,
        document_type=doc_type,
        created_at=created_at or datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Service Tests: assess_document_completeness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_completeness_no_documents(db_session, sample_building):
    """Building with no documents should score 0."""
    result = await assess_document_completeness(db_session, sample_building.id)
    assert result.score == 0.0
    assert result.present == 0
    assert result.missing == len(REQUIRED_DOCUMENT_TYPES)
    assert result.total_required == len(REQUIRED_DOCUMENT_TYPES)
    assert all(t.status == "missing" for t in result.types)


@pytest.mark.asyncio
async def test_completeness_all_present(db_session, sample_building):
    """Building with all required docs should score 100."""
    for doc_type in REQUIRED_DOCUMENT_TYPES:
        db_session.add(_make_document(sample_building.id, doc_type))
    await db_session.commit()

    result = await assess_document_completeness(db_session, sample_building.id)
    assert result.score == 100.0
    assert result.present == len(REQUIRED_DOCUMENT_TYPES)
    assert result.missing == 0


@pytest.mark.asyncio
async def test_completeness_partial(db_session, sample_building):
    """Building with some docs should have proportional score."""
    db_session.add(_make_document(sample_building.id, "diagnostic_report"))
    db_session.add(_make_document(sample_building.id, "lab_certificates"))
    await db_session.commit()

    result = await assess_document_completeness(db_session, sample_building.id)
    expected_score = (2 / len(REQUIRED_DOCUMENT_TYPES)) * 100.0
    assert result.score == round(expected_score, 1)
    assert result.present == 2
    assert result.missing == len(REQUIRED_DOCUMENT_TYPES) - 2


@pytest.mark.asyncio
async def test_completeness_outdated_diagnostic(db_session, sample_building):
    """A diagnostic report older than 5 years should be flagged as outdated."""
    old_date = datetime.now(UTC) - timedelta(days=6 * 365)
    db_session.add(_make_document(sample_building.id, "diagnostic_report", created_at=old_date))
    await db_session.commit()

    result = await assess_document_completeness(db_session, sample_building.id)
    diag_type = next(t for t in result.types if t.document_type == "diagnostic_report")
    assert diag_type.status == "outdated"
    assert result.outdated == 1
    # Outdated docs don't count as present
    assert result.present == 0


@pytest.mark.asyncio
async def test_completeness_type_aliases(db_session, sample_building):
    """Document type aliases should map to canonical types."""
    db_session.add(_make_document(sample_building.id, "lab_result"))
    db_session.add(_make_document(sample_building.id, "photo"))
    db_session.add(_make_document(sample_building.id, "compliance_certificate"))
    await db_session.commit()

    result = await assess_document_completeness(db_session, sample_building.id)
    present_types = {t.document_type for t in result.types if t.status == "present"}
    assert "lab_certificates" in present_types
    assert "photo_documentation" in present_types
    assert "compliance_declarations" in present_types


@pytest.mark.asyncio
async def test_completeness_unrecognized_type_ignored(db_session, sample_building):
    """Documents with unrecognized types should not affect required type counts."""
    db_session.add(_make_document(sample_building.id, "random_document"))
    await db_session.commit()

    result = await assess_document_completeness(db_session, sample_building.id)
    assert result.score == 0.0
    assert result.missing == len(REQUIRED_DOCUMENT_TYPES)


# ---------------------------------------------------------------------------
# Service Tests: get_missing_documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_documents_all_missing(db_session, sample_building):
    """When no docs present, all required types should appear as missing."""
    missing = await get_missing_documents(db_session, sample_building.id)
    assert len(missing) == len(REQUIRED_DOCUMENT_TYPES)
    types = {m.document_type for m in missing}
    assert types == set(REQUIRED_DOCUMENT_TYPES)


@pytest.mark.asyncio
async def test_missing_documents_sorted_by_urgency(db_session, sample_building):
    """Missing documents should be sorted by urgency (critical first)."""
    missing = await get_missing_documents(db_session, sample_building.id)
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    urgency_values = [urgency_order[m.urgency] for m in missing]
    assert urgency_values == sorted(urgency_values)


@pytest.mark.asyncio
async def test_missing_documents_none_missing(db_session, sample_building):
    """When all docs present, missing list should be empty."""
    for doc_type in REQUIRED_DOCUMENT_TYPES:
        db_session.add(_make_document(sample_building.id, doc_type))
    await db_session.commit()

    missing = await get_missing_documents(db_session, sample_building.id)
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_missing_documents_includes_outdated(db_session, sample_building):
    """Outdated documents should appear in missing list."""
    old_date = datetime.now(UTC) - timedelta(days=6 * 365)
    db_session.add(_make_document(sample_building.id, "diagnostic_report", created_at=old_date))
    await db_session.commit()

    missing = await get_missing_documents(db_session, sample_building.id)
    types = {m.document_type for m in missing}
    assert "diagnostic_report" in types


@pytest.mark.asyncio
async def test_missing_documents_has_provider_and_reason(db_session, sample_building):
    """Each missing document should have provider and reason fields."""
    missing = await get_missing_documents(db_session, sample_building.id)
    for m in missing:
        assert len(m.provider) > 0
        assert len(m.reason) > 0


# ---------------------------------------------------------------------------
# Service Tests: validate_document_currency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_currency_no_documents(db_session, sample_building):
    """No documents means nothing to check."""
    result = await validate_document_currency(db_session, sample_building.id)
    assert result.total_checked == 0
    assert result.valid == 0
    assert result.expired == 0


@pytest.mark.asyncio
async def test_currency_fresh_document(db_session, sample_building):
    """A recently uploaded diagnostic report should be valid."""
    db_session.add(_make_document(sample_building.id, "diagnostic_report"))
    await db_session.commit()

    result = await validate_document_currency(db_session, sample_building.id)
    assert result.total_checked == 1
    assert result.valid == 1
    assert result.expired == 0
    assert not result.flags[0].is_expired


@pytest.mark.asyncio
async def test_currency_expired_lab_cert(db_session, sample_building):
    """A lab certificate older than 3 years should be expired."""
    old_date = datetime.now(UTC) - timedelta(days=4 * 365)
    db_session.add(_make_document(sample_building.id, "lab_certificates", created_at=old_date))
    await db_session.commit()

    result = await validate_document_currency(db_session, sample_building.id)
    assert result.total_checked == 1
    assert result.expired == 1
    assert result.flags[0].is_expired
    assert result.flags[0].max_validity_years == 3


@pytest.mark.asyncio
async def test_currency_type_without_expiry_skipped(db_session, sample_building):
    """Document types with no validity period (e.g., photos) should not be checked."""
    db_session.add(_make_document(sample_building.id, "photo"))
    await db_session.commit()

    result = await validate_document_currency(db_session, sample_building.id)
    assert result.total_checked == 0


@pytest.mark.asyncio
async def test_currency_mixed(db_session, sample_building):
    """Mix of valid and expired documents."""
    db_session.add(_make_document(sample_building.id, "diagnostic_report"))
    old_date = datetime.now(UTC) - timedelta(days=4 * 365)
    db_session.add(_make_document(sample_building.id, "lab_certificates", created_at=old_date))
    await db_session.commit()

    result = await validate_document_currency(db_session, sample_building.id)
    assert result.total_checked == 2
    assert result.valid == 1
    assert result.expired == 1


# ---------------------------------------------------------------------------
# Service Tests: get_portfolio_document_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_no_buildings(db_session, org):
    """Org with no buildings should return empty portfolio status."""
    result = await get_portfolio_document_status(db_session, org.id)
    assert result.total_buildings == 0
    assert result.average_score == 0.0
    assert result.estimated_documents_to_full == 0


@pytest.mark.asyncio
async def test_portfolio_with_buildings(db_session, org, org_user, org_building):
    """Org with a building that has no docs should show critical gaps."""
    result = await get_portfolio_document_status(db_session, org.id)
    assert result.total_buildings == 1
    assert result.average_score == 0.0
    assert result.most_commonly_missing is not None
    assert len(result.buildings_with_critical_gaps) >= 1
    assert result.estimated_documents_to_full == len(REQUIRED_DOCUMENT_TYPES)


@pytest.mark.asyncio
async def test_portfolio_full_completeness(db_session, org, org_user, org_building):
    """Org with fully documented building should score 100."""
    for doc_type in REQUIRED_DOCUMENT_TYPES:
        db_session.add(_make_document(org_building.id, doc_type))
    await db_session.commit()

    result = await get_portfolio_document_status(db_session, org.id)
    assert result.total_buildings == 1
    assert result.average_score == 100.0
    assert result.estimated_documents_to_full == 0
    assert len(result.buildings_with_critical_gaps) == 0


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_completeness_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/document-completeness returns valid response."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/document-completeness",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert "types" in data
    assert data["total_required"] == len(REQUIRED_DOCUMENT_TYPES)


@pytest.mark.asyncio
async def test_api_completeness_404(client, auth_headers):
    """GET for non-existent building returns 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/document-completeness",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_missing_documents_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/document-completeness/missing returns list."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/document-completeness/missing",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == len(REQUIRED_DOCUMENT_TYPES)


@pytest.mark.asyncio
async def test_api_currency_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/document-completeness/currency returns result."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/document-completeness/currency",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_checked" in data
    assert "flags" in data


@pytest.mark.asyncio
async def test_api_portfolio_endpoint(client, auth_headers, org):
    """GET /organizations/{id}/document-completeness returns portfolio status."""
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/document-completeness",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "average_score" in data


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    """Unauthenticated request should return 401."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/document-completeness",
    )
    assert resp.status_code in (401, 403)
