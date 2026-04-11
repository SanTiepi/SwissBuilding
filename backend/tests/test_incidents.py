"""Tests for the Incident & Damage Memory service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.organization import Organization
from app.models.user import User
from app.services.incident_service import (
    add_damage_observation,
    create_incident,
    get_building_incidents,
    get_incident_risk_profile,
    get_insurer_incident_summary,
    get_recurring_incidents,
    resolve_incident,
    update_incident,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org Incidents",
        type="diagnostic_lab",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="incident-tester@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Incident",
        last_name="Tester",
        role="admin",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def building(db_session, org, org_user):
    b = Building(
        id=uuid.uuid4(),
        official_id="INC-001",
        address="Rue du Test 1",
        city="Lausanne",
        canton="VD",
        postal_code="1000",
        building_type="residential",
        created_by=org_user.id,
        organization_id=org.id,
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
def auth_header(org_user):
    from datetime import timedelta

    from jose import jwt

    payload = {
        "sub": str(org_user.id),
        "email": org_user.email,
        "role": org_user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestIncidentService:
    async def test_create_incident(self, db_session, building, org):
        incident = await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            title="Fuite d'eau au 2e étage",
            severity="moderate",
        )
        await db_session.commit()
        assert incident.id is not None
        assert incident.incident_type == "leak"
        assert incident.status == "reported"
        assert incident.severity == "moderate"

    async def test_update_incident(self, db_session, building, org):
        incident = await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="mold",
            title="Moisissure salle de bain",
        )
        await db_session.commit()

        updated = await update_incident(
            db_session,
            incident.id,
            status="investigating",
            cause_category="wear",
        )
        await db_session.commit()
        assert updated.status == "investigating"
        assert updated.cause_category == "wear"

    async def test_resolve_incident(self, db_session, building, org):
        incident = await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="breakage",
            title="Vitre cassée entrée",
            severity="minor",
        )
        await db_session.commit()

        resolved = await resolve_incident(
            db_session,
            incident.id,
            "Vitre remplacée par vitrier",
            repair_cost_chf=450.0,
        )
        await db_session.commit()
        assert resolved.status == "resolved"
        assert resolved.resolved_at is not None
        assert resolved.repair_cost_chf == 450.0

    async def test_get_building_incidents(self, db_session, building, org):
        for i in range(3):
            await create_incident(
                db_session,
                building.id,
                org.id,
                incident_type="leak" if i < 2 else "fire",
                title=f"Incident {i}",
            )
        await db_session.commit()

        items, total = await get_building_incidents(db_session, building.id)
        assert total == 3
        assert len(items) == 3

        # Filter by type
        _items2, total2 = await get_building_incidents(db_session, building.id, incident_type="leak")
        assert total2 == 2

    async def test_get_recurring_incidents(self, db_session, building, org):
        inc1 = await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            title="Fuite récurrente",
            recurring=True,
        )
        await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            title="Fuite récurrente 2",
            recurring=True,
            previous_incident_id=inc1.id,
        )
        await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="fire",
            title="Non récurrent",
        )
        await db_session.commit()

        recurring = await get_recurring_incidents(db_session, building.id)
        assert len(recurring) == 2

    async def test_add_damage_observation(self, db_session, building, org):
        incident = await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="flooding",
            title="Inondation sous-sol",
        )
        await db_session.commit()

        obs = await add_damage_observation(
            db_session,
            building.id,
            damage_type="stain",
            location_description="Mur nord sous-sol",
            severity="functional",
            progression="slow",
            incident_id=incident.id,
        )
        await db_session.commit()
        assert obs.id is not None
        assert obs.damage_type == "stain"
        assert obs.incident_id == incident.id

    async def test_damage_observation_standalone(self, db_session, building):
        obs = await add_damage_observation(
            db_session,
            building.id,
            damage_type="crack",
            location_description="Façade est, 3e étage",
            severity="structural",
            progression="slow",
        )
        await db_session.commit()
        assert obs.incident_id is None

    async def test_incident_risk_profile(self, db_session, building, org):
        now = datetime.now(UTC)
        await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            title="Fuite 1",
            severity="minor",
            discovered_at=now - timedelta(days=30),
        )
        inc2 = await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            title="Fuite 2",
            severity="major",
            discovered_at=now - timedelta(days=15),
            recurring=True,
            repair_cost_chf=2000.0,
        )
        await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="fire",
            title="Incendie",
            severity="critical",
            discovered_at=now - timedelta(days=5),
        )
        await db_session.commit()

        # Resolve one
        await resolve_incident(db_session, inc2.id, "Réparé", repair_cost_chf=2000.0)
        await db_session.commit()

        profile = await get_incident_risk_profile(db_session, building.id)
        assert profile["total_incidents"] == 3
        assert profile["unresolved_count"] == 2
        assert profile["recurring_count"] == 1
        assert profile["total_repair_cost_chf"] == 2000.0
        assert len(profile["by_type"]) == 2
        assert profile["most_common_type"] == "leak"

    async def test_insurer_incident_summary(self, db_session, building, org):
        await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="flooding",
            title="Inondation",
            severity="critical",
            insurance_claim_filed=True,
            occupant_impact=True,
        )
        await create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            title="Fuite",
            severity="minor",
            recurring=True,
        )
        await db_session.commit()

        summary = await get_insurer_incident_summary(db_session, building.id)
        assert summary["total_incidents"] == 2
        assert summary["claims_filed"] == 1
        assert summary["unresolved_incidents"] == 2
        assert summary["recurring_risks"] == 1
        assert summary["occupant_impact_incidents"] == 1
        assert summary["critical_incidents"] == 1
        assert summary["risk_rating"] in ("moderate", "elevated", "high")

    async def test_insurer_risk_rating_low(self, db_session, building, org):
        summary = await get_insurer_incident_summary(db_session, building.id)
        assert summary["risk_rating"] == "low"
        assert summary["total_incidents"] == 0


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


class TestIncidentAPI:
    async def test_create_incident_api(self, client: AsyncClient, auth_header, building):
        resp = await client.post(
            f"/api/v1/buildings/{building.id}/incidents",
            json={
                "incident_type": "leak",
                "title": "Fuite toiture",
                "severity": "moderate",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["incident_type"] == "leak"
        assert data["status"] == "reported"

    async def test_list_incidents_api(self, client: AsyncClient, auth_header, building):
        # Create first
        await client.post(
            f"/api/v1/buildings/{building.id}/incidents",
            json={"incident_type": "mold", "title": "Moisissure"},
            headers=auth_header,
        )
        resp = await client.get(
            f"/api/v1/buildings/{building.id}/incidents",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_update_incident_api(self, client: AsyncClient, auth_header, building):
        create_resp = await client.post(
            f"/api/v1/buildings/{building.id}/incidents",
            json={"incident_type": "breakage", "title": "Porte cassée"},
            headers=auth_header,
        )
        incident_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/incidents/{incident_id}",
            json={"status": "investigating", "cause_category": "accident"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "investigating"

    async def test_resolve_incident_api(self, client: AsyncClient, auth_header, building):
        create_resp = await client.post(
            f"/api/v1/buildings/{building.id}/incidents",
            json={"incident_type": "fire", "title": "Petit incendie", "severity": "major"},
            headers=auth_header,
        )
        incident_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/incidents/{incident_id}/resolve",
            json={"resolution_description": "Dégâts nettoyés", "repair_cost_chf": 5000.0},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"
        assert resp.json()["repair_cost_chf"] == 5000.0

    async def test_recurring_incidents_api(self, client: AsyncClient, auth_header, building):
        await client.post(
            f"/api/v1/buildings/{building.id}/incidents",
            json={"incident_type": "leak", "title": "Fuite récurrente", "recurring": True},
            headers=auth_header,
        )
        resp = await client.get(
            f"/api/v1/buildings/{building.id}/incidents/recurring",
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_create_damage_observation_api(self, client: AsyncClient, auth_header, building):
        resp = await client.post(
            f"/api/v1/buildings/{building.id}/damage-observations",
            json={
                "damage_type": "crack",
                "location_description": "Façade sud",
                "severity": "structural",
                "progression": "slow",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["damage_type"] == "crack"
        assert data["severity"] == "structural"

    async def test_incident_risk_profile_api(self, client: AsyncClient, auth_header, building):
        resp = await client.get(
            f"/api/v1/buildings/{building.id}/incident-risk-profile",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_incidents" in data
        assert "by_type" in data

    async def test_insurer_incident_summary_api(self, client: AsyncClient, auth_header, building):
        resp = await client.get(
            f"/api/v1/buildings/{building.id}/insurer-incident-summary",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_rating" in data
        assert "claims_filed" in data

    async def test_create_incident_404_building(self, client: AsyncClient, auth_header):
        resp = await client.post(
            f"/api/v1/buildings/{uuid.uuid4()}/incidents",
            json={"incident_type": "leak", "title": "Test"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_update_incident_404(self, client: AsyncClient, auth_header):
        resp = await client.put(
            f"/api/v1/incidents/{uuid.uuid4()}",
            json={"status": "investigating"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_resolve_incident_404(self, client: AsyncClient, auth_header):
        resp = await client.post(
            f"/api/v1/incidents/{uuid.uuid4()}/resolve",
            json={"resolution_description": "Test"},
            headers=auth_header,
        )
        assert resp.status_code == 404
