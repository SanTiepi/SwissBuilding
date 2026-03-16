"""Tests for the Transaction Readiness service and API."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.schemas.transaction_readiness import (
    CheckSeverity,
    CheckStatus,
    InsuranceRiskTier,
    OverallStatus,
    TransactionType,
)
from app.services.transaction_readiness_service import (
    _compute_score,
    _determine_overall_status,
    _grade_meets_minimum,
    _simulate_trend_score,
    compare_transaction_readiness,
    compute_financing_score,
    compute_insurance_risk_tier,
    evaluate_all_transaction_readiness,
    evaluate_transaction_readiness,
    get_readiness_trend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(
        **defaults,
    )
    db_session.add(building)
    return building


def _make_diagnostic(db_session, building, *, status="completed", **kwargs):
    defaults = {"date_inspection": date(2024, 1, 15)}
    defaults.update(kwargs)
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status=status,
        **defaults,
    )
    db_session.add(diag)
    return diag


def _make_sample(db_session, diag, *, pollutant_type="asbestos", **kwargs):
    defaults = {
        "risk_level": "high",
        "threshold_exceeded": True,
        "concentration": 5.0,
        "unit": "percent_weight",
        "cfst_work_category": "medium",
        "action_required": "remove_planned",
        "waste_disposal_type": "type_e",
    }
    defaults.update(kwargs)
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        **defaults,
    )
    db_session.add(sample)
    return sample


def _make_intervention(db_session, building, *, status="completed", **kwargs):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="removal",
        title="Test intervention",
        status=status,
        **kwargs,
    )
    db_session.add(intervention)
    return intervention


def _make_unknown_issue(db_session, building, *, blocks_readiness=True, status="open", **kwargs):
    issue = UnknownIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        unknown_type="missing_data",
        title="Unknown issue",
        description="Unknown issue details",
        status=status,
        blocks_readiness=blocks_readiness,
        **kwargs,
    )
    db_session.add(issue)
    return issue


def _make_contradiction(db_session, building, *, status="open", **kwargs):
    issue = DataQualityIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        issue_type="contradiction",
        field_name="test_field",
        description="Contradictory data",
        status=status,
        severity="medium",
        **kwargs,
    )
    db_session.add(issue)
    return issue


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestGradeMeetsMinimum:
    def test_a_meets_c(self):
        assert _grade_meets_minimum("A", "C") is True

    def test_b_meets_c(self):
        assert _grade_meets_minimum("B", "C") is True

    def test_c_meets_c(self):
        assert _grade_meets_minimum("C", "C") is True

    def test_d_does_not_meet_c(self):
        assert _grade_meets_minimum("D", "C") is False

    def test_f_does_not_meet_d(self):
        assert _grade_meets_minimum("F", "D") is False

    def test_d_meets_d(self):
        assert _grade_meets_minimum("D", "D") is True


class TestComputeScore:
    def test_all_met(self):
        from app.schemas.transaction_readiness import TransactionCheck

        checks = [
            TransactionCheck(
                check_id="a",
                category="c",
                label="l",
                status=CheckStatus.met,
                severity=CheckSeverity.info,
            ),
            TransactionCheck(
                check_id="b",
                category="c",
                label="l",
                status=CheckStatus.met,
                severity=CheckSeverity.info,
            ),
        ]
        assert _compute_score(checks) == 1.0

    def test_none_met(self):
        from app.schemas.transaction_readiness import TransactionCheck

        checks = [
            TransactionCheck(
                check_id="a",
                category="c",
                label="l",
                status=CheckStatus.unmet,
                severity=CheckSeverity.blocker,
            ),
            TransactionCheck(
                check_id="b",
                category="c",
                label="l",
                status=CheckStatus.unmet,
                severity=CheckSeverity.blocker,
            ),
        ]
        assert _compute_score(checks) == 0.0

    def test_half_met(self):
        from app.schemas.transaction_readiness import TransactionCheck

        checks = [
            TransactionCheck(
                check_id="a",
                category="c",
                label="l",
                status=CheckStatus.met,
                severity=CheckSeverity.info,
            ),
            TransactionCheck(
                check_id="b",
                category="c",
                label="l",
                status=CheckStatus.unmet,
                severity=CheckSeverity.blocker,
            ),
        ]
        assert _compute_score(checks) == 0.5

    def test_empty_checks(self):
        assert _compute_score([]) == 0.0


class TestDetermineOverallStatus:
    def test_blockers_means_not_ready(self):
        from app.schemas.transaction_readiness import TransactionCheck

        checks = [
            TransactionCheck(
                check_id="a",
                category="c",
                label="l",
                status=CheckStatus.unmet,
                severity=CheckSeverity.blocker,
            ),
        ]
        assert _determine_overall_status(checks, ["some blocker"]) == OverallStatus.not_ready

    def test_warnings_means_conditional(self):
        from app.schemas.transaction_readiness import TransactionCheck

        checks = [
            TransactionCheck(
                check_id="a",
                category="c",
                label="l",
                status=CheckStatus.unmet,
                severity=CheckSeverity.warning,
            ),
        ]
        assert _determine_overall_status(checks, []) == OverallStatus.conditional

    def test_all_met_means_ready(self):
        from app.schemas.transaction_readiness import TransactionCheck

        checks = [
            TransactionCheck(
                check_id="a",
                category="c",
                label="l",
                status=CheckStatus.met,
                severity=CheckSeverity.info,
            ),
        ]
        assert _determine_overall_status(checks, []) == OverallStatus.ready


# ---------------------------------------------------------------------------
# Service integration tests (with DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sell_with_no_data(db_session, admin_user):
    """A building with no diagnostics should be not_ready for sell."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.sell)

    assert result.transaction_type == TransactionType.sell
    assert result.overall_status == OverallStatus.not_ready
    assert len(result.blockers) > 0
    assert result.score < 1.0
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_sell_building_not_found(db_session):
    """Evaluating a non-existent building should raise ValueError."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await evaluate_transaction_readiness(db_session, fake_id, TransactionType.sell)


@pytest.mark.asyncio
async def test_insure_with_no_data(db_session, admin_user):
    """A building with no diagnostics should be not_ready for insure."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.insure)

    assert result.transaction_type == TransactionType.insure
    assert result.overall_status == OverallStatus.not_ready
    assert len(result.blockers) > 0


