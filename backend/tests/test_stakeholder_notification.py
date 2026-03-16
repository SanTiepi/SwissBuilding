"""Tests for stakeholder notification service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.stakeholder_notification_service import (
    generate_authority_report,
    generate_diagnostician_brief,
    generate_owner_briefing,
    get_stakeholder_digest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db, name="TestOrg", org_type="property_management"):
    org = Organization(id=uuid.uuid4(), name=name, type=org_type)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user(db, org=None, role="admin", email=None):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=email or f"{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org.id if org else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building(db, user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(**defaults)
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


async def _create_diagnostic(db, building, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building.id,
        "diagnostic_type": "asbestos",
        "status": "draft",
    }
    defaults.update(kwargs)
    diag = Diagnostic(**defaults)
    db.add(diag)
    await db.commit()
    await db.refresh(diag)
    return diag


async def _create_sample(db, diagnostic, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic.id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "threshold_exceeded": False,
    }
    defaults.update(kwargs)
    sample = Sample(**defaults)
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


async def _create_risk_score(db, building, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building.id,
        "overall_risk_level": "medium",
        "asbestos_probability": 0.3,
        "pcb_probability": 0.1,
        "lead_probability": 0.1,
        "hap_probability": 0.05,
        "radon_probability": 0.05,
    }
    defaults.update(kwargs)
    score = BuildingRiskScore(**defaults)
    db.add(score)
    await db.commit()
    await db.refresh(score)
    return score


async def _create_action(db, building, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building.id,
        "source_type": "diagnostic",
        "action_type": "remediation",
        "title": "Remove asbestos",
        "priority": "high",
        "status": "open",
    }
    defaults.update(kwargs)
    action = ActionItem(**defaults)
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def _create_zone(db, building, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building.id,
        "zone_type": "floor",
        "name": "Ground Floor",
    }
    defaults.update(kwargs)
    zone = Zone(**defaults)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


# ---------------------------------------------------------------------------
# FN1: Owner briefing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owner_briefing_building_not_found(db_session):
    result = await generate_owner_briefing(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_owner_briefing_no_data(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    result = await generate_owner_briefing(building.id, db_session)
    assert result is not None
    assert result.building_id == building.id
    assert result.urgency_level == "routine"
    assert result.cost_forecast == 0.0
    assert "No risk assessment" in result.risk_overview


@pytest.mark.asyncio
async def test_owner_briefing_with_risk(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    await _create_risk_score(db_session, building, asbestos_probability=0.8, overall_risk_level="critical")
    result = await generate_owner_briefing(building.id, db_session)
    assert result is not None
    assert "asbestos" in result.risk_overview.lower()
    assert any(d.priority == "critical" for d in result.recommended_decisions)


@pytest.mark.asyncio
async def test_owner_briefing_with_cost(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building, status="completed")
    await _create_sample(db_session, diag, threshold_exceeded=True, concentration=5.0, unit="%")
    result = await generate_owner_briefing(building.id, db_session)
    assert result is not None
    assert result.cost_forecast > 0.0


@pytest.mark.asyncio
async def test_owner_briefing_urgency_critical(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    await _create_risk_score(
        db_session,
        building,
        asbestos_probability=0.9,
        pcb_probability=0.8,
        overall_risk_level="critical",
    )
    result = await generate_owner_briefing(building.id, db_session)
    assert result is not None
    assert result.urgency_level in ("urgent", "critical")


@pytest.mark.asyncio
async def test_owner_briefing_with_obligations(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
    await _create_action(db_session, building, due_date=tomorrow, title="Inspect roof")
    result = await generate_owner_briefing(building.id, db_session)
    assert result is not None
    assert len(result.upcoming_obligations) == 1
    assert result.upcoming_obligations[0].title == "Inspect roof"


@pytest.mark.asyncio
async def test_owner_briefing_overdue_actions(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    past = (datetime.now(UTC) - timedelta(days=30)).date()
    await _create_action(db_session, building, due_date=past, title="Overdue task")
    result = await generate_owner_briefing(building.id, db_session)
    assert result is not None
    assert result.urgency_level in ("urgent", "critical")
    assert any("overdue" in d.title.lower() for d in result.recommended_decisions)


# ---------------------------------------------------------------------------
# FN2: Diagnostician brief tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostician_brief_building_not_found(db_session):
    result = await generate_diagnostician_brief(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_diagnostician_brief_no_data(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    result = await generate_diagnostician_brief(building.id, db_session)
    assert result is not None
    assert result.building_id == building.id
    assert len(result.pending_analyses) == 0
    assert result.estimated_fieldwork_hours >= 2.0


@pytest.mark.asyncio
async def test_diagnostician_brief_pending_analyses(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    await _create_diagnostic(db_session, building, status="draft", diagnostic_type="asbestos")
    await _create_diagnostic(db_session, building, status="in_progress", diagnostic_type="pcb")
    result = await generate_diagnostician_brief(building.id, db_session)
    assert result is not None
    assert len(result.pending_analyses) == 2


@pytest.mark.asyncio
async def test_diagnostician_brief_coverage_gaps(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    await _create_zone(db_session, building, name="Basement")
    diag = await _create_diagnostic(db_session, building, status="completed")
    await _create_sample(db_session, diag, pollutant_type="asbestos")
    result = await generate_diagnostician_brief(building.id, db_session)
    assert result is not None
    # Should have gaps for pollutants other than asbestos
    gap_pollutants = {g.pollutant_type for g in result.sample_coverage_gaps}
    assert "asbestos" not in gap_pollutants
    assert "pcb" in gap_pollutants


@pytest.mark.asyncio
async def test_diagnostician_brief_equipment_needed(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    result = await generate_diagnostician_brief(building.id, db_session)
    assert result is not None
    assert len(result.equipment_needed) > 0


@pytest.mark.asyncio
async def test_diagnostician_brief_priority_areas(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    await _create_risk_score(db_session, building, asbestos_probability=0.9, overall_risk_level="critical")
    result = await generate_diagnostician_brief(building.id, db_session)
    assert result is not None
    assert len(result.priority_areas) >= 1
    assert result.priority_areas[0].risk_level in ("high", "critical")


# ---------------------------------------------------------------------------
# FN3: Authority report tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authority_report_building_not_found(db_session):
    result = await generate_authority_report(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_authority_report_no_diagnostics(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    result = await generate_authority_report(building.id, db_session)
    assert result is not None
    assert "UNKNOWN" in result.compliance_status_summary
    assert result.building_identification.canton == "VD"


@pytest.mark.asyncio
async def test_authority_report_compliant(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, building, status="completed")
    await _create_sample(db_session, diag, pollutant_type="asbestos", threshold_exceeded=False)
    result = await generate_authority_report(building.id, db_session)
    assert result is not None
    assert "COMPLIANT" in result.compliance_status_summary
    assert len(result.regulatory_violations) == 0


@pytest.mark.asyncio
async def test_authority_report_violations(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user, egid=12345)
    diag = await _create_diagnostic(db_session, building, status="completed")
    await _create_sample(
        db_session,
        diag,
        pollutant_type="asbestos",
        threshold_exceeded=True,
        concentration=2.5,
        unit="%",
        location_detail="Pipe insulation 3rd floor",
        risk_level="critical",
    )
    result = await generate_authority_report(building.id, db_session)
    assert result is not None
    assert "NON-COMPLIANT" in result.compliance_status_summary
    assert len(result.regulatory_violations) == 1
    assert result.building_identification.egid == 12345
    assert "OTConst" in result.regulatory_violations[0].regulation


@pytest.mark.asyncio
async def test_authority_report_remediation_actions(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    await _create_action(db_session, building, title="Remove PCB joints", priority="critical")
    result = await generate_authority_report(building.id, db_session)
    assert result is not None
    assert len(result.required_remediation_actions) == 1
    assert result.required_remediation_actions[0].title == "Remove PCB joints"


@pytest.mark.asyncio
async def test_authority_report_deadline_overdue(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user)
    past = (datetime.now(UTC) - timedelta(days=10)).date()
    await _create_action(db_session, building, due_date=past)
    result = await generate_authority_report(building.id, db_session)
    assert result is not None
    assert "OVERDUE" in result.deadline_status


@pytest.mark.asyncio
async def test_authority_report_building_identification(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user, egid=99999, canton="GE")
    result = await generate_authority_report(building.id, db_session)
    assert result is not None
    assert result.building_identification.egid == 99999
    assert result.building_identification.canton == "GE"
    assert result.building_identification.address == "Rue Test 1"


# ---------------------------------------------------------------------------
# FN4: Stakeholder digest tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_digest_org_not_found(db_session):
    result = await get_stakeholder_digest(uuid.uuid4(), "owner", db_session)
    assert result is None


@pytest.mark.asyncio
async def test_digest_empty_org(db_session):
    org = await _create_org(db_session)
    result = await get_stakeholder_digest(org.id, "owner", db_session)
    assert result is not None
    assert result.total_buildings == 0
    assert result.total_notifications == 0


@pytest.mark.asyncio
async def test_digest_owner_role(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org=org)
    building = await _create_building(db_session, user)
    await _create_action(db_session, building, title="Fix roof")
    result = await get_stakeholder_digest(org.id, "owner", db_session)
    assert result is not None
    assert result.role == "owner"
    assert result.total_buildings == 1
    assert result.total_notifications >= 1


@pytest.mark.asyncio
async def test_digest_diagnostician_role(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org=org)
    building = await _create_building(db_session, user)
    await _create_diagnostic(db_session, building, status="draft")
    result = await get_stakeholder_digest(org.id, "diagnostician", db_session)
    assert result is not None
    assert result.role == "diagnostician"
    assert any(n.category == "fieldwork" for n in result.notifications)


@pytest.mark.asyncio
async def test_digest_authority_role_high_priority(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org=org)
    building = await _create_building(db_session, user)
    await _create_action(db_session, building, priority="critical", title="Urgent fix")
    result = await get_stakeholder_digest(org.id, "authority", db_session)
    assert result is not None
    assert result.role == "authority"
    assert any(n.priority == "critical" for n in result.notifications)


@pytest.mark.asyncio
async def test_digest_contractor_role(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org=org)
    building = await _create_building(db_session, user)
    await _create_action(db_session, building, action_type="remediation", title="Remove asbestos")
    result = await get_stakeholder_digest(org.id, "contractor", db_session)
    assert result is not None
    assert result.role == "contractor"
    assert any(n.category == "action" for n in result.notifications)


@pytest.mark.asyncio
async def test_digest_sorted_by_priority(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org=org)
    building = await _create_building(db_session, user)
    await _create_action(db_session, building, priority="low", title="Low priority task")
    await _create_action(db_session, building, priority="critical", title="Critical task")
    result = await get_stakeholder_digest(org.id, "owner", db_session)
    assert result is not None
    if len(result.notifications) >= 2:
        priorities = [n.priority for n in result.notifications]
        # critical should come before low
        assert priorities.index("critical") < priorities.index("low")


@pytest.mark.asyncio
async def test_digest_risk_notifications_for_owner(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org=org)
    building = await _create_building(db_session, user)
    await _create_risk_score(db_session, building, asbestos_probability=0.9, overall_risk_level="critical")
    result = await get_stakeholder_digest(org.id, "owner", db_session)
    assert result is not None
    assert any(n.category == "risk" for n in result.notifications)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_owner_briefing(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/stakeholder-owner-briefing",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "urgency_level" in data


@pytest.mark.asyncio
async def test_api_owner_briefing_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/stakeholder-owner-briefing",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_diagnostician_brief(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/stakeholder-diagnostician-brief",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "estimated_fieldwork_hours" in data


@pytest.mark.asyncio
async def test_api_authority_report(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/stakeholder-authority-report",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "compliance_status_summary" in data
    assert "building_identification" in data


@pytest.mark.asyncio
async def test_api_stakeholder_digest_invalid_role(client, auth_headers, db_session):
    org = await _create_org(db_session)
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/stakeholder-digest?role=invalid",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_stakeholder_digest_valid(client, auth_headers, db_session):
    org = await _create_org(db_session)
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/stakeholder-digest?role=owner",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "owner"
    assert "total_notifications" in data
