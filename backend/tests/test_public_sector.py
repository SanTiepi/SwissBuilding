"""BatiConnect — Public Sector tests (service-layer + route-level)."""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.api.public_sector import router as public_sector_router
from app.main import app
from app.models.organization import Organization
from app.services.public_sector_service import (
    activate_public_mode,
    circulate_review_pack,
    emit_governance_signal,
    generate_committee_pack,
    generate_review_pack,
    get_committee_packs,
    get_decision_traces,
    get_governance_signals,
    get_public_mode,
    get_review_packs,
    record_decision,
    resolve_signal,
)

# Register router for HTTP tests
app.include_router(public_sector_router, prefix="/api/v1")


# ---- Helpers ----


async def _create_org(db):
    org = Organization(id=uuid.uuid4(), name="Commune Test", type="authority")
    db.add(org)
    await db.flush()
    return org


# ---- Service-layer: Operating Mode ----


@pytest.mark.asyncio
async def test_activate_public_mode(db_session):
    org = await _create_org(db_session)
    mode = await activate_public_mode(
        db_session,
        org.id,
        {
            "mode_type": "municipal",
            "governance_level": "enhanced",
            "requires_committee_review": True,
        },
    )
    assert mode.id is not None
    assert mode.mode_type == "municipal"
    assert mode.governance_level == "enhanced"
    assert mode.requires_committee_review is True


@pytest.mark.asyncio
async def test_activate_public_mode_upsert(db_session):
    org = await _create_org(db_session)
    await activate_public_mode(db_session, org.id, {"mode_type": "municipal"})
    updated = await activate_public_mode(db_session, org.id, {"mode_type": "cantonal", "governance_level": "strict"})
    assert updated.mode_type == "cantonal"
    assert updated.governance_level == "strict"


@pytest.mark.asyncio
async def test_get_public_mode(db_session):
    org = await _create_org(db_session)
    await activate_public_mode(db_session, org.id, {"mode_type": "federal"})
    mode = await get_public_mode(db_session, org.id)
    assert mode is not None
    assert mode.mode_type == "federal"


@pytest.mark.asyncio
async def test_get_public_mode_not_found(db_session):
    mode = await get_public_mode(db_session, uuid.uuid4())
    assert mode is None


# ---- Service-layer: Review Pack ----


@pytest.mark.asyncio
async def test_generate_review_pack(db_session, sample_building, admin_user):
    pack = await generate_review_pack(db_session, sample_building.id, admin_user.id)
    assert pack.id is not None
    assert pack.status == "ready"
    assert pack.content_hash is not None
    assert len(pack.sections) == 6
    assert pack.generated_at is not None


@pytest.mark.asyncio
async def test_generate_review_pack_with_notes(db_session, sample_building, admin_user):
    pack = await generate_review_pack(
        db_session,
        sample_building.id,
        admin_user.id,
        notes="Annual review",
        review_deadline=date(2026, 12, 31),
    )
    assert pack.notes == "Annual review"
    assert pack.review_deadline == date(2026, 12, 31)


@pytest.mark.asyncio
async def test_circulate_review_pack(db_session, sample_building, admin_user):
    pack = await generate_review_pack(db_session, sample_building.id, admin_user.id)
    recipients = [{"org_name": "Commission", "role": "committee", "sent_at": "2026-03-25"}]
    circulated = await circulate_review_pack(db_session, pack.id, recipients)
    assert circulated.status == "circulating"
    assert circulated.circulated_to == recipients


@pytest.mark.asyncio
async def test_circulate_review_pack_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await circulate_review_pack(db_session, uuid.uuid4(), [])


@pytest.mark.asyncio
async def test_get_review_packs(db_session, sample_building, admin_user):
    await generate_review_pack(db_session, sample_building.id, admin_user.id)
    await generate_review_pack(db_session, sample_building.id, admin_user.id)
    packs = await get_review_packs(db_session, sample_building.id)
    assert len(packs) == 2


# ---- Service-layer: Committee Pack ----


@pytest.mark.asyncio
async def test_generate_committee_pack(db_session, sample_building):
    pack = await generate_committee_pack(
        db_session,
        sample_building.id,
        {
            "committee_name": "Commission des travaux",
            "committee_type": "building_committee",
        },
    )
    assert pack.id is not None
    assert pack.status == "draft"
    assert pack.committee_type == "building_committee"
    assert pack.content_hash is not None
    assert len(pack.sections) == 5