@pytest.mark.asyncio
async def test_finance_with_no_data(db_session, admin_user):
    """A building with no diagnostics should be not_ready for finance."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.finance)

    assert result.transaction_type == TransactionType.finance
    assert result.overall_status == OverallStatus.not_ready
    assert len(result.blockers) > 0


@pytest.mark.asyncio
async def test_lease_with_no_hazards(db_session, admin_user):
    """A building with no hazards should pass lease hazard check."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.lease)

    # No hazards = passes the hazard check, but radon may be a condition
    hazard_check = next((c for c in result.checks if c.check_id == "no_active_hazards"), None)
    assert hazard_check is not None
    assert hazard_check.status == CheckStatus.met


@pytest.mark.asyncio
async def test_lease_with_active_hazards_no_intervention(db_session, admin_user):
    """A building with active hazards and no interventions should be not_ready for lease."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="critical", threshold_exceeded=True)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.lease)

    assert result.overall_status == OverallStatus.not_ready
    assert any("hazard" in b.lower() for b in result.blockers)


@pytest.mark.asyncio
async def test_lease_with_hazards_remediated(db_session, admin_user):
    """A building with hazards that have been remediated should pass hazard check."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="high", threshold_exceeded=True)
    _make_intervention(db_session, building, status="completed")
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.lease)

    hazard_check = next((c for c in result.checks if c.check_id == "no_active_hazards"), None)
    assert hazard_check is not None
    assert hazard_check.status == CheckStatus.met


