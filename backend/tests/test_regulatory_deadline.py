"""Tests for regulatory deadline service and API routes."""

import uuid
from datetime import date, datetime

import pytest

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.regulatory_deadline_service import (
    check_compliance_expiry,
    get_building_deadlines,
    get_deadline_calendar,
    get_portfolio_deadlines,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    return Building(**defaults)


def _make_diagnostic(building_id, diagnostic_type="asbestos", date_report=None, **kwargs):
    return Diagnostic(
        id=kwargs.pop("id", uuid.uuid4()),
        building_id=building_id,
        diagnostic_type=diagnostic_type,
        date_report=date_report,
        status="completed",
        **kwargs,
    )


def _make_sample(diagnostic_id, pollutant_type="radon", concentration=500.0, **kwargs):
    return Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=kwargs.pop("sample_number", "S-001"),
        pollutant_type=pollutant_type,
        concentration=concentration,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Asbestos 3-year cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asbestos_expired(db_session, admin_user):
    """Asbestos diagnostic > 3 years old → overdue."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2020, 1, 15))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert len(asbestos_dl) == 1
    assert asbestos_dl[0].due_date == date(2023, 1, 15)
    assert asbestos_dl[0].status == "overdue"
    assert result.overdue_count >= 1


@pytest.mark.asyncio
async def test_asbestos_due_soon(db_session, admin_user):
    """Asbestos diagnostic due within 30 days → critical."""
    building = _make_building(admin_user.id, construction_year=1985)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2021, 7, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 15))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert len(asbestos_dl) == 1
    assert asbestos_dl[0].due_date == date(2024, 7, 1)
    assert asbestos_dl[0].status == "critical"


@pytest.mark.asyncio
async def test_asbestos_ok(db_session, admin_user):
    """Asbestos diagnostic recent → ok."""
    building = _make_building(admin_user.id, construction_year=1985)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2024, 1, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert len(asbestos_dl) == 1
    assert asbestos_dl[0].status == "ok"


# ---------------------------------------------------------------------------
# 2. PCB 5-year cycle for 1955-1975 buildings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pcb_within_range(db_session, admin_user):
    """PCB deadline generated for 1955-1975 building."""
    building = _make_building(admin_user.id, construction_year=1965)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "pcb", date_report=date(2019, 3, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    pcb_dl = [d for d in result.deadlines if d.pollutant_type == "pcb"]
    assert len(pcb_dl) == 1
    assert pcb_dl[0].due_date == date(2024, 3, 1)
    assert pcb_dl[0].status == "overdue"


@pytest.mark.asyncio
async def test_pcb_outside_range_no_deadline(db_session, admin_user):
    """PCB: building outside 1955-1975 → no PCB deadline even with diagnostic."""
    building = _make_building(admin_user.id, construction_year=1990)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "pcb", date_report=date(2019, 3, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    pcb_dl = [d for d in result.deadlines if d.pollutant_type == "pcb"]
    assert len(pcb_dl) == 0


# ---------------------------------------------------------------------------
# 3. Radon 10-year cycle only if >300 Bq/m³
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radon_high_reading(db_session, admin_user):
    """Radon with sample >300 → generates deadline."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "radon", date_report=date(2015, 6, 1))
    db_session.add(diag)
    sample = _make_sample(diag.id, pollutant_type="radon", concentration=500.0)
    db_session.add(sample)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    radon_dl = [d for d in result.deadlines if d.pollutant_type == "radon"]
    assert len(radon_dl) == 1
    assert radon_dl[0].due_date == date(2025, 6, 1)
    assert radon_dl[0].status == "upcoming"


@pytest.mark.asyncio
async def test_radon_low_reading_no_deadline(db_session, admin_user):
    """Radon with sample <=300 → no deadline."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "radon", date_report=date(2015, 6, 1))
    db_session.add(diag)
    sample = _make_sample(diag.id, pollutant_type="radon", concentration=200.0)
    db_session.add(sample)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    radon_dl = [d for d in result.deadlines if d.pollutant_type == "radon"]
    assert len(radon_dl) == 0


# ---------------------------------------------------------------------------
# 4. Missing initial diagnostic → critical
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_initial_asbestos(db_session, admin_user):
    """Pre-1991 building with no asbestos diagnostic → critical missing deadline."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    missing = [d for d in result.deadlines if d.deadline_type == "missing_initial" and d.pollutant_type == "asbestos"]
    assert len(missing) == 1
    assert missing[0].status == "critical"


@pytest.mark.asyncio
async def test_missing_initial_pcb(db_session, admin_user):
    """1955-1975 building with no PCB diagnostic → critical missing deadline."""
    building = _make_building(admin_user.id, construction_year=1965)
    db_session.add(building)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    missing = [d for d in result.deadlines if d.deadline_type == "missing_initial" and d.pollutant_type == "pcb"]
    assert len(missing) == 1
    assert missing[0].status == "critical"


# ---------------------------------------------------------------------------
# 5. Building outside risk period → no asbestos deadline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_1991_no_asbestos_deadline(db_session, admin_user):
    """Building built after 1991 → no asbestos deadline."""
    building = _make_building(admin_user.id, construction_year=2005)
    db_session.add(building)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert len(asbestos_dl) == 0


# ---------------------------------------------------------------------------
# 6. Multiple pollutants → sorted by urgency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_pollutants_sorted(db_session, admin_user):
    """Building with multiple diagnostics → deadlines sorted by status then date."""
    building = _make_building(admin_user.id, construction_year=1965)
    db_session.add(building)

    # Asbestos: overdue
    diag1 = _make_diagnostic(building.id, "asbestos", date_report=date(2020, 1, 1))
    db_session.add(diag1)

    # PCB: upcoming
    diag2 = _make_diagnostic(building.id, "pcb", date_report=date(2023, 6, 1))
    db_session.add(diag2)

    # Lead: ok
    diag3 = _make_diagnostic(building.id, "lead", date_report=date(2024, 1, 1))
    db_session.add(diag3)

    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    assert len(result.deadlines) >= 3
    # First deadline should be the most urgent
    assert result.deadlines[0].status == "overdue"
    # Verify ordering: overdue < critical < warning < upcoming < ok
    statuses = [d.status for d in result.deadlines]
    status_order = {"overdue": 0, "critical": 1, "warning": 2, "upcoming": 3, "ok": 4}
    numeric = [status_order[s] for s in statuses]
    assert numeric == sorted(numeric)


# ---------------------------------------------------------------------------
# 7. Portfolio aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_aggregation(db_session, admin_user):
    """Portfolio with 3 buildings, mixed statuses."""
    buildings = []
    for i in range(3):
        b = _make_building(
            admin_user.id,
            address=f"Rue Test {i + 1}",
            construction_year=1970 + i * 10,
        )
        db_session.add(b)
        buildings.append(b)

    # Building 0 (1970): overdue asbestos
    diag0 = _make_diagnostic(buildings[0].id, "asbestos", date_report=date(2020, 1, 1))
    db_session.add(diag0)

    # Building 1 (1980): ok asbestos
    diag1 = _make_diagnostic(buildings[1].id, "asbestos", date_report=date(2024, 1, 1))
    db_session.add(diag1)

    # Building 2 (1990): ok asbestos
    diag2 = _make_diagnostic(buildings[2].id, "asbestos", date_report=date(2024, 3, 1))
    db_session.add(diag2)

    await db_session.commit()

    result = await get_portfolio_deadlines(db_session, today=date(2024, 6, 1))
    assert result.total_buildings == 3
    assert result.total_overdue >= 1
    assert len(result.buildings_at_risk) >= 1


# ---------------------------------------------------------------------------
# 8. Calendar view
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calendar_correct_month(db_session, admin_user):
    """Calendar places deadline in correct month."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2022, 7, 15))
    db_session.add(diag)
    await db_session.commit()

    calendar = await get_deadline_calendar(db_session, building.id, 2025, today=date(2024, 6, 1))
    assert calendar.year == 2025
    assert len(calendar.months) == 12

    # Asbestos due 2025-07-15 → should appear in month 7
    july = calendar.months[6]  # 0-indexed
    assert july.month == 7
    assert len(july.deadlines) >= 1
    assert any(d.pollutant_type == "asbestos" for d in july.deadlines)

    # Other months should not have this deadline
    june = calendar.months[5]
    assert not any(d.pollutant_type == "asbestos" and d.due_date.month == 7 for d in june.deadlines)


# ---------------------------------------------------------------------------
# 9. Compliance artefact expiry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_expiry_30_day_window(db_session, admin_user):
    """Artefact expiring within 30 days → critical."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building.id,
        artefact_type="suva_notification",
        status="submitted",
        title="SUVA Notification",
        expires_at=datetime(2024, 6, 20),
    )
    db_session.add(artefact)
    await db_session.commit()

    items = await check_compliance_expiry(db_session, building.id, today=date(2024, 6, 1))
    assert len(items) == 1
    assert items[0].status == "critical"
    assert items[0].days_remaining == 19


