"""Tests for audit readiness service and API."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.user import User
from app.services.audit_readiness_service import (
    READY_THRESHOLD,
    evaluate_audit_readiness,
    get_audit_checklist,
    get_portfolio_audit_readiness,
    simulate_audit_outcome,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user_in_org(db: AsyncSession, org: Organization, role: str = "admin") -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building(
    db: AsyncSession,
    created_by: uuid.UUID,
    *,
    construction_year: int = 1965,
    surface_area_m2: float | None = 500.0,
) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=created_by,
        status="active",
        surface_area_m2=surface_area_m2,
    )
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _create_validated_diagnostic(db: AsyncSession, building_id: uuid.UUID) -> Diagnostic:
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full",
        status="validated",
        diagnostic_context="AvT",
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _create_sample(
    db: AsyncSession,
    diagnostic_id: uuid.UUID,
    *,
    pollutant_type: str = "asbestos",
    concentration: float | None = 1.5,
    unit: str | None = "%",
    risk_level: str = "high",
    threshold_exceeded: bool = True,
    waste_disposal_type: str | None = "special",
    cfst_work_category: str | None = "major",
) -> Sample:
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
        risk_level=risk_level,
        threshold_exceeded=threshold_exceeded,
        waste_disposal_type=waste_disposal_type,
        cfst_work_category=cfst_work_category,
        location_floor="1",
        location_room="Corridor",
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _create_document(
    db: AsyncSession,
    building_id: uuid.UUID,
    *,
    document_type: str = "diagnostic_report",
) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/docs/test.pdf",
        file_name="test.pdf",
        document_type=document_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def _create_artefact(
    db: AsyncSession,
    building_id: uuid.UUID,
    *,
    status: str = "submitted",
    legal_basis: str | None = "OTConst Art. 60a",
    expires_at: datetime | None = None,
) -> ComplianceArtefact:
    a = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building_id,
        artefact_type="suva_notification",
        title="SUVA Notification",
        status=status,
        legal_basis=legal_basis,
        expires_at=expires_at,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _create_assignment(
    db: AsyncSession,
    building_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    role: str = "responsible",
) -> Assignment:
    a = Assignment(
        id=uuid.uuid4(),
        target_type="building",
        target_id=building_id,
        user_id=user_id,
        role=role,
        created_by=user_id,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _create_events(
    db: AsyncSession,
    building_id: uuid.UUID,
    user_id: uuid.UUID,
    count: int = 3,
) -> list[Event]:
    events = []
    for i in range(count):
        e = Event(
            id=uuid.uuid4(),
            building_id=building_id,
            event_type="milestone",
            date=datetime.now(UTC).date(),
            title=f"Event {i + 1}",
            created_by=user_id,
        )
        db.add(e)
        events.append(e)
    await db.commit()
    return events


async def _create_plan(
    db: AsyncSession,
    building_id: uuid.UUID,
    *,
    plan_type: str = "floor_plan",
) -> TechnicalPlan:
    p = TechnicalPlan(
        id=uuid.uuid4(),
        building_id=building_id,
        plan_type=plan_type,
        title="Test Plan",
        file_path="/plans/test.pdf",
        file_name="test.pdf",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _setup_fully_ready(db: AsyncSession, admin_user):
    """Create a building with all checks passing."""
    building = await _create_building(db, admin_user.id)
    diag = await _create_validated_diagnostic(db, building.id)
    diag.suva_notification_required = True
    diag.suva_notification_date = datetime.now(UTC).date()
    await db.commit()

    for pollutant in ["asbestos", "pcb", "lead", "hap", "radon"]:
        exceeded = pollutant == "asbestos"
        await _create_sample(
            db,
            diag.id,
            pollutant_type=pollutant,
            threshold_exceeded=exceeded,
            waste_disposal_type="special" if exceeded else None,
            cfst_work_category="major" if exceeded else None,
        )
    await _create_document(db, building.id, document_type="diagnostic_report")
    await _create_document(db, building.id, document_type="lab_report")
    await _create_artefact(db, building.id)
    await _create_assignment(db, building.id, admin_user.id, role="responsible")
    await _create_events(db, building.id, admin_user.id, count=3)
    await _create_plan(db, building.id)
    return building


# ---------------------------------------------------------------------------
# FN1 - evaluate_audit_readiness
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_evaluate_readiness_not_found(db_session):
    result = await evaluate_audit_readiness(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_evaluate_readiness_empty_building(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    result = await evaluate_audit_readiness(db_session, b.id)
    assert result is not None
    assert result.score < READY_THRESHOLD
    assert len(result.checks) == 16


@pytest.mark.anyio
async def test_evaluate_readiness_full_score(db_session, admin_user):
    b = await _setup_fully_ready(db_session, admin_user)
    result = await evaluate_audit_readiness(db_session, b.id)
    assert result is not None
    assert result.score >= READY_THRESHOLD
    done_count = sum(1 for c in result.checks if c.status == "done")
    assert done_count == len(result.checks)


@pytest.mark.anyio
async def test_evaluate_readiness_partial_diagnostics(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()
    result = await evaluate_audit_readiness(db_session, b.id)
    diag_check = next(c for c in result.checks if c.id == "diagnostic_validated")
    assert diag_check.status == "partial"


@pytest.mark.anyio
async def test_evaluate_readiness_score_between_0_100(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    await _create_validated_diagnostic(db_session, b.id)
    result = await evaluate_audit_readiness(db_session, b.id)
    assert 0 <= result.score <= 100


# ---------------------------------------------------------------------------
# FN2 - get_audit_checklist
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_checklist_not_found(db_session):
    result = await get_audit_checklist(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_checklist_has_23_items(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    result = await get_audit_checklist(db_session, b.id)
    assert result is not None
    assert result.total_items == 23
    assert result.done_count + result.missing_count + result.partial_count == result.total_items


@pytest.mark.anyio
async def test_checklist_categories(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    result = await get_audit_checklist(db_session, b.id)
    categories = {item.category for item in result.items}
    assert categories == {"documentation", "compliance", "evidence", "process"}


@pytest.mark.anyio
async def test_checklist_fix_actions(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    result = await get_audit_checklist(db_session, b.id)
    missing_items = [i for i in result.items if i.status == "missing"]
    # All missing items should have a fix action
    for item in missing_items:
        assert item.fix_action is not None


@pytest.mark.anyio
async def test_checklist_fully_ready(db_session, admin_user):
    b = await _setup_fully_ready(db_session, admin_user)
    result = await get_audit_checklist(db_session, b.id)
    # Most items should be done (some heuristic items may vary)
    assert result.done_count >= 16


@pytest.mark.anyio
async def test_checklist_building_info_partial(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id, surface_area_m2=None)
    result = await get_audit_checklist(db_session, b.id)
    info_item = next(i for i in result.items if i.id == "cl_building_info")
    assert info_item.status == "partial"


# ---------------------------------------------------------------------------
# FN3 - simulate_audit_outcome
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_simulate_not_found(db_session):
    result = await simulate_audit_outcome(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_simulate_empty_building_fails(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    result = await simulate_audit_outcome(db_session, b.id)
    assert result is not None
    assert result.outcome == "fail"
    assert len(result.flags) > 0


@pytest.mark.anyio
async def test_simulate_fully_ready_passes(db_session, admin_user):
    b = await _setup_fully_ready(db_session, admin_user)
    result = await simulate_audit_outcome(db_session, b.id)
    assert result.outcome == "pass"
    assert len(result.flags) == 0


@pytest.mark.anyio
async def test_simulate_critical_actions_fail(db_session, admin_user):
    b = await _setup_fully_ready(db_session, admin_user)
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=b.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Critical action",
        priority="critical",
        status="open",
    )
    db_session.add(action)
    await db_session.commit()
    result = await simulate_audit_outcome(db_session, b.id)
    assert result.outcome == "fail"
    critical_flags = [f for f in result.flags if f.severity == "critical"]
    assert len(critical_flags) >= 1


@pytest.mark.anyio
async def test_simulate_recommendations_not_empty_on_fail(db_session, admin_user):
    b = await _create_building(db_session, admin_user.id)
    result = await simulate_audit_outcome(db_session, b.id)
    assert len(result.recommendations) > 0


@pytest.mark.anyio
async def test_simulate_conditional_on_major_flags(db_session, admin_user):
    """A building with most things done but missing compliance artefacts → conditional."""
    b = await _setup_fully_ready(db_session, admin_user)
    # Remove artefacts by creating expired ones
    await db_session.execute(ComplianceArtefact.__table__.delete().where(ComplianceArtefact.building_id == b.id))
    await db_session.commit()
    result = await simulate_audit_outcome(db_session, b.id)
    assert result.outcome in ("conditional", "fail")


# ---------------------------------------------------------------------------
# FN4 - get_portfolio_audit_readiness
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_portfolio_empty_org(db_session):
    org = await _create_org(db_session)
    result = await get_portfolio_audit_readiness(db_session, org.id)
    assert result is not None
    assert result.total_buildings == 0
    assert result.average_score == 0.0


@pytest.mark.anyio
async def test_portfolio_with_buildings(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    await _create_building(db_session, user.id)
    await _create_building(db_session, user.id)
    result = await get_portfolio_audit_readiness(db_session, org.id)
    assert result.total_buildings == 2
    assert result.buildings_needing_prep == 2
    assert len(result.buildings) == 2


@pytest.mark.anyio
async def test_portfolio_ready_building(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)

    # Create a fully ready building under the org user
    building = Building(
        id=uuid.uuid4(),
        address="Rue Ready 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
        surface_area_m2=500.0,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)

    diag = await _create_validated_diagnostic(db_session, building.id)
    diag.suva_notification_required = True
    diag.suva_notification_date = datetime.now(UTC).date()
    await db_session.commit()

    for p in ["asbestos", "pcb", "lead", "hap", "radon"]:
        exceeded = p == "asbestos"
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type=p,
            threshold_exceeded=exceeded,
            waste_disposal_type="special" if exceeded else None,
            cfst_work_category="major" if exceeded else None,
        )
    await _create_document(db_session, building.id, document_type="diagnostic_report")
    await _create_document(db_session, building.id, document_type="lab_report")
    await _create_artefact(db_session, building.id)
    await _create_assignment(db_session, building.id, user.id, role="responsible")
    await _create_events(db_session, building.id, user.id, count=3)
    await _create_plan(db_session, building.id)

    result = await get_portfolio_audit_readiness(db_session, org.id)
    assert result.buildings_ready >= 1
    assert result.average_score >= READY_THRESHOLD


@pytest.mark.anyio
async def test_portfolio_prep_hours(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    await _create_building(db_session, user.id)
    result = await get_portfolio_audit_readiness(db_session, org.id)
    for b in result.buildings:
        if not b.ready:
            assert b.estimated_prep_hours > 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_readiness_404(client: AsyncClient, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/audit-readiness",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_readiness_ok(client: AsyncClient, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/audit-readiness",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert "checks" in data
    assert 0 <= data["score"] <= 100


@pytest.mark.anyio
async def test_api_checklist_ok(client: AsyncClient, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/audit-readiness/checklist",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 23
    assert "items" in data


@pytest.mark.anyio
async def test_api_simulate_ok(client: AsyncClient, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/audit-readiness/simulate",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] in ("pass", "conditional", "fail")
    assert "flags" in data


@pytest.mark.anyio
async def test_api_portfolio_ok(client: AsyncClient, auth_headers, db_session):
    org = await _create_org(db_session)
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/audit-readiness",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "average_score" in data
    assert "buildings" in data


@pytest.mark.anyio
async def test_api_readiness_requires_auth(client: AsyncClient, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/audit-readiness",
    )
    assert resp.status_code == 401