@pytest.mark.asyncio
async def test_sell_with_critical_unknowns(db_session, admin_user):
    """Critical unknowns should block sell readiness."""
    building = _make_building(db_session, admin_user)
    _make_unknown_issue(db_session, building, blocks_readiness=True)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.sell)

    unknowns_check = next((c for c in result.checks if c.check_id == "no_critical_unknowns"), None)
    assert unknowns_check is not None
    assert unknowns_check.status == CheckStatus.unmet


@pytest.mark.asyncio
async def test_sell_with_contradictions(db_session, admin_user):
    """Unresolved contradictions should create a condition for sell."""
    building = _make_building(db_session, admin_user)
    _make_contradiction(db_session, building)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.sell)

    contradiction_check = next((c for c in result.checks if c.check_id == "no_contradictions"), None)
    assert contradiction_check is not None
    assert contradiction_check.status == CheckStatus.unmet
    assert len(result.conditions) > 0 or len(result.blockers) > 0


@pytest.mark.asyncio
async def test_insure_with_hazard_zones_remediated(db_session, admin_user):
    """Hazard zones with completed interventions should pass insurance check."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="critical", threshold_exceeded=True)
    _make_intervention(db_session, building, status="completed")
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.insure)

    hazard_check = next((c for c in result.checks if c.check_id == "hazard_interventions"), None)
    assert hazard_check is not None
    assert hazard_check.status == CheckStatus.met


@pytest.mark.asyncio
async def test_lease_radon_documented(db_session, admin_user):
    """Radon documented should pass the radon check for lease."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="radon", risk_level="low", threshold_exceeded=False)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.lease)

    radon_check = next((c for c in result.checks if c.check_id == "radon_documented"), None)
    assert radon_check is not None
    assert radon_check.status == CheckStatus.met


@pytest.mark.asyncio
async def test_evaluate_all_transaction_readiness(db_session, admin_user):
    """Evaluating all types should return 4 results."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    results = await evaluate_all_transaction_readiness(db_session, building.id)

    assert len(results) == 4
    types_returned = {r.transaction_type for r in results}
    assert types_returned == {
        TransactionType.sell,
        TransactionType.insure,
        TransactionType.finance,
        TransactionType.lease,
    }


@pytest.mark.asyncio
async def test_score_calculation_for_lease(db_session, admin_user):
    """Score should reflect the fraction of met checks."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    # Add radon sample to pass radon check
    _make_sample(db_session, diag, pollutant_type="radon", risk_level="low", threshold_exceeded=False)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.lease)

    # Score should be between 0 and 1
    assert 0.0 <= result.score <= 1.0
    # At least some checks should be met (no hazards, radon documented, no asbestos)
    met_count = sum(1 for c in result.checks if c.status == CheckStatus.met)
    assert met_count > 0
    expected_score = round(met_count / len(result.checks), 4)
    assert result.score == expected_score