@pytest.mark.asyncio
async def test_compliance_expiry_60_day_window(db_session, admin_user):
    """Artefact expiring within 60 days → warning."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building.id,
        artefact_type="canton_permit",
        status="submitted",
        title="Canton Permit",
        expires_at=datetime(2024, 7, 20),
    )
    db_session.add(artefact)
    await db_session.commit()

    items = await check_compliance_expiry(db_session, building.id, today=date(2024, 6, 1))
    assert len(items) == 1
    assert items[0].status == "warning"


@pytest.mark.asyncio
async def test_compliance_expiry_90_day_window(db_session, admin_user):
    """Artefact expiring within 90 days → warning."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building.id,
        artefact_type="oled_certificate",
        status="submitted",
        title="OLED Certificate",
        expires_at=datetime(2024, 8, 25),
    )
    db_session.add(artefact)
    await db_session.commit()

    items = await check_compliance_expiry(db_session, building.id, today=date(2024, 6, 1))
    assert len(items) == 1
    assert items[0].status == "warning"


@pytest.mark.asyncio
async def test_compliance_expiry_fallback_submitted_at(db_session, admin_user):
    """No expires_at → falls back to submitted_at + 2 years."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building.id,
        artefact_type="suva_notification",
        status="submitted",
        title="SUVA Notification",
        submitted_at=datetime(2022, 7, 1),
    )
    db_session.add(artefact)
    await db_session.commit()

    items = await check_compliance_expiry(db_session, building.id, today=date(2024, 6, 1))
    assert len(items) == 1
    assert items[0].expires_at == date(2024, 7, 1)


# ---------------------------------------------------------------------------
# 10. Edge: building with no diagnostics at all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_diagnostics_pre_1991(db_session, admin_user):
    """Pre-1991 building with no diagnostics → missing initial deadlines."""
    building = _make_building(admin_user.id, construction_year=1975)
    db_session.add(building)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    missing = [d for d in result.deadlines if d.deadline_type == "missing_initial"]
    # Should have missing asbestos and PCB (1975 is in 1955-1975 range)
    pollutants = {d.pollutant_type for d in missing}
    assert "asbestos" in pollutants
    assert "pcb" in pollutants


@pytest.mark.asyncio
async def test_no_diagnostics_post_1991(db_session, admin_user):
    """Post-1991 building with no diagnostics → no missing initial (no risk-period filter match)."""
    building = _make_building(admin_user.id, construction_year=2010)
    db_session.add(building)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    missing = [d for d in result.deadlines if d.deadline_type == "missing_initial"]
    assert len(missing) == 0


# ---------------------------------------------------------------------------
# 11. Edge: diagnostic with no date → skip gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostic_no_date_skipped(db_session, admin_user):
    """Diagnostic without date_report or date_inspection → no deadline generated."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=None)
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    # Should get a missing_initial since the diagnostic has no usable date
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert len(asbestos_dl) == 1
    assert asbestos_dl[0].deadline_type == "missing_initial"