@pytest.mark.asyncio
async def test_generate_committee_pack_with_clauses(db_session, sample_building):
    clauses = [{"clause_id": "ECO-001", "clause_text": "SUVA certified", "legal_ref": "OTConst 82", "scope": "all"}]
    pack = await generate_committee_pack(
        db_session,
        sample_building.id,
        {
            "committee_name": "Procurement Board",
            "committee_type": "procurement_committee",
            "procurement_clauses": clauses,
        },
    )
    assert pack.procurement_clauses == clauses


@pytest.mark.asyncio
async def test_get_committee_packs(db_session, sample_building):
    await generate_committee_pack(
        db_session,
        sample_building.id,
        {
            "committee_name": "C1",
            "committee_type": "other",
        },
    )
    packs = await get_committee_packs(db_session, sample_building.id)
    assert len(packs) == 1


# ---- Service-layer: Decision Traces ----


@pytest.mark.asyncio
async def test_record_decision(db_session):
    pack_id = uuid.uuid4()
    trace = await record_decision(
        db_session,
        {
            "pack_type": "committee",
            "pack_id": pack_id,
            "reviewer_name": "Jean Dupont",
            "reviewer_role": "President",
            "decision": "approved",
            "decided_at": datetime(2026, 3, 20, 16, 0, tzinfo=UTC),
        },
    )
    assert trace.id is not None
    assert trace.decision == "approved"


@pytest.mark.asyncio
async def test_record_decision_with_conditions(db_session):
    pack_id = uuid.uuid4()
    trace = await record_decision(
        db_session,
        {
            "pack_type": "municipal_review",
            "pack_id": pack_id,
            "reviewer_name": "Marie Morel",
            "decision": "deferred",
            "conditions": "Require additional quote",
            "confidence_level": "medium",
            "decided_at": datetime(2026, 3, 20, 17, 0, tzinfo=UTC),
        },
    )
    assert trace.conditions == "Require additional quote"
    assert trace.confidence_level == "medium"


@pytest.mark.asyncio
async def test_get_decision_traces(db_session):
    pack_id = uuid.uuid4()
    await record_decision(
        db_session,
        {
            "pack_type": "committee",
            "pack_id": pack_id,
            "reviewer_name": "A",
            "decision": "approved",
            "decided_at": datetime(2026, 3, 20, 16, 0, tzinfo=UTC),
        },
    )
    await record_decision(
        db_session,
        {
            "pack_type": "committee",
            "pack_id": pack_id,
            "reviewer_name": "B",
            "decision": "deferred",
            "decided_at": datetime(2026, 3, 20, 17, 0, tzinfo=UTC),
        },
    )
    traces = await get_decision_traces(db_session, "committee", pack_id)
    assert len(traces) == 2


# ---- Service-layer: Governance Signals ----


@pytest.mark.asyncio
async def test_emit_governance_signal(db_session):
    org = await _create_org(db_session)
    signal = await emit_governance_signal(
        db_session,
        {
            "organization_id": org.id,
            "signal_type": "review_overdue",
            "severity": "warning",
            "title": "Annual review overdue",
        },
    )
    assert signal.id is not None
    assert signal.resolved is False


@pytest.mark.asyncio
async def test_get_governance_signals(db_session, sample_building):
    org = await _create_org(db_session)
    await emit_governance_signal(
        db_session,
        {
            "organization_id": org.id,
            "building_id": sample_building.id,
            "signal_type": "decision_pending",
            "severity": "info",
            "title": "Decision pending",
        },
    )
    await emit_governance_signal(
        db_session,
        {
            "organization_id": org.id,
            "signal_type": "governance_gap",
            "severity": "critical",
            "title": "Gap detected",
        },
    )
    all_signals = await get_governance_signals(db_session, org.id)
    assert len(all_signals) == 2
    building_signals = await get_governance_signals(db_session, org.id, sample_building.id)
    assert len(building_signals) == 1


