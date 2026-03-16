"""Tests for the digital vault module — service + API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.digital_vault_service import (
    generate_integrity_report,
    get_building_vault_summary,
    get_portfolio_vault_status,
    verify_document_trust,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db, name="Test Org") -> Organization:
    org = Organization(id=uuid.uuid4(), name=name, type="diagnostic_lab")
    db.add(org)
    await db.flush()
    return org


async def _create_user(db, org_id=None, role="admin") -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db, created_by) -> Building:
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Vault 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db.add(bldg)
    await db.flush()
    return bldg


async def _create_document(db, building_id, uploaded_by=None, document_type="report") -> Document:
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/files/test.pdf",
        file_name="test.pdf",
        document_type=document_type,
        uploaded_by=uploaded_by,
        created_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.flush()
    return doc


async def _create_diagnostic(db, building_id, status="completed", days_ago=0) -> Diagnostic:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status=status,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
    db.add(diag)
    await db.flush()
    return diag


async def _create_sample(db, diagnostic_id, concentration=None) -> Sample:
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        concentration=concentration,
        created_at=datetime.now(UTC),
    )
    db.add(sample)
    await db.flush()
    return sample


async def _create_intervention(db, building_id) -> Intervention:
    interv = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="removal",
        title="Test intervention",
        status="completed",
        created_at=datetime.now(UTC),
    )
    db.add(interv)
    await db.flush()
    return interv


async def _create_action_item(db, building_id) -> ActionItem:
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        source_type="diagnostic",
        action_type="remediation",
        title="Test action",
        priority="medium",
        status="open",
        created_at=datetime.now(UTC),
    )
    db.add(action)
    await db.flush()
    return action


# ---------------------------------------------------------------------------
# FN1 — get_building_vault_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vault_summary_empty_building(db_session, admin_user, sample_building):
    """Empty building has 0 entries and integrity_score 1.0."""
    result = await get_building_vault_summary(sample_building.id, db_session)
    assert result is not None
    assert result.total_entries == 0
    assert result.verified_count == 0
    assert result.unverified_count == 0
    assert result.integrity_score == 1.0
    assert result.last_verified_at is None


@pytest.mark.asyncio
async def test_vault_summary_not_found(db_session):
    """Non-existent building returns None."""
    result = await get_building_vault_summary(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_vault_summary_with_documents_and_diagnostics(db_session, admin_user, sample_building):
    """Building with documents and diagnostics counts entries correctly."""
    await _create_document(db_session, sample_building.id, admin_user.id)
    await _create_document(db_session, sample_building.id, admin_user.id)
    diag = await _create_diagnostic(db_session, sample_building.id)
    await _create_sample(db_session, diag.id, concentration=5.0)
    await db_session.commit()

    result = await get_building_vault_summary(sample_building.id, db_session)
    assert result is not None
    # 2 docs + 1 diag + 1 sample = 4
    assert result.total_entries == 4
    assert result.verified_count == 2  # documents
    assert result.unverified_count == 2  # diag + sample
    assert result.last_verified_at is not None


@pytest.mark.asyncio
async def test_vault_summary_integrity_score(db_session, admin_user, sample_building):
    """Integrity score = verified / total."""
    await _create_document(db_session, sample_building.id, admin_user.id)
    diag = await _create_diagnostic(db_session, sample_building.id)
    await _create_sample(db_session, diag.id)
    await _create_intervention(db_session, sample_building.id)
    await _create_action_item(db_session, sample_building.id)
    await db_session.commit()

    result = await get_building_vault_summary(sample_building.id, db_session)
    assert result is not None
    # 1 doc + 1 diag + 1 sample + 1 interv + 1 action = 5 total, 1 verified
    assert result.total_entries == 5
    assert result.integrity_score == pytest.approx(0.2, abs=0.01)


# ---------------------------------------------------------------------------
# FN2 — verify_document_trust
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_document_trust_exists(db_session, admin_user, sample_building):
    """Existing document returns verified result with intact hash."""
    doc = await _create_document(db_session, sample_building.id, admin_user.id)
    await db_session.commit()

    result = await verify_document_trust(doc.id, db_session)
    assert result is not None
    assert result.document_id == doc.id
    assert result.file_name == "test.pdf"
    assert result.is_intact is True
    assert result.original_hash == result.current_hash
    assert len(result.chain_of_custody) == 2
    assert result.chain_of_custody[0].event_type == "upload"
    assert result.chain_of_custody[1].event_type == "verify"


@pytest.mark.asyncio
async def test_verify_document_trust_not_found(db_session):
    """Non-existent document returns None."""
    result = await verify_document_trust(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_verify_document_trust_fields(db_session, admin_user, sample_building):
    """Verification includes document_type and upload_date."""
    doc = await _create_document(db_session, sample_building.id, admin_user.id, document_type="lab_report")
    await db_session.commit()

    result = await verify_document_trust(doc.id, db_session)
    assert result is not None
    assert result.document_type == "lab_report"
    assert result.upload_date is not None


# ---------------------------------------------------------------------------
# FN3 — generate_integrity_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integrity_report_clean_building(db_session, admin_user, sample_building):
    """Building with only good records has 100% integrity."""
    await _create_document(db_session, sample_building.id, admin_user.id, document_type="report")
    diag = await _create_diagnostic(db_session, sample_building.id, status="completed")
    await _create_sample(db_session, diag.id, concentration=5.0)
    await db_session.commit()

    result = await generate_integrity_report(sample_building.id, db_session)
    assert result is not None
    assert result.integrity_percentage == pytest.approx(100.0)
    assert len(result.suspicious_entries) == 0
    assert len(result.recommendations) >= 1


@pytest.mark.asyncio
async def test_integrity_report_not_found(db_session):
    """Non-existent building returns None."""
    result = await generate_integrity_report(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_integrity_report_stale_drafts(db_session, admin_user, sample_building):
    """Stale draft diagnostics are flagged as suspicious."""
    await _create_diagnostic(db_session, sample_building.id, status="draft", days_ago=120)
    await db_session.commit()

    result = await generate_integrity_report(sample_building.id, db_session)
    assert result is not None
    assert len(result.suspicious_entries) == 1
    assert result.suspicious_entries[0].record_type == "diagnostic_report"
    assert "stale" in result.suspicious_entries[0].issue.lower()


@pytest.mark.asyncio
async def test_integrity_report_incomplete_samples(db_session, admin_user, sample_building):
    """Samples without concentration are flagged as suspicious."""
    diag = await _create_diagnostic(db_session, sample_building.id, status="completed")
    await _create_sample(db_session, diag.id, concentration=None)
    await db_session.commit()

    result = await generate_integrity_report(sample_building.id, db_session)
    assert result is not None
    suspicious_samples = [s for s in result.suspicious_entries if s.record_type == "sample_result"]
    assert len(suspicious_samples) == 1
    assert suspicious_samples[0].severity == "high"


@pytest.mark.asyncio
async def test_integrity_report_unclassified_document(db_session, admin_user, sample_building):
    """Document without document_type is flagged."""
    await _create_document(db_session, sample_building.id, admin_user.id, document_type=None)
    await db_session.commit()

    result = await generate_integrity_report(sample_building.id, db_session)
    assert result is not None
    doc_suspicious = [s for s in result.suspicious_entries if s.record_type == "document"]
    assert len(doc_suspicious) == 1
    assert doc_suspicious[0].severity == "low"


@pytest.mark.asyncio
async def test_integrity_report_empty_building(db_session, admin_user, sample_building):
    """Empty building has 100% integrity."""
    result = await generate_integrity_report(sample_building.id, db_session)
    assert result is not None
    assert result.total_documents == 0
    assert result.integrity_percentage == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_integrity_report_recommendations(db_session, admin_user, sample_building):
    """Recommendations are generated based on issues found."""
    await _create_document(db_session, sample_building.id, admin_user.id, document_type=None)
    diag = await _create_diagnostic(db_session, sample_building.id, status="draft", days_ago=120)
    await _create_sample(db_session, diag.id, concentration=None)
    await db_session.commit()

    result = await generate_integrity_report(sample_building.id, db_session)
    assert result is not None
    assert len(result.recommendations) == 3


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_vault_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_vault_empty_org(db_session):
    """Empty org has 0 buildings and default scores."""
    org = await _create_org(db_session)
    await db_session.commit()

    result = await get_portfolio_vault_status(org.id, db_session)
    assert result is not None
    assert result.total_buildings == 0
    assert result.total_vault_entries == 0
    assert result.average_integrity_score == 1.0
    assert result.buildings_with_issues == 0


@pytest.mark.asyncio
async def test_portfolio_vault_not_found(db_session):
    """Non-existent org returns None."""
    result = await get_portfolio_vault_status(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_portfolio_vault_with_buildings(db_session):
    """Org with buildings aggregates vault data."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    bldg = await _create_building(db_session, created_by=user.id)
    await _create_document(db_session, bldg.id, user.id)
    diag = await _create_diagnostic(db_session, bldg.id)
    await _create_sample(db_session, diag.id, concentration=5.0)
    await db_session.commit()

    result = await get_portfolio_vault_status(org.id, db_session)
    assert result is not None
    assert result.total_buildings == 1
    assert result.total_vault_entries >= 3
    assert result.by_record_type.get("document", 0) == 1
    assert result.by_record_type.get("diagnostic_report", 0) == 1


