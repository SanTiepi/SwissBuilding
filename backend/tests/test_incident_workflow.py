"""Tests for the incident workflow service (Programme D — Incidents)."""

import uuid

import pytest
from sqlalchemy import select

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.incident import IncidentEpisode
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.services.incident_workflow_service import (
    auto_generate_obligation,
    create_incident,
    escalate_incident,
    get_incident_patterns,
    resolve_incident,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db.add(org)
    await db.flush()
    return org


async def _create_building(db, admin_user, org):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        organization_id=org.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


# ---------------------------------------------------------------------------
# Tests: create_incident
# ---------------------------------------------------------------------------


class TestCreateIncident:
    async def test_create_basic_incident(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={
                "incident_type": "leak",
                "title": "Water leak in basement",
                "severity": "moderate",
            },
            created_by_id=admin_user.id,
        )

        assert incident.id is not None
        assert incident.incident_type == "leak"
        assert incident.title == "Water leak in basement"
        assert incident.severity == "moderate"
        assert incident.status == "reported"
        assert incident.building_id == building.id

    async def test_create_incident_generates_action_item(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={
                "incident_type": "fire",
                "title": "Kitchen fire",
                "severity": "critical",
            },
        )

        result = await db_session.execute(select(ActionItem).where(ActionItem.building_id == building.id))
        actions = result.scalars().all()
        assert len(actions) >= 1
        investigation = [a for a in actions if "Investigate" in a.title]
        assert len(investigation) == 1
        assert investigation[0].priority == "critical"

    async def test_create_incident_defaults(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "vandalism", "title": "Graffiti on facade"},
        )

        assert incident.severity == "minor"
        assert incident.cause_category == "unknown"
        assert incident.status == "reported"


# ---------------------------------------------------------------------------
# Tests: escalate_incident
# ---------------------------------------------------------------------------


class TestEscalateIncident:
    async def test_escalate_severity(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "leak", "title": "Roof leak", "severity": "minor"},
        )

        updated = await escalate_incident(db_session, incident.id, "major")
        assert updated.severity == "major"

    async def test_escalate_to_critical_sets_investigating(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "fire", "title": "Electrical fire", "severity": "minor"},
        )

        updated = await escalate_incident(db_session, incident.id, "critical")
        assert updated.severity == "critical"
        assert updated.status == "investigating"

    async def test_escalate_invalid_lower_severity(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "leak", "title": "Pipe burst", "severity": "major"},
        )

        with pytest.raises(ValueError, match="must be higher"):
            await escalate_incident(db_session, incident.id, "minor")

    async def test_escalate_same_severity_rejected(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "leak", "title": "Leak", "severity": "moderate"},
        )

        with pytest.raises(ValueError, match="must be higher"):
            await escalate_incident(db_session, incident.id, "moderate")

    async def test_escalate_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await escalate_incident(db_session, uuid.uuid4(), "critical")


# ---------------------------------------------------------------------------
# Tests: resolve_incident
# ---------------------------------------------------------------------------


class TestResolveIncident:
    async def test_resolve_basic(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "breakage", "title": "Broken window", "severity": "minor"},
        )

        resolved = await resolve_incident(
            db_session,
            incident.id,
            {
                "response_description": "Window replaced",
                "repair_cost_chf": 450.0,
            },
        )

        assert resolved.status == "resolved"
        assert resolved.resolved_at is not None
        assert resolved.response_description == "Window replaced"
        assert resolved.repair_cost_chf == 450.0

    async def test_resolve_already_resolved(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "breakage", "title": "Broken door", "severity": "minor"},
        )
        await resolve_incident(db_session, incident.id, {})

        with pytest.raises(ValueError, match="already resolved"):
            await resolve_incident(db_session, incident.id, {})

    async def test_resolve_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await resolve_incident(db_session, uuid.uuid4(), {})


# ---------------------------------------------------------------------------
# Tests: auto_generate_obligation
# ---------------------------------------------------------------------------


class TestAutoGenerateObligation:
    async def test_flooding_creates_obligation(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "flooding", "title": "Basement flood", "severity": "major"},
        )

        result = await db_session.execute(
            select(Obligation).where(
                Obligation.building_id == building.id,
                Obligation.linked_entity_type == "incident",
            )
        )
        obligation = result.scalar_one_or_none()
        assert obligation is not None
        assert obligation.obligation_type == "structural_inspection"
        assert "Post-flood" in obligation.title

    async def test_fire_creates_obligation(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "fire", "title": "Garage fire", "severity": "critical"},
        )

        result = await db_session.execute(select(Obligation).where(Obligation.building_id == building.id))
        obligations = result.scalars().all()
        fire_obligs = [o for o in obligations if o.obligation_type == "fire_safety_review"]
        assert len(fire_obligs) == 1

    async def test_no_obligation_for_vandalism(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "vandalism", "title": "Broken mailbox", "severity": "minor"},
        )

        result = await db_session.execute(
            select(Obligation).where(
                Obligation.building_id == building.id,
                Obligation.linked_entity_type == "incident",
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_obligation_idempotent(self, db_session, admin_user):
        """Calling auto_generate_obligation twice should not duplicate."""
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        incident = IncidentEpisode(
            id=uuid.uuid4(),
            building_id=building.id,
            organization_id=org.id,
            incident_type="mold",
            title="Mold in bathroom",
            severity="moderate",
            status="reported",
        )
        db_session.add(incident)
        await db_session.flush()

        obl1 = await auto_generate_obligation(db_session, incident)
        await db_session.flush()
        obl2 = await auto_generate_obligation(db_session, incident)

        assert obl1 is not None
        assert obl2 is None  # Idempotent: second call returns None


# ---------------------------------------------------------------------------
# Tests: lifecycle (create → escalate → resolve)
# ---------------------------------------------------------------------------


class TestIncidentLifecycle:
    async def test_full_lifecycle(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        # Create
        incident = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "subsidence", "title": "Ground settlement", "severity": "moderate"},
        )
        assert incident.status == "reported"

        # Escalate
        incident = await escalate_incident(db_session, incident.id, "critical")
        assert incident.severity == "critical"
        assert incident.status == "investigating"

        # Resolve
        incident = await resolve_incident(
            db_session,
            incident.id,
            {
                "response_description": "Foundation reinforced",
                "repair_cost_chf": 25000.0,
            },
        )
        assert incident.status == "resolved"
        assert incident.resolved_at is not None


# ---------------------------------------------------------------------------
# Tests: recurring pattern detection
# ---------------------------------------------------------------------------


class TestIncidentPatterns:
    async def test_recurring_detection(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        # Create first leak
        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "leak", "title": "Leak 1", "severity": "minor"},
        )

        # Create second leak — should be marked recurring
        incident2 = await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "leak", "title": "Leak 2", "severity": "minor"},
        )
        assert incident2.recurring is True
        assert incident2.previous_incident_id is not None

    async def test_patterns_endpoint(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "leak", "title": "Leak", "severity": "minor"},
        )
        await create_incident(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            data={"incident_type": "mold", "title": "Mold", "severity": "critical"},
        )

        patterns = await get_incident_patterns(db_session, building.id)
        assert patterns["total_incidents"] == 2
        assert patterns["type_counts"]["leak"] == 1
        assert patterns["type_counts"]["mold"] == 1
        assert "mold" in patterns["high_risk_types"]  # critical severity

    async def test_empty_patterns(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)

        patterns = await get_incident_patterns(db_session, building.id)
        assert patterns["total_incidents"] == 0
        assert patterns["avg_resolution_days"] is None