# ---------------------------------------------------------------------------
# 12. Status transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_transition_overdue(db_session, admin_user):
    """due_date < today → overdue."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2020, 1, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 1, 2))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert asbestos_dl[0].status == "overdue"


@pytest.mark.asyncio
async def test_status_transition_critical(db_session, admin_user):
    """due within 30 days → critical."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2021, 7, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 5))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert asbestos_dl[0].status == "critical"


@pytest.mark.asyncio
async def test_status_transition_warning(db_session, admin_user):
    """due within 90 days → warning."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2021, 7, 1))
    db_session.add(diag)
    await db_session.commit()

    # Due date is 2024-07-01, today is 2024-04-15 → 77 days → warning
    result = await get_building_deadlines(db_session, building.id, today=date(2024, 4, 15))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert asbestos_dl[0].status == "warning"


@pytest.mark.asyncio
async def test_status_transition_upcoming(db_session, admin_user):
    """due within 365 days → upcoming."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2021, 7, 1))
    db_session.add(diag)
    await db_session.commit()

    # Due date is 2024-07-01, today is 2023-10-01 → 274 days → upcoming
    result = await get_building_deadlines(db_session, building.id, today=date(2023, 10, 1))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert asbestos_dl[0].status == "upcoming"


@pytest.mark.asyncio
async def test_status_transition_ok(db_session, admin_user):
    """due > 365 days → ok."""
    building = _make_building(admin_user.id, construction_year=1980)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "asbestos", date_report=date(2024, 1, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 1, 2))
    asbestos_dl = [d for d in result.deadlines if d.pollutant_type == "asbestos"]
    assert asbestos_dl[0].status == "ok"