@pytest.mark.asyncio
async def test_resolve_signal(db_session):
    org = await _create_org(db_session)
    signal = await emit_governance_signal(
        db_session,
        {
            "organization_id": org.id,
            "signal_type": "proof_aging",
            "severity": "warning",
            "title": "Proof aging",
        },
    )
    resolved = await resolve_signal(db_session, signal.id)
    assert resolved.resolved is True
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_resolve_signal_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await resolve_signal(db_session, uuid.uuid4())


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_activate_public_mode(client, auth_headers, db_session):
    org = await _create_org(db_session)
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/organizations/{org.id}/public-owner-mode",
        json={"mode_type": "municipal", "governance_level": "enhanced"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mode_type"] == "municipal"
    assert body["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_get_public_mode(client, auth_headers, db_session):
    org = await _create_org(db_session)
    await activate_public_mode(db_session, org.id, {"mode_type": "cantonal"})
    await db_session.commit()
    resp = await client.get(f"/api/v1/organizations/{org.id}/public-owner-mode", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["mode_type"] == "cantonal"


@pytest.mark.asyncio
async def test_api_get_public_mode_404(client, auth_headers):
    resp = await client.get(f"/api/v1/organizations/{uuid.uuid4()}/public-owner-mode", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_generate_review_pack(client, auth_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/review-packs",
        json={"notes": "Test pack"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ready"
    assert body["notes"] == "Test pack"


@pytest.mark.asyncio
async def test_api_list_review_packs(client, auth_headers, sample_building):
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/review-packs",
        json={},
        headers=auth_headers,
    )
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/review-packs", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_circulate_review_pack(client, auth_headers, db_session, sample_building, admin_user):
    pack = await generate_review_pack(db_session, sample_building.id, admin_user.id)
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/review-packs/{pack.id}/circulate",
        json={"recipients": [{"org_name": "Commission", "role": "committee", "sent_at": "2026-03-25"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "circulating"


@pytest.mark.asyncio
async def test_api_generate_committee_pack(client, auth_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/committee-packs",
        json={"committee_name": "Test Committee", "committee_type": "building_committee"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["committee_name"] == "Test Committee"
    assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_api_list_committee_packs(client, auth_headers, sample_building):
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/committee-packs",
        json={"committee_name": "C1", "committee_type": "other"},
        headers=auth_headers,
    )
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/committee-packs", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_record_decision(client, auth_headers, db_session, sample_building):
    pack = await generate_committee_pack(
        db_session,
        sample_building.id,
        {
            "committee_name": "C1",
            "committee_type": "other",
        },
    )
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/committee-packs/{pack.id}/decide",
        json={
            "reviewer_name": "Jean Dupont",
            "decision": "approved",
            "decided_at": "2026-03-20T16:00:00Z",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "approved"
    assert body["pack_type"] == "committee"


@pytest.mark.asyncio
async def test_api_list_decision_traces(client, auth_headers, db_session, sample_building):
    pack = await generate_committee_pack(
        db_session,
        sample_building.id,
        {
            "committee_name": "C1",
            "committee_type": "other",
        },
    )
    await record_decision(
        db_session,
        {
            "pack_type": "committee",
            "pack_id": pack.id,
            "reviewer_name": "A",
            "decision": "approved",
            "decided_at": datetime(2026, 3, 20, 16, 0, tzinfo=UTC),
        },
    )
    await db_session.commit()
    resp = await client.get(f"/api/v1/decision-traces/committee/{pack.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_api_governance_signals(client, auth_headers, db_session):
    org = await _create_org(db_session)
    await emit_governance_signal(
        db_session,
        {
            "organization_id": org.id,
            "signal_type": "governance_gap",
            "severity": "critical",
            "title": "Gap",
        },
    )
    await db_session.commit()
    resp = await client.get(f"/api/v1/organizations/{org.id}/governance-signals", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["signal_type"] == "governance_gap"


@pytest.mark.asyncio
async def test_api_resolve_signal(client, auth_headers, db_session):
    org = await _create_org(db_session)
    signal = await emit_governance_signal(
        db_session,
        {
            "organization_id": org.id,
            "signal_type": "proof_aging",
            "severity": "warning",
            "title": "Aging",
        },
    )
    await db_session.commit()
    resp = await client.post(f"/api/v1/governance-signals/{signal.id}/resolve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True


@pytest.mark.asyncio
async def test_api_resolve_signal_404(client, auth_headers):
    resp = await client.post(f"/api/v1/governance-signals/{uuid.uuid4()}/resolve", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_review_pack_building_not_found(client, auth_headers):
    resp = await client.post(
        f"/api/v1/buildings/{uuid.uuid4()}/review-packs",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 404
