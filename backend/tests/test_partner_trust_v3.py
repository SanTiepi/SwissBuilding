"""Tests for Partner Trust V3 doctrine integration.

Covers: case-rooted signals, ritual signals, RFQ trust wiring,
contractor acknowledgment trust wiring, trusted partner lookup,
and API endpoints.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.contractor_acknowledgment import ContractorAcknowledgment
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.partner_trust import PartnerTrustProfile, PartnerTrustSignal
from app.models.rfq import TenderInvitation, TenderRequest
from app.services.partner_trust_service import (
    get_partner_trust_for_case,
    get_profile,
    get_trusted_partners_for_work_family,
    record_signal_from_case,
    record_signal_from_ritual,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(db_session, *, org_id=None, name="Contractor Corp", org_type="contractor"):
    org = Organization(
        id=org_id or uuid.uuid4(),
        name=name,
        type=org_type,
    )
    db_session.add(org)
    return org


def _make_building(db_session, *, building_id=None, created_by=None):
    b = Building(
        id=building_id or uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db_session.add(b)
    return b


def _make_case(db_session, building_id, org_id, created_by_id, *, tender_id=None):
    case = BuildingCase(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        case_type="tender",
        title="Test case",
        state="draft",
        tender_id=tender_id,
        priority="medium",
    )
    db_session.add(case)
    return case


def _make_tender(db_session, building_id, created_by_id, *, org_id=None):
    t = TenderRequest(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        title="Test tender",
        work_type="asbestos_removal",
        status="draft",
    )
    db_session.add(t)
    return t


# ---------------------------------------------------------------------------
# record_signal_from_case
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_signal_from_case_creates_signal(db_session, admin_user):
    """Signal from case records correctly with source_entity_type=building_case."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()
    case = _make_case(db_session, building.id, org.id, admin_user.id)
    await db_session.commit()

    signal = await record_signal_from_case(
        db_session,
        partner_org_id=org.id,
        case_id=case.id,
        signal_type="delivery_success",
        notes="Quote submitted",
    )

    assert signal.partner_org_id == org.id
    assert signal.signal_type == "delivery_success"
    assert signal.source_entity_type == "building_case"
    assert signal.source_entity_id == case.id
    assert signal.notes == "Quote submitted"


@pytest.mark.asyncio
async def test_record_signal_from_case_auto_evaluates(db_session, admin_user):
    """Recording a case signal auto-evaluates the partner profile."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()
    case = _make_case(db_session, building.id, org.id, admin_user.id)
    await db_session.commit()

    await record_signal_from_case(db_session, org.id, case.id, "delivery_success")
    await db_session.commit()

    profile = await get_profile(db_session, org.id)
    assert profile is not None
    assert profile.signal_count == 1
    assert profile.delivery_reliability_score == 1.0


# ---------------------------------------------------------------------------
# record_signal_from_ritual
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_signal_from_ritual(db_session, admin_user):
    """Signal from ritual records with source_entity_type=truth_ritual."""
    org = _make_org(db_session)
    await db_session.commit()

    ritual_id = uuid.uuid4()
    signal = await record_signal_from_ritual(
        db_session,
        partner_org_id=org.id,
        ritual_id=ritual_id,
        signal_type="evidence_clean",
    )

    assert signal.source_entity_type == "truth_ritual"
    assert signal.source_entity_id == ritual_id
    assert signal.signal_type == "evidence_clean"


# ---------------------------------------------------------------------------
# get_partner_trust_for_case
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_partner_trust_for_case_empty(db_session, admin_user):
    """Returns empty list for a non-existent case."""
    result = await get_partner_trust_for_case(db_session, uuid.uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_get_partner_trust_for_case_with_tender(db_session, admin_user):
    """Returns partner trust for case linked to a tender with invitations."""
    org_owner = _make_org(db_session, name="Owner Org", org_type="property_management")
    org_contractor = _make_org(db_session, name="Contractor A", org_type="contractor")
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()

    tender = _make_tender(db_session, building.id, admin_user.id, org_id=org_owner.id)
    await db_session.flush()

    case = _make_case(db_session, building.id, org_owner.id, admin_user.id, tender_id=tender.id)

    # Create invitation for contractor
    inv = TenderInvitation(
        id=uuid.uuid4(),
        tender_id=tender.id,
        contractor_org_id=org_contractor.id,
        status="pending",
    )
    db_session.add(inv)
    await db_session.commit()

    result = await get_partner_trust_for_case(db_session, case.id)
    assert len(result) == 1
    assert result[0]["partner_org_id"] == str(org_contractor.id)
    assert result[0]["overall_trust_level"] == "unknown"
    assert result[0]["case_signal_count"] == 0


@pytest.mark.asyncio
async def test_get_partner_trust_for_case_includes_signal_partners(db_session, admin_user):
    """Partners with case-linked signals also appear even without tender invitations."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()
    case = _make_case(db_session, building.id, org.id, admin_user.id)
    await db_session.commit()

    await record_signal_from_case(db_session, org.id, case.id, "delivery_success")
    await db_session.commit()

    result = await get_partner_trust_for_case(db_session, case.id)
    assert len(result) == 1
    assert result[0]["case_signal_count"] == 1
    assert result[0]["total_signal_count"] == 1