# ---------------------------------------------------------------------------
# 13. API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_building_deadlines(client, auth_headers, sample_building):
    """GET /api/v1/buildings/{id}/regulatory-deadlines returns correct structure."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/regulatory-deadlines",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "building_id" in data
    assert "deadlines" in data
    assert "overdue_count" in data
    assert "critical_count" in data


@pytest.mark.asyncio
async def test_api_portfolio_deadlines(client, auth_headers, sample_building):
    """GET /api/v1/portfolio/regulatory-deadlines returns correct structure."""
    resp = await client.get(
        "/api/v1/portfolio/regulatory-deadlines",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "total_overdue" in data
    assert "upcoming_by_month" in data


@pytest.mark.asyncio
async def test_api_deadline_calendar(client, auth_headers, sample_building):
    """GET /api/v1/buildings/{id}/deadline-calendar/2025 returns 12 months."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/deadline-calendar/2025",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2025
    assert len(data["months"]) == 12


@pytest.mark.asyncio
async def test_api_compliance_expiry(client, auth_headers, sample_building):
    """GET /api/v1/buildings/{id}/compliance-expiry returns list."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance-expiry",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 14. HAP assessment 5-year cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hap_deadline(db_session, admin_user):
    """HAP diagnostic generates 5-year deadline."""
    building = _make_building(admin_user.id, construction_year=1970)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "hap", date_report=date(2020, 3, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    hap_dl = [d for d in result.deadlines if d.pollutant_type == "hap"]
    assert len(hap_dl) == 1
    assert hap_dl[0].due_date == date(2025, 3, 1)
    assert hap_dl[0].status == "upcoming"


# ---------------------------------------------------------------------------
# 15. Lead assessment 5-year cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lead_deadline(db_session, admin_user):
    """Lead diagnostic generates 5-year deadline regardless of construction year."""
    building = _make_building(admin_user.id, construction_year=2000)
    db_session.add(building)
    diag = _make_diagnostic(building.id, "lead", date_report=date(2019, 6, 1))
    db_session.add(diag)
    await db_session.commit()

    result = await get_building_deadlines(db_session, building.id, today=date(2024, 6, 1))
    lead_dl = [d for d in result.deadlines if d.pollutant_type == "lead"]
    assert len(lead_dl) == 1
    assert lead_dl[0].due_date == date(2024, 6, 1)
    # Exactly on due date → critical (0 days remaining, <= 30)
    assert lead_dl[0].status == "critical"
