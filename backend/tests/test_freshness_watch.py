"""Tests for the Freshness Watch service and API."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freshness_watch import FreshnessWatchEntry
from app.services.freshness_watch_service import (
    assess_impact,
    dismiss_watch,
    get_critical_for_today,
    get_pending_watches,
    get_watch_dashboard,
    record_change,
)


@pytest.fixture
def user_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# record_change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_change_basic(db: AsyncSession):
    """Recording a change creates a detected entry."""
    entry = await record_change(
        db,
        delta_type="new_rule",
        title="Nouvelle directive OTConst",
        description="Modification du seuil amiante",
        severity="critical",
        canton="VD",
    )
    assert entry is not None
    assert entry.delta_type == "new_rule"
    assert entry.title == "Nouvelle directive OTConst"
    assert entry.severity == "critical"
    assert entry.status == "detected"
    assert entry.canton == "VD"


@pytest.mark.asyncio
async def test_record_change_with_reactions(db: AsyncSession):
    """Recording a change with reactions stores them as JSON."""
    reactions = [
        {"type": "template_invalidation", "target": "suva_notification"},
        {"type": "safe_to_x_refresh", "scope": "all_vd_buildings"},
    ]
    entry = await record_change(
        db,
        delta_type="amended_rule",
        title="Modification seuil PCB",
        severity="warning",
        reactions=reactions,
    )
    assert entry.reactions is not None
    assert len(entry.reactions) == 2
    assert entry.reactions[0]["type"] == "template_invalidation"


@pytest.mark.asyncio
async def test_record_change_with_scope(db: AsyncSession):
    """Recording a change with work families and procedure types."""
    entry = await record_change(
        db,
        delta_type="procedure_change",
        title="Changement procedure OLED",
        affected_work_families=["asbestos_removal", "pcb_removal"],
        affected_procedure_types=["notification_suva", "autorisation_travaux"],
    )
    assert entry.affected_work_families == ["asbestos_removal", "pcb_removal"]
    assert entry.affected_procedure_types == ["notification_suva", "autorisation_travaux"]


# ---------------------------------------------------------------------------
# get_pending_watches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pending_watches_empty(db: AsyncSession):
    """Empty DB returns empty list."""
    entries, total = await get_pending_watches(db)
    assert total == 0
    assert entries == []


@pytest.mark.asyncio
async def test_get_pending_watches_filters(db: AsyncSession):
    """Filters by status, severity, canton."""
    await record_change(db, delta_type="new_rule", title="Rule 1", severity="critical", canton="VD")
    await record_change(db, delta_type="portal_change", title="Portal 1", severity="info", canton="GE")
    await record_change(db, delta_type="form_change", title="Form 1", severity="warning", canton="VD")

    # All detected
    entries, total = await get_pending_watches(db, status="detected")
    assert total == 3

    # Critical only
    entries, total = await get_pending_watches(db, severity="critical")
    assert total == 1
    assert entries[0].title == "Rule 1"

    # VD only
    entries, total = await get_pending_watches(db, canton="VD")
    assert total == 2

    # Portal changes only
    entries, total = await get_pending_watches(db, delta_type="portal_change")
    assert total == 1


# ---------------------------------------------------------------------------
# get_watch_dashboard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_watch_dashboard(db: AsyncSession):
    """Dashboard returns aggregated counts."""
    await record_change(db, delta_type="new_rule", title="R1", severity="critical", canton="VD")
    await record_change(db, delta_type="new_rule", title="R2", severity="warning", canton="VD")
    await record_change(db, delta_type="portal_change", title="P1", severity="info", canton="GE")

    dashboard = await get_watch_dashboard(db)
    assert dashboard["total"] == 3
    assert dashboard["by_severity"]["critical"] == 1
    assert dashboard["by_severity"]["warning"] == 1
    assert dashboard["by_severity"]["info"] == 1
    assert dashboard["by_delta_type"]["new_rule"] == 2
    assert dashboard["by_delta_type"]["portal_change"] == 1
    assert dashboard["by_canton"]["VD"] == 2
    assert dashboard["by_canton"]["GE"] == 1
    assert dashboard["critical_pending"] == 1


# ---------------------------------------------------------------------------
# assess_impact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assess_impact_not_found(db: AsyncSession):
    """Assessing a non-existent entry returns error."""
    result = await assess_impact(db, uuid.uuid4())
    assert "error" in result


@pytest.mark.asyncio
async def test_assess_impact_updates_status(db: AsyncSession):
    """Assessing impact moves status to under_review."""
    entry = await record_change(
        db,
        delta_type="threshold_change",
        title="Seuil radon abaisse",
        severity="critical",
        canton="VD",
        reactions=[{"type": "safe_to_x_refresh", "scope": "all_vd"}],
    )
    result = await assess_impact(db, entry.id)
    assert "error" not in result
    assert result["affected_buildings_estimate"] >= 0
    assert result["reactions_summary"][0]["type"] == "safe_to_x_refresh"

    # Re-read entry to check status
    from sqlalchemy import select

    refreshed = await db.execute(select(FreshnessWatchEntry).where(FreshnessWatchEntry.id == entry.id))
    updated = refreshed.scalar_one()
    assert updated.status == "under_review"


# ---------------------------------------------------------------------------
# dismiss_watch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dismiss_watch(db: AsyncSession, user_id: uuid.UUID):
    """Dismissing sets status, reason, reviewer."""
    entry = await record_change(db, delta_type="dataset_refresh", title="Refresh GEO", severity="info")

    result = await dismiss_watch(db, entry.id, dismissed_by_id=user_id, reason="Pas d'impact")
    assert result is not None
    assert result.status == "dismissed"
    assert result.dismiss_reason == "Pas d'impact"
    assert result.reviewed_by_id == user_id
    assert result.reviewed_at is not None


@pytest.mark.asyncio
async def test_dismiss_watch_not_found(db: AsyncSession, user_id: uuid.UUID):
    """Dismissing a non-existent entry returns None."""
    result = await dismiss_watch(db, uuid.uuid4(), dismissed_by_id=user_id, reason="test")
    assert result is None


# ---------------------------------------------------------------------------
# get_critical_for_today
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_critical_for_today(db: AsyncSession):
    """Returns critical detected/under_review entries only."""
    await record_change(db, delta_type="new_rule", title="Critical 1", severity="critical")
    await record_change(db, delta_type="portal_change", title="Info 1", severity="info")
    await record_change(db, delta_type="form_change", title="Warning 1", severity="warning")

    alerts = await get_critical_for_today(db)
    assert len(alerts) == 1
    assert alerts[0]["title"] == "Critical 1"
    assert alerts[0]["priority"] == "critical"
    assert alerts[0]["type"] == "freshness_watch"


@pytest.mark.asyncio
async def test_get_critical_excludes_applied(db: AsyncSession):
    """Applied entries are not shown in today feed."""
    entry = await record_change(db, delta_type="new_rule", title="Applied", severity="critical")
    entry.status = "applied"
    await db.flush()

    alerts = await get_critical_for_today(db)
    assert len(alerts) == 0


# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_delta_types(db: AsyncSession):
    """All delta types can be recorded."""
    from app.models.freshness_watch import DELTA_TYPES

    for dt in DELTA_TYPES:
        entry = await record_change(db, delta_type=dt, title=f"Test {dt}", severity="info")
        assert entry.delta_type == dt


@pytest.mark.asyncio
async def test_all_severity_levels(db: AsyncSession):
    """All severity levels can be recorded."""
    from app.models.freshness_watch import SEVERITY_LEVELS

    for sev in SEVERITY_LEVELS:
        entry = await record_change(db, delta_type="new_rule", title=f"Sev {sev}", severity=sev)
        assert entry.severity == sev
