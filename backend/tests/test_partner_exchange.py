"""BatiConnect — Partner Exchange Contract tests.

Covers: contract CRUD, access validation, submission validation,
trust level requirements, exchange event audit trail.
"""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_contract import PartnerExchangeContract
from app.models.organization import Organization
from app.models.partner_trust import PartnerTrustProfile
from app.services.partner_gateway_service import (
    create_contract,
    get_active_contracts,
    get_contract,
    get_exchange_history,
    list_contracts,
    record_exchange_event,
    update_contract,
    validate_partner_access,
    validate_submission,
)

# ============================================================
# Helpers
# ============================================================


async def _make_org(db: AsyncSession, name: str = "Test Org") -> Organization:
    org = Organization(id=uuid.uuid4(), name=name, type="diagnostic_lab")
    db.add(org)
    await db.flush()
    return org


async def _make_contract(
    db: AsyncSession,
    partner_org: Organization,
    our_org: Organization,
    *,
    status: str = "active",
    operations: list[str] | None = None,
    api_access_level: str = "read_only",
    minimum_trust_level: str = "unknown",
    data_sharing_scope: str = "building_specific",
    start_date: date | None = None,
    end_date: date | None = None,
    allowed_endpoints: list[str] | None = None,
    contract_type: str = "data_provider",
) -> PartnerExchangeContract:
    data = {
        "partner_org_id": partner_org.id,
        "our_org_id": our_org.id,
        "contract_type": contract_type,
        "allowed_operations": operations or ["submit_diagnostics"],
        "api_access_level": api_access_level,
        "allowed_endpoints": allowed_endpoints,
        "data_sharing_scope": data_sharing_scope,
        "redaction_profile": "none",
        "minimum_trust_level": minimum_trust_level,
        "status": status,
        "start_date": start_date or date.today(),
        "end_date": end_date,
    }
    return await create_contract(db, data)


async def _make_trust_profile(
    db: AsyncSession,
    org: Organization,
    trust_level: str = "adequate",
) -> PartnerTrustProfile:
    profile = PartnerTrustProfile(
        id=uuid.uuid4(),
        partner_org_id=org.id,
        overall_trust_level=trust_level,
        signal_count=5,
    )
    db.add(profile)
    await db.flush()
    return profile


# ============================================================
# Contract CRUD
# ============================================================


@pytest.mark.asyncio
async def test_create_contract(db: AsyncSession):
    partner = await _make_org(db, "Partner Lab")
    our = await _make_org(db, "Our Org")
    contract = await _make_contract(db, partner, our)

    assert contract.id is not None
    assert contract.partner_org_id == partner.id
    assert contract.our_org_id == our.id
    assert contract.contract_type == "data_provider"
    assert contract.status == "active"
    assert "submit_diagnostics" in contract.allowed_operations


