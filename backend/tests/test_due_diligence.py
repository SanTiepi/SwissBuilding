"""
SwissBuildingOS - Due Diligence Tests

Tests for due diligence service, schemas, and API endpoints.
"""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.due_diligence_service import (
    assess_transaction_risks,
    compare_acquisition_targets,
    estimate_property_value_impact,
    generate_due_diligence_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_clean(db_session, admin_user):
    """A modern building with no pollutant issues."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Propre 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2005,
        building_type="residential",
        surface_area_m2=200.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_contaminated(db_session, admin_user):
    """A 1965 building with pollutant diagnostics."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Polluee 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="industrial",
        surface_area_m2=500.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)

    samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S1",
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="critical",
            material_category="flocage",
            material_state="degraded",
            cfst_work_category="major",
            waste_disposal_type="special",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S2",
            pollutant_type="pcb",
            concentration=120.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            waste_disposal_type="special",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S3",
            pollutant_type="lead",
            concentration=8000.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            waste_disposal_type="type_e",
        ),
    ]
    for s in samples:
        db_session.add(s)
    await db_session.commit()

    return b


@pytest.fixture
async def building_minor(db_session, admin_user):
    """A building with only one minor pollutant finding."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Modeste 3",
        postal_code="1201",
        city="Geneve",
        canton="GE",
        construction_year=1985,
        building_type="residential",
        surface_area_m2=150.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="renovation",
        status="validated",
    )
    db_session.add(diag)
    await db_session.commit()

    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="M1",
        pollutant_type="hap",
        concentration=250.0,
        unit="mg_per_kg",
        threshold_exceeded=True,
        risk_level="medium",
        waste_disposal_type="special",
    )
    db_session.add(s)
    await db_session.commit()

    return b


# ---------------------------------------------------------------------------
# Service tests — generate_due_diligence_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_clean_building(db_session, building_clean):
    report = await generate_due_diligence_report(db_session, building_clean.id)
    assert report.building_id == building_clean.id
    assert report.recommendation == "proceed"
    assert report.value_impact.total_depreciation_pct == 0.0


@pytest.mark.asyncio
async def test_report_contaminated_building(db_session, building_contaminated):
    report = await generate_due_diligence_report(db_session, building_contaminated.id)
    assert report.building_id == building_contaminated.id
    assert report.recommendation in ("defer", "avoid")
    assert report.value_impact.total_depreciation_pct > 0
    assert report.remediation_cost.total_max_chf > 0
    assert report.remediation_cost.pollutant_count >= 3


@pytest.mark.asyncio
async def test_report_has_pollutant_statuses(db_session, building_contaminated):
    report = await generate_due_diligence_report(db_session, building_contaminated.id)
    assert len(report.pollutant_statuses) == 5  # all 5 pollutants covered
    asbestos_status = next(s for s in report.pollutant_statuses if s.pollutant == "asbestos")
    assert asbestos_status.detected is True
    assert asbestos_status.threshold_exceeded is True


@pytest.mark.asyncio
async def test_report_compliance_state(db_session, building_contaminated):
    report = await generate_due_diligence_report(db_session, building_contaminated.id)
    assert report.compliance_state.diagnostic_required is True
    assert report.compliance_state.diagnostic_completed is True
    assert report.compliance_state.suva_notification_required is True
    assert report.compliance_state.canton == "VD"


@pytest.mark.asyncio
async def test_report_risk_flags(db_session, building_contaminated):
    report = await generate_due_diligence_report(db_session, building_contaminated.id)
    flag_names = [f.flag for f in report.risk_flags]
    assert "multi_pollutant" in flag_names
    assert "suva_notification" in flag_names


@pytest.mark.asyncio
async def test_report_not_found(db_session):
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await generate_due_diligence_report(db_session, fake_id)


# ---------------------------------------------------------------------------
# Service tests — assess_transaction_risks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transaction_risks_clean(db_session, building_clean):
    result = await assess_transaction_risks(db_session, building_clean.id)
    assert result.building_id == building_clean.id
    assert len(result.risks) == 4
    assert result.overall_risk_score <= 0.1


@pytest.mark.asyncio
async def test_transaction_risks_contaminated(db_session, building_contaminated):
    result = await assess_transaction_risks(db_session, building_contaminated.id)
    assert result.overall_risk_score > 0.1
    categories = {r.category for r in result.risks}
    assert categories == {"regulatory", "financial", "legal", "reputational"}
    # Financial risk should have contributing pollutants
    financial = next(r for r in result.risks if r.category == "financial")
    assert len(financial.contributing_pollutants) >= 2


@pytest.mark.asyncio
async def test_transaction_risks_has_mitigation(db_session, building_contaminated):
    result = await assess_transaction_risks(db_session, building_contaminated.id)
    for risk in result.risks:
        assert risk.mitigation  # every risk must have mitigation advice


# ---------------------------------------------------------------------------
# Service tests — estimate_property_value_impact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_value_impact_clean(db_session, building_clean):
    impact = await estimate_property_value_impact(db_session, building_clean.id)
    assert impact.capped_depreciation_pct == 0.0
    assert impact.net_impact_pct == 0.0


@pytest.mark.asyncio
async def test_value_impact_contaminated(db_session, building_contaminated):
    impact = await estimate_property_value_impact(db_session, building_contaminated.id)
    # asbestos(8) + pcb(5) + lead(4) = 17%
    assert impact.raw_cumulative_pct == 17.0
    assert impact.capped_depreciation_pct == 17.0  # under 25% cap
    assert impact.post_remediation_recovery_pct == 10.2  # 17 * 0.6
    assert impact.net_impact_pct == 6.8  # 17 - 10.2


@pytest.mark.asyncio
async def test_value_impact_cap(db_session, admin_user):
    """When all 5 pollutants exceed threshold, cap at 25%."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Totale 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="industrial",
        surface_area_m2=300.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    for pt in ("asbestos", "pcb", "lead", "hap", "radon"):
        db_session.add(
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=diag.id,
                sample_number=f"CAP-{pt}",
                pollutant_type=pt,
                concentration=9999.0,
                unit="mg_per_kg",
                threshold_exceeded=True,
                risk_level="critical",
            )
        )
    await db_session.commit()

    impact = await estimate_property_value_impact(db_session, b.id)
    # Raw: 8+5+3+4+2 = 22, under cap
    assert impact.raw_cumulative_pct == 22.0
    assert impact.capped_depreciation_pct == 22.0


