"""BatiConnect — Exchange contract + Partner trust tests (service + route)."""

import uuid
from datetime import date

import pytest

from app.api.exchange import router as exchange_router
from app.api.partner_trust import router as partner_trust_router
from app.main import app
from app.models.exchange_contract import ExchangeContractVersion
from app.models.organization import Organization
from app.services.exchange_service import (
    get_active_contract,
    get_imports,
    get_publications,
    list_contracts,
    publish_passport,
    record_import,
)
from app.services.partner_trust_service import (
    evaluate_partner,
    get_profile,
    get_routing_hint,
    list_profiles,
    record_signal,
)

# Register routers for HTTP tests (not yet in router.py hub file)
app.include_router(exchange_router, prefix="/api/v1")
app.include_router(partner_trust_router, prefix="/api/v1")


# ============================================================
# Helpers
# ============================================================


async def _create_contract(db, code="test_contract_v1", **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "contract_code": code,
        "version": 1,
        "status": "active",
        "audience_type": "authority",
        "payload_type": "diagnostic_report",
        "effective_from": date(2025, 1, 1),
    }
    defaults.update(overrides)
    c = ExchangeContractVersion(**defaults)
    db.add(c)
    await db.flush()
    return c


async def _create_org(db, name="Partner Org"):
    org = Organization(id=uuid.uuid4(), name=name, type="diagnostic_lab")
    db.add(org)
    await db.flush()
    return org


# ============================================================
# Exchange Service Tests
# ============================================================


@pytest.mark.asyncio
async def test_list_contracts_empty(db_session):
    result = await list_contracts(db_session)
    assert result == []


@pytest.mark.asyncio
async def test_list_contracts_returns_all(db_session):
    await _create_contract(db_session, "alpha_v1")
    await _create_contract(db_session, "beta_v1", audience_type="insurer")
    result = await list_contracts(db_session)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_contracts_filter_audience(db_session):
    await _create_contract(db_session, "alpha_v1", audience_type="authority")
    await _create_contract(db_session, "beta_v1", audience_type="insurer")
    result = await list_contracts(db_session, audience_filter="insurer")
    assert len(result) == 1
    assert result[0].audience_type == "insurer"


@pytest.mark.asyncio
async def test_get_active_contract(db_session):
    await _create_contract(db_session, "diag_v1", status="active")
    await _create_contract(db_session, "diag_v1", status="deprecated", version=0, id=uuid.uuid4())
    result = await get_active_contract(db_session, "diag_v1")
    assert result is not None
    assert result.status == "active"


@pytest.mark.asyncio
async def test_get_active_contract_not_found(db_session):
    result = await get_active_contract(db_session, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_publish_passport(db_session, sample_building):
    contract = await _create_contract(db_session)
    pub = await publish_passport(
        db_session,
        sample_building.id,
        {
            "contract_version_id": contract.id,
            "audience_type": "authority",
            "publication_type": "authority_pack",
            "content_hash": "abc123" * 10 + "abcd",
            "delivery_state": "published",
        },
    )
    assert pub.id is not None
    assert pub.building_id == sample_building.id
    assert pub.delivery_state == "published"


@pytest.mark.asyncio
async def test_get_publications(db_session, sample_building):
    contract = await _create_contract(db_session)
    await publish_passport(
        db_session,
        sample_building.id,
        {
            "contract_version_id": contract.id,
            "audience_type": "authority",
            "publication_type": "diagnostic_report",
            "content_hash": "hash1" + "0" * 59,
            "delivery_state": "published",
        },
    )
    pubs = await get_publications(db_session, sample_building.id)
    assert len(pubs) == 1


@pytest.mark.asyncio
async def test_record_import(db_session, sample_building):
    receipt = await record_import(
        db_session,
        {
            "building_id": sample_building.id,
            "source_system": "batiscan-legacy",
            "contract_code": "diag_v1",
            "contract_version": 1,
            "content_hash": "importhash" + "0" * 54,
            "status": "received",
        },
    )
    assert receipt.id is not None
    assert receipt.source_system == "batiscan-legacy"


@pytest.mark.asyncio
async def test_get_imports(db_session, sample_building):
    await record_import(
        db_session,
        {
            "building_id": sample_building.id,
            "source_system": "external",
            "contract_code": "pack_v1",
            "contract_version": 1,
            "content_hash": "hash" + "0" * 60,
        },
    )
    imports = await get_imports(db_session, sample_building.id)
    assert len(imports) == 1


# ============================================================
# Partner Trust Service Tests
# ============================================================


@pytest.mark.asyncio
async def test_record_signal(db_session):
    org = await _create_org(db_session)
    signal = await record_signal(
        db_session,
        {
            "partner_org_id": org.id,
            "signal_type": "delivery_success",
            "value": 1.0,
            "notes": "On-time delivery",
        },
    )
    assert signal.id is not None
    assert signal.signal_type == "delivery_success"


@pytest.mark.asyncio
async def test_evaluate_partner_no_signals(db_session):
    org = await _create_org(db_session)
    profile = await evaluate_partner(db_session, org.id)
    assert profile.overall_trust_level == "unknown"
    assert profile.signal_count == 0


@pytest.mark.asyncio
async def test_evaluate_partner_strong(db_session):
    org = await _create_org(db_session)
    for stype in ["delivery_success", "evidence_clean", "response_fast"]:
        await record_signal(db_session, {"partner_org_id": org.id, "signal_type": stype})
    profile = await evaluate_partner(db_session, org.id)
    assert profile.overall_trust_level == "strong"
    assert profile.signal_count == 3
    assert profile.delivery_reliability_score == 1.0


@pytest.mark.asyncio
async def test_evaluate_partner_weak(db_session):
    org = await _create_org(db_session)
    for stype in ["delivery_failure", "evidence_rejected", "response_slow"]:
        await record_signal(db_session, {"partner_org_id": org.id, "signal_type": stype})
    profile = await evaluate_partner(db_session, org.id)
    assert profile.overall_trust_level == "weak"
    assert profile.delivery_reliability_score == 0.0


@pytest.mark.asyncio
async def test_evaluate_partner_mixed(db_session):
    org = await _create_org(db_session)
    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "delivery_success"})
    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "delivery_failure"})
    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "evidence_clean"})
    profile = await evaluate_partner(db_session, org.id)
    # delivery = 0.5, evidence = 1.0 => avg = 0.75 => adequate
    assert profile.overall_trust_level == "adequate"


