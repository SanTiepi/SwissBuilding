"""Tests for Composite Score Engine service."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.user import User
from app.models.zone import Zone
from app.services.composite_score_engine import (
    _SCORE_COMPUTERS,
    compute_all_composite_scores,
    compute_single_score,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"composite-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
    )
    db.add(user)
    await db.commit()
    return user


async def _make_building(db, user, **kw):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Composite 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "surface_area_m2": 500,
        "created_by": user.id,
        "status": "active",
    }
    defaults.update(kw)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    return b


async def _enrich_building(db, building_id, user_id):
    """Add diagnostics, samples, documents, plans, elements, interventions, leases, inventory."""
    # Diagnostic + samples
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db.add(diag)
    await db.commit()

    for i in range(3):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{i}",
            pollutant_type="asbestos",
            concentration=0.5 if i < 2 else 3.0,
            unit="%",
            threshold_exceeded=(i == 2),
            risk_level="low" if i < 2 else "high",
        )
        db.add(s)

    # Documents
    for dtype in ["diagnostic_report", "lab_report"]:
        doc = Document(
            id=uuid.uuid4(),
            building_id=building_id,
            file_path=f"/files/{dtype}.pdf",
            file_name=f"{dtype}.pdf",
            document_type=dtype,
        )
        db.add(doc)

    # Plan
    plan = TechnicalPlan(
        id=uuid.uuid4(),
        building_id=building_id,
        plan_type="floor_plan",
        title="Plan RDC",
        file_path="/plans/floor.pdf",
        file_name="floor.pdf",
    )
    db.add(plan)

    # Zone + elements
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="floor",
        name="Floor 1",
    )
    db.add(zone)
    await db.commit()

    for cond in ["good", "fair", "poor"]:
        el = BuildingElement(
            id=uuid.uuid4(),
            zone_id=zone.id,
            element_type="wall",
            name=f"Mur {cond}",
            condition=cond,
        )
        db.add(el)

    # Intervention
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="asbestos_removal",
        title="Asbestos removal floor 1",
        status="completed",
        cost_chf=25000,
        date_start=date(2025, 1, 1),
        date_end=date(2025, 4, 1),
    )
    db.add(iv)

    # Lease
    lease = Lease(
        id=uuid.uuid4(),
        building_id=building_id,
        lease_type="residential",
        reference_code=f"L-{uuid.uuid4().hex[:4]}",
        tenant_type="contact",
        tenant_id=uuid.uuid4(),
        date_start=date(2024, 1, 1),
        date_end=date(2027, 1, 1),
        rent_monthly_chf=2500,
        status="active",
    )
    db.add(lease)

    # Inventory
    inv = InventoryItem(
        id=uuid.uuid4(),
        building_id=building_id,
        item_type="boiler",
        name="Chaudière",
        condition="good",
        warranty_end_date=date.today() + timedelta(days=365),
    )
    db.add(inv)

    # Obligation
    obl = Obligation(
        id=uuid.uuid4(),
        building_id=building_id,
        title="Inspection annuelle",
        obligation_type="regulatory_inspection",
        due_date=date.today() + timedelta(days=90),
        status="upcoming",
        priority="medium",
    )
    db.add(obl)

    await db.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await compute_all_composite_scores(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_all_15_scores_present(db_session):
    """All 15 composite scores should be present in result."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    result = await compute_all_composite_scores(db_session, building.id)
    expected_keys = set(_SCORE_COMPUTERS.keys())
    actual_keys = {k for k in result if k not in ("building_id", "generated_at")}
    assert expected_keys == actual_keys


@pytest.mark.asyncio
async def test_each_score_has_required_fields(db_session):
    """Each score dict should have value, grade, data_completeness, top_factors."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    result = await compute_all_composite_scores(db_session, building.id)
    for name in _SCORE_COMPUTERS:
        score = result[name]
        assert "value" in score, f"{name} missing 'value'"
        assert "grade" in score, f"{name} missing 'grade'"
        assert "data_completeness" in score, f"{name} missing 'data_completeness'"
        assert "top_factors" in score, f"{name} missing 'top_factors'"
        assert isinstance(score["top_factors"], list)


@pytest.mark.asyncio
async def test_scores_with_enriched_building(db_session):
    """Enriched building should produce meaningful (non-zero) scores."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)
    await _enrich_building(db_session, building.id, user.id)

    result = await compute_all_composite_scores(db_session, building.id)
    # Health score should be computed with data
    health = result["health_score"]
    assert health["value"] > 0
    assert health["data_completeness"] > 0

    # Digital twin should reflect data presence
    twin = result["digital_twin_score"]
    assert twin["value"] > 40  # We added lots of data

    # Investment score should reflect lease revenue
    invest = result["investment_score"]
    assert invest["data_completeness"] > 0


@pytest.mark.asyncio
async def test_minimal_building_has_low_completeness(db_session):
    """Building with no data should have low data_completeness on most scores."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    result = await compute_all_composite_scores(db_session, building.id)
    # Digital twin should be very low for empty building
    twin = result["digital_twin_score"]
    assert twin["value"] < 40  # Missing most data


@pytest.mark.asyncio
async def test_health_score_no_diagnostics(db_session):
    """Health score without diagnostics should be lower."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user, construction_year=1960)

    result = await compute_all_composite_scores(db_session, building.id)
    health = result["health_score"]
    assert health["value"] < 70  # No diagnostics = lower health


@pytest.mark.asyncio
async def test_urgency_score_with_obligations(db_session):
    """Approaching obligations increase urgency."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    obl = Obligation(
        id=uuid.uuid4(),
        building_id=building.id,
        title="Urgent obligation",
        obligation_type="regulatory_inspection",
        due_date=date.today() + timedelta(days=15),
        status="due_soon",
        priority="critical",
    )
    db_session.add(obl)
    await db_session.commit()

    result = await compute_all_composite_scores(db_session, building.id)
    urgency = result["urgency_score"]
    assert urgency["value"] > 0


@pytest.mark.asyncio
async def test_compute_single_score(db_session):
    """compute_single_score returns one score with metadata."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    result = await compute_single_score(db_session, building.id, "health_score")
    assert "value" in result
    assert result["score_name"] == "health_score"
    assert "building_id" in result


@pytest.mark.asyncio
async def test_compute_single_score_unknown(db_session):
    """Unknown score name raises ValueError."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    with pytest.raises(ValueError, match="Unknown score"):
        await compute_single_score(db_session, building.id, "nonexistent_score")


@pytest.mark.asyncio
async def test_grade_boundaries(db_session):
    """Grades should be A-F based on score thresholds."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)
    await _enrich_building(db_session, building.id, user.id)

    result = await compute_all_composite_scores(db_session, building.id)
    valid_grades = {"A", "B", "C", "D", "E", "F"}
    for name in _SCORE_COMPUTERS:
        grade = result[name]["grade"]
        assert grade in valid_grades, f"{name} has invalid grade: {grade}"