@pytest.mark.asyncio
async def test_portfolio_vault_issues_count(db_session):
    """Buildings with low integrity score are counted as issues."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    # Building with only non-document entries → integrity < 0.8
    bldg = await _create_building(db_session, created_by=user.id)
    diag = await _create_diagnostic(db_session, bldg.id)
    await _create_sample(db_session, diag.id)
    await _create_intervention(db_session, bldg.id)
    await _create_action_item(db_session, bldg.id)
    await db_session.commit()

    result = await get_portfolio_vault_status(org.id, db_session)
    assert result is not None
    assert result.buildings_with_issues == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_vault_summary_200(client, auth_headers, admin_user, sample_building):
    """GET /digital-vault/buildings/{id}/summary returns 200."""
    resp = await client.get(
        f"/api/v1/digital-vault/buildings/{sample_building.id}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "integrity_score" in data


@pytest.mark.asyncio
async def test_api_vault_summary_404(client, auth_headers):
    """GET /digital-vault/buildings/{id}/summary returns 404 for unknown building."""
    resp = await client.get(
        f"/api/v1/digital-vault/buildings/{uuid.uuid4()}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_verify_document_200(client, auth_headers, db_session, admin_user, sample_building):
    """GET /digital-vault/documents/{id}/verify returns 200."""
    doc = await _create_document(db_session, sample_building.id, admin_user.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/digital-vault/documents/{doc.id}/verify",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_intact"] is True


@pytest.mark.asyncio
async def test_api_verify_document_404(client, auth_headers):
    """GET /digital-vault/documents/{id}/verify returns 404 for unknown document."""
    resp = await client.get(
        f"/api/v1/digital-vault/documents/{uuid.uuid4()}/verify",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_integrity_report_200(client, auth_headers, admin_user, sample_building):
    """GET /digital-vault/buildings/{id}/integrity-report returns 200."""
    resp = await client.get(
        f"/api/v1/digital-vault/buildings/{sample_building.id}/integrity-report",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "integrity_percentage" in data
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_api_integrity_report_404(client, auth_headers):
    """GET /digital-vault/buildings/{id}/integrity-report returns 404."""
    resp = await client.get(
        f"/api/v1/digital-vault/buildings/{uuid.uuid4()}/integrity-report",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_portfolio_status_200(client, auth_headers, db_session):
    """GET /digital-vault/organizations/{id}/status returns 200."""
    org = await _create_org(db_session)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/digital-vault/organizations/{org.id}/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_portfolio_status_404(client, auth_headers):
    """GET /digital-vault/organizations/{id}/status returns 404."""
    resp = await client.get(
        f"/api/v1/digital-vault/organizations/{uuid.uuid4()}/status",
        headers=auth_headers,
    )
    assert resp.status_code == 404