@pytest.mark.asyncio
async def test_get_contract(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    created = await _make_contract(db, partner, our)

    fetched = await get_contract(db, created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_contract_not_found(db: AsyncSession):
    result = await get_contract(db, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_contract(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    contract = await _make_contract(db, partner, our, status="draft")

    updated = await update_contract(db, contract.id, {"status": "active"})
    assert updated is not None
    assert updated.status == "active"


@pytest.mark.asyncio
async def test_update_contract_not_found(db: AsyncSession):
    result = await update_contract(db, uuid.uuid4(), {"status": "active"})
    assert result is None


@pytest.mark.asyncio
async def test_list_contracts_all(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(db, partner, our, status="active")
    await _make_contract(db, partner, our, status="draft")

    all_contracts = await list_contracts(db)
    assert len(all_contracts) >= 2


@pytest.mark.asyncio
async def test_list_contracts_filter_status(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(db, partner, our, status="active")
    await _make_contract(db, partner, our, status="suspended")

    active = await list_contracts(db, status_filter="active")
    assert all(c.status == "active" for c in active)


@pytest.mark.asyncio
async def test_get_active_contracts(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(db, partner, our, status="active")
    await _make_contract(db, partner, our, status="draft")

    active = await get_active_contracts(db, partner_org_id=partner.id)
    assert len(active) >= 1
    assert all(c.status == "active" for c in active)


# ============================================================
# Access Validation
# ============================================================


@pytest.mark.asyncio
async def test_access_allowed(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(db, partner, our, operations=["submit_diagnostics"], minimum_trust_level="unknown")

    result = await validate_partner_access(db, partner.id, "submit_diagnostics")
    assert result["allowed"] is True
    assert result["contract_id"] is not None


@pytest.mark.asyncio
async def test_access_denied_no_contract(db: AsyncSession):
    result = await validate_partner_access(db, uuid.uuid4(), "submit_diagnostics")
    assert result["allowed"] is False
    assert "No active" in result["reason"]


@pytest.mark.asyncio
async def test_access_denied_operation_not_allowed(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(db, partner, our, operations=["receive_packs"])

    result = await validate_partner_access(db, partner.id, "submit_diagnostics")
    assert result["allowed"] is False
    assert "No contract allows" in result["reason"]


@pytest.mark.asyncio
async def test_access_denied_expired_contract(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(
        db,
        partner,
        our,
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=1),
    )

    result = await validate_partner_access(db, partner.id, "submit_diagnostics")
    assert result["allowed"] is False
    assert "expired" in result["reason"]


@pytest.mark.asyncio
async def test_access_denied_trust_too_low(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    # Require strong trust but partner has weak
    await _make_trust_profile(db, partner, "weak")
    await _make_contract(db, partner, our, minimum_trust_level="strong")

    result = await validate_partner_access(db, partner.id, "submit_diagnostics")
    assert result["allowed"] is False
    assert "trust level" in result["reason"]


@pytest.mark.asyncio
async def test_access_allowed_with_adequate_trust(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_trust_profile(db, partner, "strong")
    await _make_contract(db, partner, our, minimum_trust_level="adequate")

    result = await validate_partner_access(db, partner.id, "submit_diagnostics")
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_access_denied_endpoint_not_in_whitelist(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(
        db,
        partner,
        our,
        operations=["submit_diagnostics"],
        allowed_endpoints=["/api/v1/diagnostics"],
    )

    result = await validate_partner_access(db, partner.id, "submit_diagnostics", endpoint="/api/v1/buildings")
    assert result["allowed"] is False


@pytest.mark.asyncio
async def test_access_allowed_endpoint_in_whitelist(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(
        db,
        partner,
        our,
        operations=["submit_diagnostics"],
        allowed_endpoints=["/api/v1/diagnostics"],
    )

    result = await validate_partner_access(db, partner.id, "submit_diagnostics", endpoint="/api/v1/diagnostics")
    assert result["allowed"] is True


# ============================================================
# Submission Validation
# ============================================================


@pytest.mark.asyncio
async def test_submission_valid(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(db, partner, our, operations=["submit_diagnostics"], data_sharing_scope="building_specific")

    result = await validate_submission(db, partner.id, "diagnostics", {"type": "asbestos_report"})
    assert result["valid"] is True
    assert result["contract_id"] is not None


@pytest.mark.asyncio
async def test_submission_denied_no_contract(db: AsyncSession):
    result = await validate_submission(db, uuid.uuid4(), "diagnostics", {"type": "asbestos_report"})
    assert result["valid"] is False
    assert len(result["issues"]) > 0


@pytest.mark.asyncio
async def test_submission_denied_data_sharing_none(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_contract(
        db,
        partner,
        our,
        operations=["submit_diagnostics"],
        data_sharing_scope="none",
    )

    result = await validate_submission(db, partner.id, "diagnostics", {"type": "asbestos_report"})
    assert result["valid"] is False
    assert any(i["check"] == "data_sharing_scope" for i in result["issues"])


# ============================================================
# Exchange Event Audit Trail
# ============================================================


@pytest.mark.asyncio
async def test_exchange_event_recorded_on_access(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    contract = await _make_contract(db, partner, our, operations=["submit_diagnostics"])

    await validate_partner_access(db, partner.id, "submit_diagnostics")

    events = await get_exchange_history(db, contract.id)
    # At least creation + access_granted
    event_types = [e.event_type for e in events]
    assert "contract_created" in event_types
    assert "access_granted" in event_types


@pytest.mark.asyncio
async def test_exchange_event_recorded_on_denied(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    await _make_trust_profile(db, partner, "weak")
    contract = await _make_contract(db, partner, our, operations=["submit_diagnostics"], minimum_trust_level="strong")

    await validate_partner_access(db, partner.id, "submit_diagnostics")

    events = await get_exchange_history(db, contract.id)
    event_types = [e.event_type for e in events]
    assert "access_denied" in event_types


@pytest.mark.asyncio
async def test_record_custom_exchange_event(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    contract = await _make_contract(db, partner, our)

    event = await record_exchange_event(db, contract.id, "custom_event", {"note": "test event"})
    assert event.event_type == "custom_event"
    assert event.detail["note"] == "test event"

    history = await get_exchange_history(db, contract.id)
    assert any(e.event_type == "custom_event" for e in history)


# ============================================================
# Contract lifecycle
# ============================================================


@pytest.mark.asyncio
async def test_status_change_records_event(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    contract = await _make_contract(db, partner, our, status="draft")

    await update_contract(db, contract.id, {"status": "active"})

    events = await get_exchange_history(db, contract.id)
    status_events = [e for e in events if e.event_type == "status_changed"]
    assert len(status_events) >= 1
    assert status_events[0].detail["new_status"] == "active"


@pytest.mark.asyncio
async def test_suspended_contract_denies_access(db: AsyncSession):
    partner = await _make_org(db, "Partner")
    our = await _make_org(db, "Ours")
    contract = await _make_contract(db, partner, our, status="active")

    # Suspend the contract
    await update_contract(db, contract.id, {"status": "suspended"})

    result = await validate_partner_access(db, partner.id, "submit_diagnostics")
    assert result["allowed"] is False