@pytest.mark.asyncio
async def test_recommendations_generated_for_unmet(db_session, admin_user):
    """Recommendations should be generated for unmet checks."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.sell)

    # With no data, there should be recommendations
    assert len(result.recommendations) > 0
    # Recommendations should be actionable strings
    for rec in result.recommendations:
        assert isinstance(rec, str)
        assert len(rec) > 10


@pytest.mark.asyncio
async def test_finance_no_critical_blockers(db_session, admin_user):
    """No critical unknowns should pass finance blocker check."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await evaluate_transaction_readiness(db_session, building.id, TransactionType.finance)

    blocker_check = next((c for c in result.checks if c.check_id == "no_critical_blockers"), None)
    assert blocker_check is not None
    assert blocker_check.status == CheckStatus.met


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_single_transaction_readiness(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/transaction-readiness/sell should return readiness."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/buildings/{building.id}/transaction-readiness/sell",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "sell"
    assert data["overall_status"] in ("ready", "conditional", "not_ready")
    assert "checks" in data
    assert "blockers" in data
    assert "score" in data


@pytest.mark.asyncio
async def test_api_get_all_transaction_readiness(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/transaction-readiness should return all 4 types."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/buildings/{building.id}/transaction-readiness",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    types_returned = {d["transaction_type"] for d in data}
    assert types_returned == {"sell", "insure", "finance", "lease"}


@pytest.mark.asyncio
async def test_api_transaction_readiness_building_not_found(client, auth_headers):
    """GET for non-existent building should return 404."""
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/buildings/{fake_id}/transaction-readiness/sell",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_invalid_transaction_type(client, db_session, admin_user, auth_headers):
    """GET with invalid transaction type should return 422."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/buildings/{building.id}/transaction-readiness/invalid_type",
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Insurance risk tier tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insurance_risk_tier_no_data(db_session, admin_user):
    """Building with no samples should be tier_1 (low risk) except for age."""
    building = _make_building(db_session, admin_user, construction_year=1965)
    await db_session.commit()

    result = await compute_insurance_risk_tier(db_session, building.id)

    assert result.building_id == building.id
    assert result.pollutant_diversity == 0
    assert result.threshold_exceedance_count == 0
    assert result.intervention_coverage == 1.0
    assert result.building_age_factor == 1.5  # pre-1990
    # Only age factor contributes: 1.0 * 0.20 = 0.20 → tier_1
    assert result.risk_tier == InsuranceRiskTier.tier_1


@pytest.mark.asyncio
async def test_insurance_risk_tier_post_1990(db_session, admin_user):
    """Post-1990 building with no pollutants should be tier_1."""
    building = _make_building(db_session, admin_user, construction_year=2005)
    await db_session.commit()

    result = await compute_insurance_risk_tier(db_session, building.id)

    assert result.building_age_factor == 1.0
    assert result.risk_tier == InsuranceRiskTier.tier_1
    assert result.raw_score == 0.0


@pytest.mark.asyncio
async def test_insurance_risk_tier_high_risk(db_session, admin_user):
    """Building with multiple pollutants, no interventions should be high tier."""
    building = _make_building(db_session, admin_user, construction_year=1960)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="critical", threshold_exceeded=True)
    _make_sample(db_session, diag, pollutant_type="pcb", risk_level="high", threshold_exceeded=True)
    _make_sample(db_session, diag, pollutant_type="lead", risk_level="high", threshold_exceeded=True)
    _make_sample(db_session, diag, pollutant_type="hap", risk_level="high", threshold_exceeded=True)
    await db_session.commit()

    result = await compute_insurance_risk_tier(db_session, building.id)

    assert result.pollutant_diversity == 4
    assert result.threshold_exceedance_count == 4
    assert result.intervention_coverage == 0.0
    assert result.risk_tier in (InsuranceRiskTier.tier_3, InsuranceRiskTier.tier_4)


@pytest.mark.asyncio
async def test_insurance_risk_tier_with_interventions(db_session, admin_user):
    """Completed interventions should lower the risk tier."""
    building = _make_building(db_session, admin_user, construction_year=1970)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="high", threshold_exceeded=True)
    _make_intervention(db_session, building, status="completed")
    await db_session.commit()

    result = await compute_insurance_risk_tier(db_session, building.id)

    assert result.intervention_coverage == 1.0
    # With intervention coverage at 100%, intervention_risk = 0
    assert result.risk_tier in (InsuranceRiskTier.tier_1, InsuranceRiskTier.tier_2)


@pytest.mark.asyncio
async def test_insurance_risk_tier_building_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await compute_insurance_risk_tier(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Financing score breakdown tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_financing_score_no_data(db_session, admin_user):
    """Building with no data should have low scores."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await compute_financing_score(db_session, building.id)

    assert result.building_id == building.id
    assert 0.0 <= result.documentation_score <= 1.0
    assert result.risk_mitigation_score == 1.0  # No hazards = full mitigation
    assert result.regulatory_compliance_score == 0.0  # No completed diags
    assert 0.0 <= result.overall_score <= 1.0


@pytest.mark.asyncio
async def test_financing_score_with_completed_diags(db_session, admin_user):
    """Building with completed diagnostics should have higher regulatory score."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building, status="completed")
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="low", threshold_exceeded=False)
    _make_sample(db_session, diag, pollutant_type="pcb", risk_level="low", threshold_exceeded=False)
    await db_session.commit()

    result = await compute_financing_score(db_session, building.id)

    # 2 pollutant types covered out of 5 = 0.4
    assert result.regulatory_compliance_score == 0.4
    assert result.risk_mitigation_score == 1.0  # No hazards


@pytest.mark.asyncio
async def test_financing_score_with_hazards_and_interventions(db_session, admin_user):
    """Risk mitigation score should reflect intervention completion."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building, status="completed")
    _make_sample(db_session, diag, pollutant_type="asbestos", risk_level="high", threshold_exceeded=True)
    _make_sample(db_session, diag, pollutant_type="pcb", risk_level="critical", threshold_exceeded=True)
    _make_intervention(db_session, building, status="completed")
    await db_session.commit()

    result = await compute_financing_score(db_session, building.id)

    # 1 completed intervention for 2 hazard samples = 0.5
    assert result.risk_mitigation_score == 0.5


@pytest.mark.asyncio
async def test_financing_score_building_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await compute_financing_score(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Comparative readiness tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_two_buildings(db_session, admin_user):
    """Comparing 2 buildings should return 4 ComparativeReadiness objects."""
    b1 = _make_building(db_session, admin_user)
    b2 = _make_building(db_session, admin_user)
    await db_session.commit()

    results = await compare_transaction_readiness(db_session, [b1.id, b2.id])

    assert len(results) == 4  # One per transaction type
    for comp in results:
        assert len(comp.rankings) == 2
        ranks = [r.rank for r in comp.rankings]
        assert sorted(ranks) == [1, 2]


@pytest.mark.asyncio
async def test_compare_too_few_buildings(db_session):
    """Comparing fewer than 2 buildings should raise ValueError."""
    with pytest.raises(ValueError, match="At least 2"):
        await compare_transaction_readiness(db_session, [uuid.uuid4()])


@pytest.mark.asyncio
async def test_compare_too_many_buildings(db_session):
    """Comparing more than 10 buildings should raise ValueError."""
    ids = [uuid.uuid4() for _ in range(11)]
    with pytest.raises(ValueError, match="At most 10"):
        await compare_transaction_readiness(db_session, ids)


@pytest.mark.asyncio
async def test_compare_building_not_found(db_session, admin_user):
    """Comparing with a non-existent building should raise ValueError."""
    b1 = _make_building(db_session, admin_user)
    await db_session.commit()

    with pytest.raises(ValueError, match="not found"):
        await compare_transaction_readiness(db_session, [b1.id, uuid.uuid4()])


@pytest.mark.asyncio
async def test_compare_rankings_sorted_by_score(db_session, admin_user):
    """Rankings should be sorted by score descending (rank 1 = best)."""
    b1 = _make_building(db_session, admin_user)
    b2 = _make_building(db_session, admin_user)
    # Give b2 a completed diagnostic to improve its lease score
    diag = _make_diagnostic(db_session, b2, status="completed")
    _make_sample(db_session, diag, pollutant_type="radon", risk_level="low", threshold_exceeded=False)
    await db_session.commit()

    results = await compare_transaction_readiness(db_session, [b1.id, b2.id])

    # For lease, b2 should rank higher (has radon documented)
    lease_comp = next(c for c in results if c.transaction_type == TransactionType.lease)
    assert lease_comp.rankings[0].score >= lease_comp.rankings[1].score
    assert lease_comp.rankings[0].rank == 1


# ---------------------------------------------------------------------------
# Readiness trend tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readiness_trend_basic(db_session, admin_user):
    """Trend should return months+1 data points."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await get_readiness_trend(db_session, building.id, TransactionType.sell, months=6)

    assert result.building_id == building.id
    assert result.transaction_type == TransactionType.sell
    assert len(result.data_points) == 7  # 6 months back + current


@pytest.mark.asyncio
async def test_readiness_trend_has_valid_months(db_session, admin_user):
    """Each data point should have a valid YYYY-MM month label."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await get_readiness_trend(db_session, building.id, TransactionType.lease, months=3)

    for dp in result.data_points:
        assert len(dp.month) == 7  # YYYY-MM
        assert dp.month[4] == "-"
        assert 0.0 <= dp.score <= 1.0
        assert dp.overall_status in ("ready", "conditional", "not_ready")


@pytest.mark.asyncio
async def test_readiness_trend_building_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await get_readiness_trend(db_session, uuid.uuid4(), TransactionType.sell)


# ---------------------------------------------------------------------------
# Unit test for _simulate_trend_score
# ---------------------------------------------------------------------------


class TestSimulateTrendScore:
    def test_sell_no_data(self):
        score, status = _simulate_trend_score(
            TransactionType.sell,
            completed_diags=[],
            hazard_samples=[],
            completed_interventions=[],
            all_samples=[],
        )
        assert score == 0.5  # 1/2 checks met (no hazards passes)
        assert status == OverallStatus.not_ready

    def test_lease_all_met(self):
        """Lease with no hazards and radon documented."""

        class FakeSample:
            pollutant_type = "radon"

        score, status = _simulate_trend_score(
            TransactionType.lease,
            completed_diags=[],
            hazard_samples=[],
            completed_interventions=[],
            all_samples=[FakeSample()],
        )
        assert score == 1.0
        assert status == OverallStatus.ready


# ---------------------------------------------------------------------------
# API tests for new endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_insurance_risk_tier(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/insurance-risk-tier should return assessment."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/buildings/{building.id}/insurance-risk-tier",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_tier"] in ("tier_1", "tier_2", "tier_3", "tier_4")
    assert "pollutant_diversity" in data
    assert "raw_score" in data


@pytest.mark.asyncio
async def test_api_financing_score(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/financing-score should return breakdown."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/buildings/{building.id}/financing-score",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "documentation_score" in data
    assert "risk_mitigation_score" in data
    assert "regulatory_compliance_score" in data
    assert "overall_score" in data
    assert 0.0 <= data["overall_score"] <= 1.0


@pytest.mark.asyncio
async def test_api_compare_readiness(client, db_session, admin_user, auth_headers):
    """POST /transaction-readiness/compare should return comparative view."""
    b1 = _make_building(db_session, admin_user)
    b2 = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.post(
        "/api/v1/transaction-readiness/compare",
        json={"building_ids": [str(b1.id), str(b2.id)]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    for comp in data:
        assert "transaction_type" in comp
        assert "rankings" in comp
        assert len(comp["rankings"]) == 2


@pytest.mark.asyncio
async def test_api_readiness_trend(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/readiness-trend/sell should return trend data."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/buildings/{building.id}/readiness-trend/sell?months=3",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "sell"
    assert len(data["data_points"]) == 4  # 3 months back + current


@pytest.mark.asyncio
async def test_api_insurance_risk_tier_not_found(client, auth_headers):
    """GET for non-existent building should return 404."""
    response = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/insurance-risk-tier",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_compare_validation(client, auth_headers):
    """POST with only 1 building should return 422."""
    response = await client.post(
        "/api/v1/transaction-readiness/compare",
        json={"building_ids": [str(uuid.uuid4())]},
        headers=auth_headers,
    )
    assert response.status_code == 422