# ---------------------------------------------------------------------------
# get_trusted_partners_for_work_family
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trusted_partners_empty(db_session, admin_user):
    """Returns empty list when no partners have adequate+ trust."""
    org = _make_org(db_session)
    await db_session.commit()
    result = await get_trusted_partners_for_work_family(db_session, org.id, "asbestos_removal")
    assert result == []


@pytest.mark.asyncio
async def test_get_trusted_partners_returns_adequate_plus(db_session, admin_user):
    """Returns partners with adequate or strong trust."""
    org_requester = _make_org(db_session, name="Requester", org_type="property_management")
    org_strong = _make_org(db_session, name="Strong Partner", org_type="contractor")
    org_weak = _make_org(db_session, name="Weak Partner", org_type="contractor")
    await db_session.flush()

    # Create strong profile
    strong_profile = PartnerTrustProfile(
        partner_org_id=org_strong.id,
        delivery_reliability_score=0.9,
        evidence_quality_score=0.85,
        responsiveness_score=0.95,
        overall_trust_level="strong",
        signal_count=10,
        last_evaluated_at=datetime.now(UTC),
    )
    db_session.add(strong_profile)

    # Create weak profile
    weak_profile = PartnerTrustProfile(
        partner_org_id=org_weak.id,
        delivery_reliability_score=0.2,
        evidence_quality_score=0.1,
        responsiveness_score=0.3,
        overall_trust_level="weak",
        signal_count=5,
        last_evaluated_at=datetime.now(UTC),
    )
    db_session.add(weak_profile)
    await db_session.commit()

    result = await get_trusted_partners_for_work_family(db_session, org_requester.id, "asbestos_removal")
    assert len(result) == 1
    assert result[0]["partner_org_id"] == str(org_strong.id)
    assert result[0]["guidance"] == "qualified"
    assert result[0]["work_family"] == "asbestos_removal"


@pytest.mark.asyncio
async def test_get_trusted_partners_excludes_self(db_session, admin_user):
    """Requesting org is excluded from results even if it has adequate+ trust."""
    org = _make_org(db_session, name="Self Org", org_type="contractor")
    await db_session.flush()

    profile = PartnerTrustProfile(
        partner_org_id=org.id,
        overall_trust_level="strong",
        signal_count=5,
        last_evaluated_at=datetime.now(UTC),
    )
    db_session.add(profile)
    await db_session.commit()

    result = await get_trusted_partners_for_work_family(db_session, org.id, "general")
    assert len(result) == 0


# ---------------------------------------------------------------------------
# RFQ trust wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rfq_submit_quote_records_signal(db_session, admin_user):
    """Submitting a quote via RFQ service records a delivery_success signal."""
    from app.services.rfq_service import submit_quote

    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()

    tender = _make_tender(db_session, building.id, admin_user.id, org_id=org.id)
    tender.status = "sent"
    await db_session.flush()

    # Create a case linked to the tender
    _make_case(db_session, building.id, org.id, admin_user.id, tender_id=tender.id)
    await db_session.commit()

    await submit_quote(
        db_session,
        tender.id,
        {
            "contractor_org_id": org.id,
            "total_amount_chf": 50000,
            "scope_description": "Full removal",
        },
    )
    await db_session.commit()

    # Verify trust signal was recorded
    from sqlalchemy import select

    signals = (
        (await db_session.execute(select(PartnerTrustSignal).where(PartnerTrustSignal.partner_org_id == org.id)))
        .scalars()
        .all()
    )

    assert len(signals) >= 1
    signal_types = {s.signal_type for s in signals}
    assert "delivery_success" in signal_types