@pytest.mark.asyncio
async def test_evaluate_partner_upserts(db_session):
    org = await _create_org(db_session)
    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "delivery_success"})
    profile1 = await evaluate_partner(db_session, org.id)
    assert profile1.overall_trust_level == "strong"

    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "delivery_failure"})
    profile2 = await evaluate_partner(db_session, org.id)
    # Same profile row, updated
    assert profile2.id == profile1.id
    assert profile2.signal_count == 2


@pytest.mark.asyncio
async def test_get_profile_not_found(db_session):
    result = await get_profile(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_profiles(db_session):
    org = await _create_org(db_session)
    await evaluate_partner(db_session, org.id)
    profiles = await list_profiles(db_session)
    assert len(profiles) == 1


@pytest.mark.asyncio
async def test_routing_hint_no_profile(db_session):
    hint = await get_routing_hint(db_session, uuid.uuid4(), "delivery")
    assert hint["recommendation"] == "review"
    assert hint["overall_trust_level"] == "unknown"


@pytest.mark.asyncio
async def test_routing_hint_strong(db_session):
    org = await _create_org(db_session)
    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "delivery_success"})
    await evaluate_partner(db_session, org.id)
    hint = await get_routing_hint(db_session, org.id, "delivery")
    assert hint["recommendation"] == "preferred"


@pytest.mark.asyncio
async def test_routing_hint_weak(db_session):
    org = await _create_org(db_session)
    await record_signal(db_session, {"partner_org_id": org.id, "signal_type": "delivery_failure"})
    await evaluate_partner(db_session, org.id)
    hint = await get_routing_hint(db_session, org.id, "delivery")
    assert hint["recommendation"] == "avoid"


# ============================================================
# API Route Tests — Exchange
# ============================================================


@pytest.mark.asyncio
async def test_api_list_contracts(client, auth_headers, db_session):
    await _create_contract(db_session, "api_test_v1")
    await db_session.commit()
    resp = await client.get("/api/v1/exchange/contracts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_api_get_active_contract(client, auth_headers, db_session):
    await _create_contract(db_session, "lookup_v1")
    await db_session.commit()
    resp = await client.get("/api/v1/exchange/contracts/lookup_v1/active", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["contract_code"] == "lookup_v1"


@pytest.mark.asyncio
async def test_api_get_active_contract_404(client, auth_headers):
    resp = await client.get("/api/v1/exchange/contracts/missing/active", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_publish_passport(client, auth_headers, db_session, sample_building):
    contract = await _create_contract(db_session)
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/passport-publications",
        headers=auth_headers,
        json={
            "contract_version_id": str(contract.id),
            "audience_type": "authority",
            "publication_type": "authority_pack",
            "content_hash": "apihash" + "0" * 58,
            "delivery_state": "published",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["delivery_state"] == "published"


@pytest.mark.asyncio
async def test_api_list_publications(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/passport-publications",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_record_import(client, auth_headers, sample_building):
    resp = await client.post(
        "/api/v1/passport-import-receipts",
        headers=auth_headers,
        json={
            "building_id": str(sample_building.id),
            "source_system": "external-sys",
            "contract_code": "pack_v1",
            "contract_version": 1,
            "content_hash": "importapi" + "0" * 55,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["source_system"] == "external-sys"


@pytest.mark.asyncio
async def test_api_list_imports(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/import-receipts",
        headers=auth_headers,
    )
    assert resp.status_code == 200


# ============================================================
# API Route Tests — Partner Trust
# ============================================================


@pytest.mark.asyncio
async def test_api_list_profiles(client, auth_headers):
    resp = await client.get("/api/v1/partner-trust/profiles", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_get_profile_404(client, auth_headers):
    resp = await client.get(f"/api/v1/partner-trust/profiles/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_record_signal_and_auto_evaluate(client, auth_headers, db_session):
    org = await _create_org(db_session)
    await db_session.commit()
    resp = await client.post(
        "/api/v1/partner-trust/signals",
        headers=auth_headers,
        json={
            "partner_org_id": str(org.id),
            "signal_type": "delivery_success",
            "value": 1.0,
        },
    )
    assert resp.status_code == 201
    # Profile should now exist
    resp2 = await client.get(f"/api/v1/partner-trust/profiles/{org.id}", headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["overall_trust_level"] == "strong"


@pytest.mark.asyncio
async def test_api_routing_hint(client, auth_headers):
    resp = await client.get(
        f"/api/v1/partner-trust/profiles/{uuid.uuid4()}/routing-hint?workflow_type=delivery",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["recommendation"] == "review"
