"""Tests for stakeholder dashboard service and API endpoints."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.contractor_acknowledgment import ContractorAcknowledgment
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.user import User
from app.services.stakeholder_dashboard_service import (
    get_authority_dashboard,
    get_contractor_dashboard,
    get_diagnostician_dashboard,
    get_owner_dashboard,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH = "$2b$12$LJ3m4ys3uz0MnTuMQJxXxOZ8RoTfNGF5.WEBYMBFOYPMwRLMGOLGG"


def _make_token(user: User) -> dict[str, str]:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


async def _create_user(db, *, role: str, email: str | None = None) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email or f"{role}-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH,
        first_name=role.capitalize(),
        last_name="Test",
        role=role,
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building(db, *, owner_id=None, created_by=None) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        owner_id=owner_id,
        created_by=created_by or uuid.uuid4(),
        status="active",
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


# ===========================================================================
# Service-level tests
# ===========================================================================


class TestOwnerDashboardService:
    @pytest.mark.asyncio
    async def test_empty_owner(self, db_session):
        """Owner with no buildings gets empty dashboard."""
        owner = await _create_user(db_session, role="owner")
        result = await get_owner_dashboard(db_session, owner.id)
        assert result.buildings_count == 0
        assert result.pending_actions == 0
        assert result.upcoming_deadlines == []

    @pytest.mark.asyncio
    async def test_owner_with_buildings(self, db_session):
        """Owner sees their buildings counted."""
        owner = await _create_user(db_session, role="owner")
        await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        result = await get_owner_dashboard(db_session, owner.id)
        assert result.buildings_count == 2

    @pytest.mark.asyncio
    async def test_owner_risk_status(self, db_session):
        """Overall risk reflects worst building risk."""
        owner = await _create_user(db_session, role="owner")
        b1 = await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        b2 = await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b1.id, overall_risk_level="low"))
        db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b2.id, overall_risk_level="critical"))
        await db_session.commit()
        result = await get_owner_dashboard(db_session, owner.id)
        assert result.overall_risk_status == "critical"

    @pytest.mark.asyncio
    async def test_owner_upcoming_deadlines(self, db_session):
        """Deadlines within 30 days are returned."""
        owner = await _create_user(db_session, role="owner")
        b = await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        db_session.add(
            ActionItem(
                id=uuid.uuid4(),
                building_id=b.id,
                source_type="diagnostic",
                action_type="inspection",
                title="Inspect asbestos",
                priority="high",
                status="open",
                due_date=date.today() + timedelta(days=10),
            )
        )
        await db_session.commit()
        result = await get_owner_dashboard(db_session, owner.id)
        assert len(result.upcoming_deadlines) == 1
        assert result.upcoming_deadlines[0].title == "Inspect asbestos"

    @pytest.mark.asyncio
    async def test_owner_buildings_needing_attention(self, db_session):
        """Buildings with critical/high risk appear in attention list."""
        owner = await _create_user(db_session, role="owner")
        b = await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b.id, overall_risk_level="high"))
        await db_session.commit()
        result = await get_owner_dashboard(db_session, owner.id)
        assert len(result.buildings_needing_attention) == 1
        assert result.buildings_needing_attention[0].risk_level == "high"

    @pytest.mark.asyncio
    async def test_owner_estimated_cost(self, db_session):
        """Total estimated cost sums planned intervention costs."""
        owner = await _create_user(db_session, role="owner")
        b = await _create_building(db_session, owner_id=owner.id, created_by=owner.id)
        db_session.add(
            Intervention(
                id=uuid.uuid4(),
                building_id=b.id,
                intervention_type="removal",
                title="Remove asbestos",
                status="planned",
                cost_chf=25000.0,
                created_by=owner.id,
            )
        )
        await db_session.commit()
        result = await get_owner_dashboard(db_session, owner.id)
        assert result.total_estimated_cost == 25000.0


class TestDiagnosticianDashboardService:
    @pytest.mark.asyncio
    async def test_empty_diagnostician(self, db_session):
        """Diagnostician with no diagnostics gets empty dashboard."""
        diag = await _create_user(db_session, role="diagnostician")
        result = await get_diagnostician_dashboard(db_session, diag.id)
        assert result.assigned_buildings == 0
        assert result.diagnostics_in_progress == 0

    @pytest.mark.asyncio
    async def test_diagnostician_counts(self, db_session):
        """Diagnostician sees correct counts for their diagnostics."""
        diag = await _create_user(db_session, role="diagnostician")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        db_session.add(
            Diagnostic(
                id=uuid.uuid4(),
                building_id=b.id,
                diagnostic_type="asbestos",
                status="in_progress",
                diagnostician_id=diag.id,
            )
        )
        db_session.add(
            Diagnostic(
                id=uuid.uuid4(),
                building_id=b.id,
                diagnostic_type="pcb",
                status="draft",
                diagnostician_id=diag.id,
            )
        )
        await db_session.commit()
        result = await get_diagnostician_dashboard(db_session, diag.id)
        assert result.assigned_buildings == 1
        assert result.diagnostics_in_progress == 1
        assert result.workload_forecast == 1  # draft

    @pytest.mark.asyncio
    async def test_diagnostician_pending_validations(self, db_session):
        """Completed but not validated diagnostics count as pending."""
        diag = await _create_user(db_session, role="diagnostician")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        db_session.add(
            Diagnostic(
                id=uuid.uuid4(),
                building_id=b.id,
                diagnostic_type="asbestos",
                status="completed",
                diagnostician_id=diag.id,
            )
        )
        await db_session.commit()
        result = await get_diagnostician_dashboard(db_session, diag.id)
        assert result.pending_validations == 1


class TestAuthorityDashboardService:
    @pytest.mark.asyncio
    async def test_empty_authority(self, db_session):
        """Authority with no buildings gets zeros."""
        auth_user = await _create_user(db_session, role="authority")
        result = await get_authority_dashboard(db_session, auth_user.id)
        assert result.buildings_in_jurisdiction == 0

    @pytest.mark.asyncio
    async def test_authority_counts(self, db_session):
        """Authority sees all buildings and pending submissions."""
        auth_user = await _create_user(db_session, role="authority")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        db_session.add(
            Diagnostic(
                id=uuid.uuid4(),
                building_id=b.id,
                diagnostic_type="asbestos",
                status="completed",
                diagnostician_id=admin.id,
            )
        )
        await db_session.commit()
        result = await get_authority_dashboard(db_session, auth_user.id)
        assert result.buildings_in_jurisdiction == 1
        assert result.pending_submissions == 1
        assert result.approval_queue == 1

    @pytest.mark.asyncio
    async def test_authority_overdue(self, db_session):
        """Overdue actions are counted."""
        auth_user = await _create_user(db_session, role="authority")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        db_session.add(
            ActionItem(
                id=uuid.uuid4(),
                building_id=b.id,
                source_type="compliance",
                action_type="remediation",
                title="Overdue task",
                priority="high",
                status="open",
                due_date=date.today() - timedelta(days=10),
            )
        )
        await db_session.commit()
        result = await get_authority_dashboard(db_session, auth_user.id)
        assert result.overdue_compliance_items == 1

    @pytest.mark.asyncio
    async def test_authority_critical_risk(self, db_session):
        """Buildings with critical risk are counted."""
        auth_user = await _create_user(db_session, role="authority")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b.id, overall_risk_level="critical"))
        await db_session.commit()
        result = await get_authority_dashboard(db_session, auth_user.id)
        assert result.buildings_with_critical_risk == 1


class TestContractorDashboardService:
    @pytest.mark.asyncio
    async def test_empty_contractor(self, db_session):
        """Contractor with no interventions gets empty dashboard."""
        contractor = await _create_user(db_session, role="contractor")
        result = await get_contractor_dashboard(db_session, contractor.id)
        assert result.assigned_interventions == 0
        assert result.in_progress_works == 0

    @pytest.mark.asyncio
    async def test_contractor_counts(self, db_session):
        """Contractor sees their intervention counts."""
        contractor = await _create_user(db_session, role="contractor")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        db_session.add(
            Intervention(
                id=uuid.uuid4(),
                building_id=b.id,
                intervention_type="removal",
                title="Remove asbestos",
                status="in_progress",
                contractor_id=contractor.id,
                created_by=admin.id,
            )
        )
        db_session.add(
            Intervention(
                id=uuid.uuid4(),
                building_id=b.id,
                intervention_type="encapsulation",
                title="Encapsulate PCB",
                status="planned",
                contractor_id=contractor.id,
                date_start=date.today() + timedelta(days=5),
                created_by=admin.id,
            )
        )
        await db_session.commit()
        result = await get_contractor_dashboard(db_session, contractor.id)
        assert result.assigned_interventions == 2
        assert result.in_progress_works == 1
        assert len(result.upcoming_starts) == 1

    @pytest.mark.asyncio
    async def test_contractor_acknowledgment_status(self, db_session):
        """Contractor sees acknowledgment status counts."""
        contractor = await _create_user(db_session, role="contractor")
        admin = await _create_user(db_session, role="admin")
        b = await _create_building(db_session, created_by=admin.id)
        interv = Intervention(
            id=uuid.uuid4(),
            building_id=b.id,
            intervention_type="removal",
            title="Remove lead",
            status="planned",
            contractor_id=contractor.id,
            created_by=admin.id,
        )
        db_session.add(interv)
        await db_session.commit()
        db_session.add(
            ContractorAcknowledgment(
                id=uuid.uuid4(),
                intervention_id=interv.id,
                building_id=b.id,
                contractor_user_id=contractor.id,
                status="pending",
                safety_requirements={"ppe": True},
                created_by=admin.id,
            )
        )
        await db_session.commit()
        result = await get_contractor_dashboard(db_session, contractor.id)
        assert result.acknowledgment_status.get("pending") == 1
        assert result.required_certifications == 1


# ===========================================================================
# API-level tests
# ===========================================================================


class TestOwnerDashboardAPI:
    @pytest.mark.asyncio
    async def test_owner_endpoint(self, client, db_session):
        owner = await _create_user(db_session, role="owner", email="dash-owner@test.ch")
        headers = _make_token(owner)
        resp = await client.get("/api/v1/dashboard/owner", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "buildings_count" in data

    @pytest.mark.asyncio
    async def test_owner_endpoint_forbidden_for_contractor(self, client, db_session):
        contractor = await _create_user(db_session, role="contractor", email="dash-contr@test.ch")
        headers = _make_token(contractor)
        resp = await client.get("/api/v1/dashboard/owner", headers=headers)
        assert resp.status_code in (401, 403)


class TestDiagnosticianDashboardAPI:
    @pytest.mark.asyncio
    async def test_diagnostician_endpoint(self, client, db_session):
        diag = await _create_user(db_session, role="diagnostician", email="dash-diag@test.ch")
        headers = _make_token(diag)
        resp = await client.get("/api/v1/dashboard/diagnostician", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "assigned_buildings" in data


class TestAuthorityDashboardAPI:
    @pytest.mark.asyncio
    async def test_authority_endpoint(self, client, db_session):
        auth_user = await _create_user(db_session, role="authority", email="dash-auth@test.ch")
        headers = _make_token(auth_user)
        resp = await client.get("/api/v1/dashboard/authority", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "buildings_in_jurisdiction" in data

    @pytest.mark.asyncio
    async def test_authority_endpoint_forbidden_for_owner(self, client, db_session):
        owner = await _create_user(db_session, role="owner", email="dash-own2@test.ch")
        headers = _make_token(owner)
        resp = await client.get("/api/v1/dashboard/authority", headers=headers)
        assert resp.status_code in (401, 403)


class TestContractorDashboardAPI:
    @pytest.mark.asyncio
    async def test_contractor_endpoint(self, client, db_session):
        contractor = await _create_user(db_session, role="contractor", email="dash-cont@test.ch")
        headers = _make_token(contractor)
        resp = await client.get("/api/v1/dashboard/contractor", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "assigned_interventions" in data

    @pytest.mark.asyncio
    async def test_admin_can_access_all(self, client, db_session):
        """Admin can access any dashboard endpoint."""
        admin = await _create_user(db_session, role="admin", email="dash-admin@test.ch")
        headers = _make_token(admin)
        for endpoint in ("owner", "diagnostician", "authority", "contractor"):
            resp = await client.get(f"/api/v1/dashboard/{endpoint}", headers=headers)
            assert resp.status_code == 200, f"Admin denied on {endpoint}"

    @pytest.mark.asyncio
    async def test_unauthenticated_request(self, client):
        """Unauthenticated request returns 403."""
        resp = await client.get("/api/v1/dashboard/owner")
        assert resp.status_code == 401
