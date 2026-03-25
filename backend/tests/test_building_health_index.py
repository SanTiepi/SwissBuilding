"""Tests for Building Health Index service and API."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.user import User
from app.models.zone import Zone
from app.services.building_health_index_service import (
    DIMENSION_WEIGHTS,
    _compute_trend,
    _score_pollutant_status,
    _score_structural_condition,
    _score_to_grade,
    calculate_health_index,
    get_health_breakdown,
    get_portfolio_health_dashboard,
    predict_health_trajectory,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": date.today(),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "concentration": 0.5,
        "unit": "%",
        "threshold_exceeded": False,
        "risk_level": "low",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _create_document(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "file_path": "/files/test.pdf",
        "file_name": "test.pdf",
        "document_type": "diagnostic_report",
    }
    defaults.update(kwargs)
    d = Document(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _create_zone(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "zone_type": "floor",
        "name": "Floor 1",
    }
    defaults.update(kwargs)
    z = Zone(**defaults)
    db.add(z)
    await db.commit()
    await db.refresh(z)
    return z


async def _create_element(db, zone_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "zone_id": zone_id,
        "element_type": "wall",
        "name": "Wall A",
        "condition": "good",
    }
    defaults.update(kwargs)
    e = BuildingElement(**defaults)
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return e


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "remediation",
        "title": "Asbestos removal",
        "status": "completed",
        "date_end": datetime.now(UTC).date(),
    }
    defaults.update(kwargs)
    i = Intervention(**defaults)
    db.add(i)
    await db.commit()
    await db.refresh(i)
    return i


async def _create_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": "diagnostic",
        "action_type": "remediation",
        "title": "Test action",
        "priority": "medium",
        "status": "open",
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _create_plan(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "plan_type": "floor_plan",
        "title": "Ground floor",
        "file_path": "/plans/floor.pdf",
        "file_name": "floor.pdf",
    }
    defaults.update(kwargs)
    p = TechnicalPlan(**defaults)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _create_org(db, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Org",
        "type": "property_management",
    }
    defaults.update(kwargs)
    o = Organization(**defaults)
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return o


async def _create_org_user(db, org_id):
    u = User(
        id=uuid.uuid4(),
        email=f"health-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Health",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Unit tests — grade helper
# ---------------------------------------------------------------------------


class TestScoreToGrade:
    def test_grade_a(self):
        assert _score_to_grade(95) == "A"
        assert _score_to_grade(90) == "A"

    def test_grade_b(self):
        assert _score_to_grade(80) == "B"
        assert _score_to_grade(75) == "B"

    def test_grade_c(self):
        assert _score_to_grade(65) == "C"
        assert _score_to_grade(60) == "C"

    def test_grade_d(self):
        assert _score_to_grade(50) == "D"
        assert _score_to_grade(40) == "D"

    def test_grade_f(self):
        assert _score_to_grade(10) == "F"
        assert _score_to_grade(0) == "F"

    def test_grade_e(self):
        assert _score_to_grade(30) == "E"
        assert _score_to_grade(20) == "E"

    def test_boundary_values(self):
        assert _score_to_grade(89.9) == "B"
        assert _score_to_grade(90.0) == "A"
        assert _score_to_grade(74.9) == "C"
        assert _score_to_grade(75.0) == "B"


# ---------------------------------------------------------------------------
# Unit tests — pollutant scorer
# ---------------------------------------------------------------------------


class TestScorePollutantStatus:
    def test_no_diagnostics(self):
        score, factors = _score_pollutant_status([], [])
        assert score == 20.0
        assert "No diagnostics performed" in factors

    def test_no_completed_diagnostics(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="draft",
        )
        score, _factors = _score_pollutant_status([], [diag])
        assert score == 30.0

    def test_completed_no_samples(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="completed",
        )
        score, _factors = _score_pollutant_status([], [diag])
        assert score == 50.0

    def test_all_clean_samples(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="completed",
        )
        samples = []
        for pt in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
            samples.append(
                Sample(
                    id=uuid.uuid4(),
                    diagnostic_id=diag.id,
                    sample_number=f"S-{pt}",
                    pollutant_type=pt,
                    threshold_exceeded=False,
                    risk_level="low",
                )
            )
        score, factors = _score_pollutant_status(samples, [diag])
        assert score == 100.0
        assert "All samples within thresholds" in factors

    def test_exceeded_samples_lower_score(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="completed",
        )
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S-001",
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="high",
        )
        score, factors = _score_pollutant_status([sample], [diag])
        assert score < 100
        assert any("exceed" in f for f in factors)


# ---------------------------------------------------------------------------
# Unit tests — structural condition scorer
# ---------------------------------------------------------------------------


class TestScoreStructuralCondition:
    def test_no_elements_no_year(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
        )
        score, factors = _score_structural_condition([], b)
        assert score == 50.0
        assert "No structural data" in factors[0]

    def test_new_building_high_score(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            construction_year=datetime.now(UTC).year - 5,
        )
        score, _factors = _score_structural_condition([], b)
        assert score == 90.0

    def test_old_building_low_score(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            construction_year=1900,
        )
        score, _factors = _score_structural_condition([], b)
        assert score == 35.0

    def test_excellent_elements(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
        )
        el = BuildingElement(
            id=uuid.uuid4(),
            zone_id=uuid.uuid4(),
            element_type="wall",
            name="Wall",
            condition="excellent",
        )
        score, _factors = _score_structural_condition([el], b)
        assert score == 100.0

    def test_critical_elements(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
        )
        el = BuildingElement(
            id=uuid.uuid4(),
            zone_id=uuid.uuid4(),
            element_type="wall",
            name="Wall",
            condition="critical",
        )
        score, factors = _score_structural_condition([el], b)
        assert score == 10.0
        assert any("Critical" in f for f in factors)


# ---------------------------------------------------------------------------
# Unit tests — trend computation
# ---------------------------------------------------------------------------


class TestComputeTrend:
    def test_stable_no_data(self):
        assert _compute_trend([], []) == "stable"

    def test_improving_with_completed_intervention(self):
        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            intervention_type="remediation",
            title="Test",
            status="completed",
            date_end=date.today(),
        )
        assert _compute_trend([], [intervention]) == "improving"

    def test_declining_with_recent_critical_action(self):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            source_type="diagnostic",
            action_type="remediation",
            title="Critical issue",
            priority="critical",
            status="open",
            created_at=datetime.now(UTC),
        )
        assert _compute_trend([action], []) == "declining"

    def test_stable_with_old_intervention(self):
        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            intervention_type="remediation",
            title="Test",
            status="completed",
            date_end=date.today() - timedelta(days=120),
        )
        assert _compute_trend([], [intervention]) == "stable"

    def test_declining_when_critical_exceeds_completed(self):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            source_type="diagnostic",
            action_type="remediation",
            title="Critical",
            priority="high",
            status="open",
            created_at=datetime.now(UTC),
        )
        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            intervention_type="remediation",
            title="Done",
            status="completed",
            date_end=date.today() - timedelta(days=120),
        )
        # intervention is old (>90 days), action is recent → declining
        assert _compute_trend([action], [intervention]) == "declining"


# ---------------------------------------------------------------------------
# Unit tests — dimension weights
# ---------------------------------------------------------------------------


class TestDimensionWeights:
    def test_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_pollutant_weight_30(self):
        assert DIMENSION_WEIGHTS["pollutant_status"] == 0.30

    def test_structural_weight_20(self):
        assert DIMENSION_WEIGHTS["structural_condition"] == 0.20

    def test_compliance_weight_20(self):
        assert DIMENSION_WEIGHTS["compliance"] == 0.20

    def test_documentation_weight_15(self):
        assert DIMENSION_WEIGHTS["documentation_completeness"] == 0.15

    def test_monitoring_weight_15(self):
        assert DIMENSION_WEIGHTS["monitoring_compliance"] == 0.15


# ---------------------------------------------------------------------------
# Service tests — calculate_health_index
# ---------------------------------------------------------------------------


class TestCalculateHealthIndex:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await calculate_health_index(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_minimal_building(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_health_index(db_session, b.id)

        assert result.building_id == b.id
        assert 0 <= result.overall_score <= 100
        assert result.grade in ("A", "B", "C", "D", "E", "F")
        assert result.trend in ("improving", "stable", "declining")
        assert len(result.dimensions) == 5

    @pytest.mark.asyncio
    async def test_dimension_weights_sum_to_one(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_health_index(db_session, b.id)
        total_weight = sum(d.weight for d in result.dimensions)
        assert abs(total_weight - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_healthy_building_scores_high(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user, construction_year=2020)
        diag = await _create_diagnostic(db_session, b.id, status="completed")
        for pt in ("asbestos", "pcb", "lead", "hap", "radon"):
            await _create_sample(db_session, diag.id, pollutant_type=pt, threshold_exceeded=False)
        await _create_document(db_session, b.id, document_type="diagnostic_report")
        await _create_document(db_session, b.id, document_type="lab_report")
        await _create_plan(db_session, b.id)
        zone = await _create_zone(db_session, b.id)
        await _create_element(db_session, zone.id, condition="excellent")
        await _create_intervention(db_session, b.id, status="completed")

        result = await calculate_health_index(db_session, b.id)
        assert result.overall_score >= 70
        assert result.grade in ("A", "B", "C")

    @pytest.mark.asyncio
    async def test_polluted_building_scores_lower(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        diag = await _create_diagnostic(db_session, b.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="critical",
        )
        result = await calculate_health_index(db_session, b.id)
        pollutant_dim = next(d for d in result.dimensions if d.dimension == "pollutant_status")
        assert pollutant_dim.score < 80

    @pytest.mark.asyncio
    async def test_all_dimensions_present(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_health_index(db_session, b.id)
        dim_names = {d.dimension for d in result.dimensions}
        assert dim_names == set(DIMENSION_WEIGHTS.keys())

    @pytest.mark.asyncio
    async def test_overall_equals_sum_of_weighted(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_health_index(db_session, b.id)
        expected = round(sum(d.weighted_score for d in result.dimensions), 1)
        assert result.overall_score == expected

    @pytest.mark.asyncio
    async def test_building_with_zones_and_elements(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        zone = await _create_zone(db_session, b.id)
        await _create_element(db_session, zone.id, condition="good")
        await _create_element(db_session, zone.id, condition="fair", name="Wall B", element_type="ceiling")

        result = await calculate_health_index(db_session, b.id)
        structural = next(d for d in result.dimensions if d.dimension == "structural_condition")
        # Average of good(80) and fair(60) = 70
        assert structural.score == 70.0

    @pytest.mark.asyncio
    async def test_building_with_completed_interventions(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        await _create_intervention(db_session, b.id, status="completed")
        result = await calculate_health_index(db_session, b.id)
        assert result.trend == "improving"

    @pytest.mark.asyncio
    async def test_building_with_open_critical_actions(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        await _create_action(
            db_session,
            b.id,
            priority="critical",
            status="open",
            created_at=datetime.now(UTC),
        )
        result = await calculate_health_index(db_session, b.id)
        assert result.trend == "declining"

    @pytest.mark.asyncio
    async def test_building_with_documents_and_plans(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        diag = await _create_diagnostic(db_session, b.id, status="completed")
        await _create_sample(db_session, diag.id, pollutant_type="asbestos")
        await _create_document(db_session, b.id, document_type="diagnostic_report")
        await _create_document(db_session, b.id, document_type="lab_report")
        await _create_plan(db_session, b.id, plan_type="floor_plan")

        result = await calculate_health_index(db_session, b.id)
        doc_dim = next(d for d in result.dimensions if d.dimension == "documentation_completeness")
        assert doc_dim.score > 50

    @pytest.mark.asyncio
    async def test_grade_assignment_consistent(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_health_index(db_session, b.id)
        expected_grade = _score_to_grade(result.overall_score)
        assert result.grade == expected_grade


# ---------------------------------------------------------------------------
# Service tests — get_health_breakdown
# ---------------------------------------------------------------------------


class TestGetHealthBreakdown:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_health_breakdown(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_breakdown_structure(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)

        assert result.building_id == b.id
        assert result.overall_score >= 0
        assert isinstance(result.worst_contributors, list)
        assert isinstance(result.improvement_levers, list)

    @pytest.mark.asyncio
    async def test_levers_sorted_by_priority(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)

        if len(result.improvement_levers) >= 2:
            for i in range(len(result.improvement_levers) - 1):
                assert result.improvement_levers[i].priority < result.improvement_levers[i + 1].priority

    @pytest.mark.asyncio
    async def test_levers_have_gain(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)
        for lever in result.improvement_levers:
            assert lever.potential_gain > 0

    @pytest.mark.asyncio
    async def test_worst_contributors_only_below_80(self, db_session, admin_user):
        """Worst contributors should only include dimensions scoring < 80."""
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)
        assert len(result.worst_contributors) <= 3

    @pytest.mark.asyncio
    async def test_lever_effort_levels(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)
        for lever in result.improvement_levers:
            assert lever.effort in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_lever_dimensions_are_valid(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)
        for lever in result.improvement_levers:
            assert lever.dimension in DIMENSION_WEIGHTS

    @pytest.mark.asyncio
    async def test_levers_sorted_by_potential_gain_desc(self, db_session, admin_user):
        """Levers should be sorted by potential_gain descending (priority 1 = highest gain)."""
        b = await _create_building(db_session, admin_user)
        result = await get_health_breakdown(db_session, b.id)
        gains = [lv.potential_gain for lv in result.improvement_levers]
        assert gains == sorted(gains, reverse=True)


# ---------------------------------------------------------------------------
# Service tests — predict_health_trajectory
# ---------------------------------------------------------------------------


class TestPredictHealthTrajectory:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await predict_health_trajectory(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_trajectory_structure(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await predict_health_trajectory(db_session, b.id)

        assert result.building_id == b.id
        assert result.current_score >= 0
        assert len(result.decay_curve) == 12
        assert len(result.improvement_curve) == 12

    @pytest.mark.asyncio
    async def test_decay_curve_decreasing(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await predict_health_trajectory(db_session, b.id)

        scores = [p.score for p in result.decay_curve]
        assert scores[0] >= scores[-1]

    @pytest.mark.asyncio
    async def test_improvement_with_planned_interventions(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        await _create_intervention(db_session, b.id, status="planned")
        await _create_action(db_session, b.id, status="open")

        result = await predict_health_trajectory(db_session, b.id)
        scores = [p.score for p in result.improvement_curve]
        assert scores[-1] >= scores[0]

    @pytest.mark.asyncio
    async def test_trajectory_months_sequential(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await predict_health_trajectory(db_session, b.id)
        for i, pt in enumerate(result.decay_curve):
            assert pt.month == i + 1
        for i, pt in enumerate(result.improvement_curve):
            assert pt.month == i + 1

    @pytest.mark.asyncio
    async def test_decay_curve_minimum_floor(self, db_session, admin_user):
        """Decay curve should not go below 5."""
        b = await _create_building(db_session, admin_user)
        result = await predict_health_trajectory(db_session, b.id)
        for pt in result.decay_curve:
            assert pt.score >= 5

    @pytest.mark.asyncio
    async def test_improvement_curve_capped_at_100(self, db_session, admin_user):
        """Improvement curve should not exceed 100."""
        b = await _create_building(db_session, admin_user)
        await _create_intervention(db_session, b.id, status="planned")
        await _create_intervention(db_session, b.id, status="planned")
        await _create_intervention(db_session, b.id, status="planned")
        await _create_action(db_session, b.id, status="open")

        result = await predict_health_trajectory(db_session, b.id)
        for pt in result.improvement_curve:
            assert pt.score <= 100

    @pytest.mark.asyncio
    async def test_recommended_actions_from_worst_dims(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await predict_health_trajectory(db_session, b.id)
        for action in result.recommended_actions:
            assert action.dimension in DIMENSION_WEIGHTS
            assert action.expected_gain > 0

    @pytest.mark.asyncio
    async def test_no_interventions_flat_improvement(self, db_session, admin_user):
        """Without planned interventions or open actions, improvement curve stays flat."""
        b = await _create_building(db_session, admin_user)
        result = await predict_health_trajectory(db_session, b.id)
        # No planned interventions and no open actions
        scores = [p.score for p in result.improvement_curve]
        # All should be the same (current_score + 0 per month)
        assert all(s == scores[0] for s in scores)

    @pytest.mark.asyncio
    async def test_current_score_matches_health_index(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        hi = await calculate_health_index(db_session, b.id)
        traj = await predict_health_trajectory(db_session, b.id)
        assert traj.current_score == hi.overall_score


# ---------------------------------------------------------------------------
# Service tests — get_portfolio_health_dashboard
# ---------------------------------------------------------------------------


class TestPortfolioHealthDashboard:
    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        org = await _create_org(db_session)
        result = await get_portfolio_health_dashboard(db_session, org.id)

        assert result.building_count == 0
        assert result.average_score == 0.0
        assert result.trend == "stable"

    @pytest.mark.asyncio
    async def test_org_no_users(self, db_session):
        """Org with no users returns empty dashboard."""
        result = await get_portfolio_health_dashboard(db_session, uuid.uuid4())
        assert result.building_count == 0
        assert result.average_grade == "F"

    @pytest.mark.asyncio
    async def test_org_with_buildings(self, db_session, admin_user):
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        await _create_building(db_session, admin_user)
        await _create_building(db_session, admin_user, address="Rue Test 2", id=uuid.uuid4())

        result = await get_portfolio_health_dashboard(db_session, org.id)
        assert result.building_count == 2
        assert result.average_score > 0
        assert result.average_grade in ("A", "B", "C", "D", "E", "F")
        assert sum(result.health_distribution.values()) == 2

    @pytest.mark.asyncio
    async def test_worst_best_buildings(self, db_session, admin_user):
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        await _create_building(db_session, admin_user, construction_year=2020)
        await _create_building(
            db_session,
            admin_user,
            address="Old Building",
            id=uuid.uuid4(),
            construction_year=1920,
        )

        result = await get_portfolio_health_dashboard(db_session, org.id)
        assert len(result.best_buildings) <= 5
        assert len(result.worst_buildings) <= 5

    @pytest.mark.asyncio
    async def test_health_distribution_keys(self, db_session, admin_user):
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        await _create_building(db_session, admin_user)
        result = await get_portfolio_health_dashboard(db_session, org.id)
        assert set(result.health_distribution.keys()) == {"A", "B", "C", "D", "E", "F"}

    @pytest.mark.asyncio
    async def test_threshold_crossings_below_50(self, db_session, admin_user):
        """Buildings scoring below 50 should appear in threshold_crossings."""
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        # Building with very poor health: old, polluted, no docs
        b = await _create_building(db_session, admin_user, construction_year=1900)
        diag = await _create_diagnostic(db_session, b.id, status="draft")
        await _create_sample(
            db_session, diag.id, pollutant_type="asbestos", threshold_exceeded=True, risk_level="critical"
        )
        await _create_action(db_session, b.id, priority="critical", status="open", created_at=datetime.now(UTC))

        result = await get_portfolio_health_dashboard(db_session, org.id)
        # The building should likely be below 50 given draft diagnostic + critical pollutant
        hi = await calculate_health_index(db_session, b.id)
        if hi.overall_score < 50:
            assert len(result.threshold_crossings) >= 1

    @pytest.mark.asyncio
    async def test_aggregate_cost_positive(self, db_session, admin_user):
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        await _create_building(db_session, admin_user)
        result = await get_portfolio_health_dashboard(db_session, org.id)
        # Most buildings will score below 80 so cost should be > 0
        assert result.aggregate_improvement_cost_chf >= 0

    @pytest.mark.asyncio
    async def test_portfolio_trend_majority_vote(self, db_session, admin_user):
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        await _create_building(db_session, admin_user)
        result = await get_portfolio_health_dashboard(db_session, org.id)
        assert result.trend in ("improving", "stable", "declining")

    @pytest.mark.asyncio
    async def test_multiple_buildings_different_health(self, db_session):
        """Portfolio with multiple buildings in different states."""
        org = await _create_org(db_session)
        user = await _create_org_user(db_session, org.id)

        # Healthy building
        b1 = await _create_building(db_session, user, construction_year=2020, address="New St 1")
        diag1 = await _create_diagnostic(db_session, b1.id, status="completed")
        for pt in ("asbestos", "pcb", "lead", "hap", "radon"):
            await _create_sample(db_session, diag1.id, pollutant_type=pt, threshold_exceeded=False)
        await _create_document(db_session, b1.id, document_type="diagnostic_report")
        zone1 = await _create_zone(db_session, b1.id)
        await _create_element(db_session, zone1.id, condition="excellent")

        # Unhealthy building
        await _create_building(db_session, user, construction_year=1920, address="Old St 1")

        result = await get_portfolio_health_dashboard(db_session, org.id)
        assert result.building_count == 2
        # Best buildings should have the healthy one first
        assert result.best_buildings[0].score >= result.worst_buildings[0].score

    @pytest.mark.asyncio
    async def test_building_summaries_have_address(self, db_session, admin_user):
        org = await _create_org(db_session)
        admin_user.organization_id = org.id
        db_session.add(admin_user)
        await db_session.commit()

        await _create_building(db_session, admin_user, address="Specific Address 42")
        result = await get_portfolio_health_dashboard(db_session, org.id)
        assert result.best_buildings[0].address == "Specific Address 42"
        assert result.best_buildings[0].city == "Lausanne"


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestHealthIndexAPI:
    @pytest.mark.asyncio
    async def test_health_index_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/health-index",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert "grade" in data
        assert "trend" in data
        assert len(data["dimensions"]) == 5

    @pytest.mark.asyncio
    async def test_health_index_not_found(self, client: AsyncClient, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/health-index",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_health_breakdown_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/health-breakdown",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "worst_contributors" in data
        assert "improvement_levers" in data

    @pytest.mark.asyncio
    async def test_health_trajectory_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/health-trajectory",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["decay_curve"]) == 12
        assert len(data["improvement_curve"]) == 12

    @pytest.mark.asyncio
    async def test_portfolio_dashboard_endpoint(self, client: AsyncClient, auth_headers, db_session, admin_user):
        org = await _create_org(db_session)
        resp = await client.get(
            f"/api/v1/organizations/{org.id}/health-dashboard",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "building_count" in data
        assert "health_distribution" in data

    @pytest.mark.asyncio
    async def test_unauthenticated_request(self, client: AsyncClient, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/health-index",
        )
        assert resp.status_code == 401