@pytest.mark.asyncio
async def test_rfq_attribute_tender_records_signal(db_session, admin_user):
    """Attributing a tender records delivery_success for the winner."""
    from app.services.rfq_service import attribute_tender, submit_quote

    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()

    tender = _make_tender(db_session, building.id, admin_user.id, org_id=org.id)
    tender.status = "sent"
    await db_session.flush()
    _make_case(db_session, building.id, org.id, admin_user.id, tender_id=tender.id)
    await db_session.commit()

    quote = await submit_quote(
        db_session,
        tender.id,
        {"contractor_org_id": org.id, "total_amount_chf": 30000},
    )
    await db_session.commit()

    await attribute_tender(db_session, tender.id, quote.id, reason="Best quality evidence")
    await db_session.commit()

    from sqlalchemy import select

    signals = (
        (await db_session.execute(select(PartnerTrustSignal).where(PartnerTrustSignal.partner_org_id == org.id)))
        .scalars()
        .all()
    )

    # At least: 1 from submit_quote + 1 from attribute + 1 quality bonus
    signal_types = [s.signal_type for s in signals]
    assert signal_types.count("delivery_success") >= 2
    assert "evidence_clean" in signal_types  # quality keyword in reason


# ---------------------------------------------------------------------------
# Contractor acknowledgment trust wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contractor_ack_records_response_fast(db_session, admin_user):
    """Acknowledging within 48h records response_fast signal."""
    from app.services.contractor_acknowledgment_service import acknowledge, send_acknowledgment

    org = _make_org(db_session)
    admin_user.organization_id = org.id
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()

    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="asbestos_removal",
        title="Test intervention",
        status="planned",
    )
    db_session.add(intervention)
    await db_session.flush()

    ack = ContractorAcknowledgment(
        id=uuid.uuid4(),
        intervention_id=intervention.id,
        building_id=building.id,
        contractor_user_id=admin_user.id,
        status="pending",
        safety_requirements=[{"item": "Mask required"}],
        created_by=admin_user.id,
    )
    db_session.add(ack)
    await db_session.commit()

    await send_acknowledgment(db_session, ack.id)
    await db_session.commit()

    await acknowledge(db_session, ack.id, notes="All good")
    await db_session.commit()

    from sqlalchemy import select

    signals = (
        (await db_session.execute(select(PartnerTrustSignal).where(PartnerTrustSignal.partner_org_id == org.id)))
        .scalars()
        .all()
    )

    assert len(signals) == 1
    assert signals[0].signal_type == "response_fast"
    assert signals[0].source_entity_type == "contractor_acknowledgment"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_partner_trust_profile(client, auth_headers, db_session, admin_user):
    """GET /partners/{org_id}/trust-profile returns profile."""
    org = _make_org(db_session)
    await db_session.flush()

    profile = PartnerTrustProfile(
        partner_org_id=org.id,
        overall_trust_level="adequate",
        signal_count=3,
        last_evaluated_at=datetime.now(UTC),
    )
    db_session.add(profile)
    await db_session.commit()

    resp = await client.get(f"/api/v1/partners/{org.id}/trust-profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_trust_level"] == "adequate"
    assert data["signal_count"] == 3


@pytest.mark.asyncio
async def test_api_get_partner_trust_profile_404(client, auth_headers):
    """GET /partners/{org_id}/trust-profile returns 404 for unknown org."""
    resp = await client.get(f"/api/v1/partners/{uuid.uuid4()}/trust-profile", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_get_case_partner_trust(client, auth_headers, db_session, admin_user):
    """GET /cases/{case_id}/partner-trust returns partner trust for a case."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.flush()

    tender = _make_tender(db_session, building.id, admin_user.id, org_id=org.id)
    await db_session.flush()
    case = _make_case(db_session, building.id, org.id, admin_user.id, tender_id=tender.id)

    inv = TenderInvitation(
        id=uuid.uuid4(),
        tender_id=tender.id,
        contractor_org_id=org.id,
        status="pending",
    )
    db_session.add(inv)
    await db_session.commit()

    resp = await client.get(f"/api/v1/cases/{case.id}/partner-trust", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["partner_org_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_get_case_partner_trust_empty(client, auth_headers):
    """GET /cases/{case_id}/partner-trust returns empty for non-existent case."""
    resp = await client.get(f"/api/v1/cases/{uuid.uuid4()}/partner-trust", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