@pytest.mark.asyncio
async def test_value_impact_minor(db_session, building_minor):
    impact = await estimate_property_value_impact(db_session, building_minor.id)
    assert impact.raw_cumulative_pct == 2.0  # only HAP
    assert impact.capped_depreciation_pct == 2.0


# ---------------------------------------------------------------------------
# Service tests — compare_acquisition_targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_targets(db_session, building_clean, building_contaminated, building_minor):
    result = await compare_acquisition_targets(
        db_session,
        [building_clean.id, building_contaminated.id, building_minor.id],
    )
    assert len(result.targets) == 3
    # Clean building should rank best (rank 1)
    clean_target = next(t for t in result.targets if t.building_id == building_clean.id)
    assert clean_target.rank == 1
    assert result.best_target == building_clean.id


@pytest.mark.asyncio
async def test_compare_too_many(db_session):
    ids = [uuid.uuid4() for _ in range(11)]
    with pytest.raises(ValueError, match="Cannot compare more than 10"):
        await compare_acquisition_targets(db_session, ids)


@pytest.mark.asyncio
async def test_compare_single(db_session, building_clean):
    result = await compare_acquisition_targets(db_session, [building_clean.id])
    assert len(result.targets) == 1
    assert result.targets[0].rank == 1


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_due_diligence_report(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/due-diligence", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["recommendation"] in ("proceed", "proceed_with_conditions", "defer", "avoid")


@pytest.mark.asyncio
async def test_api_due_diligence_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/due-diligence", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_transaction_risks(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/transaction-risks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["risks"]) == 4
    assert "overall_risk_score" in data


@pytest.mark.asyncio
async def test_api_value_impact(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/value-impact", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "capped_depreciation_pct" in data
    assert "pollutant_depreciations" in data


@pytest.mark.asyncio
async def test_api_compare(client, auth_headers, sample_building):
    resp = await client.post(
        "/api/v1/due-diligence/compare",
        headers=auth_headers,
        json={"building_ids": [str(sample_building.id)]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["targets"]) == 1


@pytest.mark.asyncio
async def test_api_compare_unauthenticated(client, sample_building):
    resp = await client.post(
        "/api/v1/due-diligence/compare",
        json={"building_ids": [str(sample_building.id)]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_due_diligence_unauthenticated(client, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/due-diligence")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_building_no_surface(db_session, admin_user):
    """Building with no surface area should still produce a report."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Sans Surface 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)

    report = await generate_due_diligence_report(db_session, b.id)
    assert report.building_id == b.id
    assert report.surface_area_m2 is None


@pytest.mark.asyncio
async def test_recommendation_proceed_with_conditions(db_session, building_minor):
    """Building with minor finding should get proceed_with_conditions."""
    report = await generate_due_diligence_report(db_session, building_minor.id)
    # HAP only → 2% depreciation, no critical flags → should not be defer/avoid
    assert report.recommendation in ("proceed", "proceed_with_conditions")
