"""SwissRules Watch — tests (models, schemas, service, API)."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.api.swiss_rules_watch import router as srw_router
from app.main import app
from app.models.communal_adapter import CommunalAdapterProfile
from app.models.communal_override import CommunalRuleOverride
from app.models.rule_change_event import RuleChangeEvent
from app.models.swiss_rules_source import RuleSource
from app.schemas.swiss_rules_watch import (
    BuildingCommuneContext,
    CommunalAdapterRead,
    CommunalOverrideRead,
    RuleChangeEventCreate,
    RuleChangeEventRead,
    RuleSourceCreate,
    RuleSourceRead,
)
from app.services.swiss_rules_watch_service import (
    _compute_freshness,
    get_building_commune_context,
    get_commune_overrides,
    get_unreviewed_changes,
    list_change_events,
    list_communal_adapters,
    list_sources,
    record_change_event,
    refresh_source_freshness,
    review_change_event,
)

# Register router for HTTP tests (not yet in router.py hub file)
app.include_router(srw_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_source(db, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "source_code": f"test_{uuid.uuid4().hex[:8]}",
        "source_name": "Test Source",
        "watch_tier": "weekly",
        "freshness_state": "unknown",
        "is_active": True,
    }
    defaults.update(overrides)
    src = RuleSource(**defaults)
    db.add(src)
    await db.flush()
    return src


async def _make_adapter(db, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "commune_code": "9999",
        "commune_name": "TestVille",
        "canton_code": "VD",
        "adapter_status": "active",
        "fallback_mode": "canton_default",
    }
    defaults.update(overrides)
    a = CommunalAdapterProfile(**defaults)
    db.add(a)
    await db.flush()
    return a


async def _make_override(db, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "commune_code": "9999",
        "canton_code": "VD",
        "override_type": "stricter_threshold",
        "impact_summary": "Test impact",
        "review_required": True,
        "confidence_level": "review_required",
        "is_active": True,
    }
    defaults.update(overrides)
    o = CommunalRuleOverride(**defaults)
    db.add(o)
    await db.flush()
    return o


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_source_create(db_session):
    src = await _make_source(db_session, source_code="mdl_test")
    assert src.id is not None
    assert src.source_code == "mdl_test"
    assert src.freshness_state == "unknown"


@pytest.mark.asyncio
async def test_rule_change_event_create(db_session):
    src = await _make_source(db_session, source_code="mdl_evt")
    evt = RuleChangeEvent(
        id=uuid.uuid4(),
        source_id=src.id,
        event_type="new_rule",
        title="Test event",
    )
    db_session.add(evt)
    await db_session.flush()
    assert evt.id is not None
    assert evt.reviewed is False


@pytest.mark.asyncio
async def test_communal_adapter_create(db_session):
    a = await _make_adapter(db_session, commune_code="1234")
    assert a.commune_code == "1234"
    assert a.adapter_status == "active"


@pytest.mark.asyncio
async def test_communal_override_create(db_session):
    o = await _make_override(db_session, commune_code="5678")
    assert o.commune_code == "5678"
    assert o.override_type == "stricter_threshold"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_rule_source_read_schema():
    now = datetime.now(UTC)
    data = RuleSourceRead(
        id=uuid.uuid4(),
        source_code="sch_test",
        source_name="Schema Test",
        source_url=None,
        watch_tier="daily",
        last_checked_at=now,
        last_changed_at=None,
        freshness_state="current",
        change_types_detected=None,
        is_active=True,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    assert data.source_code == "sch_test"


def test_rule_change_event_read_schema():
    now = datetime.now(UTC)
    data = RuleChangeEventRead(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        event_type="portal_change",
        title="Test",
        description=None,
        impact_summary=None,
        detected_at=now,
        reviewed=False,
        reviewed_by_user_id=None,
        reviewed_at=None,
        review_notes=None,
        affects_buildings=False,
        created_at=now,
    )
    assert data.reviewed is False


def test_communal_adapter_read_schema():
    now = datetime.now(UTC)
    data = CommunalAdapterRead(
        id=uuid.uuid4(),
        commune_code="5586",
        commune_name="Lausanne",
        canton_code="VD",
        adapter_status="active",
        supports_procedure_projection=True,
        supports_rule_projection=True,
        fallback_mode="canton_default",
        source_ids=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    assert data.commune_name == "Lausanne"


def test_communal_override_read_schema():
    now = datetime.now(UTC)
    data = CommunalOverrideRead(
        id=uuid.uuid4(),
        commune_code="5586",
        canton_code="VD",
        override_type="heritage_constraint",
        rule_reference="RPGA Art. 45",
        impact_summary="Heritage buildings need full diagnostic",
        review_required=True,
        confidence_level="review_required",
        source_id=None,
        effective_from=date(2020, 1, 1),
        effective_to=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    assert data.override_type == "heritage_constraint"


def test_rule_source_create_schema():
    data = RuleSourceCreate(
        source_code="test",
        source_name="Test",
        watch_tier="daily",
    )
    assert data.is_active is True


def test_rule_change_event_create_schema():
    data = RuleChangeEventCreate(
        event_type="new_rule",
        title="New regulation",
        affects_buildings=True,
    )
    assert data.affects_buildings is True


def test_building_commune_context_schema():
    ctx = BuildingCommuneContext(
        building_id=uuid.uuid4(),
        city="Lausanne",
        canton="VD",
        adapter=None,
        overrides=[],
    )
    assert ctx.adapter is None
    assert ctx.overrides == []


# ---------------------------------------------------------------------------
# Service tests — freshness
# ---------------------------------------------------------------------------


def test_freshness_unknown_when_none():
    assert _compute_freshness("daily", None) == "unknown"


def test_freshness_current():
    now = datetime.now(UTC)
    assert _compute_freshness("daily", now) == "current"


def test_freshness_aging():
    ago = datetime.now(UTC) - timedelta(days=2)
    assert _compute_freshness("daily", ago) == "aging"


def test_freshness_stale():
    ago = datetime.now(UTC) - timedelta(days=5)
    assert _compute_freshness("daily", ago) == "stale"


def test_freshness_weekly_current():
    ago = datetime.now(UTC) - timedelta(days=5)
    assert _compute_freshness("weekly", ago) == "current"


def test_freshness_quarterly_current():
    ago = datetime.now(UTC) - timedelta(days=60)
    assert _compute_freshness("quarterly", ago) == "current"


# ---------------------------------------------------------------------------
# Service tests — CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sources_empty(db_session):
    result = await list_sources(db_session)
    assert result == []


@pytest.mark.asyncio
async def test_list_sources_with_filter(db_session):
    await _make_source(db_session, source_code="daily_src", watch_tier="daily")
    await _make_source(db_session, source_code="weekly_src", watch_tier="weekly")
    daily = await list_sources(db_session, tier_filter="daily")
    assert len(daily) == 1
    assert daily[0].source_code == "daily_src"


@pytest.mark.asyncio
async def test_refresh_source_freshness(db_session):
    src = await _make_source(db_session, source_code="refresh_test", watch_tier="daily")
    assert src.last_checked_at is None
    updated = await refresh_source_freshness(db_session, src.id)
    assert updated is not None
    assert updated.last_checked_at is not None
    assert updated.freshness_state == "current"


@pytest.mark.asyncio
async def test_refresh_nonexistent_source(db_session):
    result = await refresh_source_freshness(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_record_change_event(db_session):
    src = await _make_source(db_session, source_code="evt_src")
    evt = await record_change_event(
        db_session,
        src.id,
        {
            "event_type": "new_rule",
            "title": "New asbestos threshold",
            "affects_buildings": True,
        },
    )
    assert evt.id is not None
    assert evt.event_type == "new_rule"
    assert evt.affects_buildings is True
    # Source should have updated change_types_detected
    await db_session.refresh(src)
    assert "new_rule" in (src.change_types_detected or [])


@pytest.mark.asyncio
async def test_review_change_event(db_session, admin_user):
    src = await _make_source(db_session, source_code="review_src")
    evt = await record_change_event(db_session, src.id, {"event_type": "portal_change", "title": "Portal updated"})
    assert evt.reviewed is False
    reviewed = await review_change_event(db_session, evt.id, admin_user.id, "Looks fine")
    assert reviewed is not None
    assert reviewed.reviewed is True
    assert reviewed.reviewed_by_user_id == admin_user.id
    assert reviewed.review_notes == "Looks fine"


@pytest.mark.asyncio
async def test_review_nonexistent_event(db_session, admin_user):
    result = await review_change_event(db_session, uuid.uuid4(), admin_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_unreviewed_changes(db_session):
    src = await _make_source(db_session, source_code="unrev_src")
    await record_change_event(db_session, src.id, {"event_type": "new_rule", "title": "Unreviewed"})
    await record_change_event(db_session, src.id, {"event_type": "form_change", "title": "Also unreviewed"})
    unreviewed = await get_unreviewed_changes(db_session)
    assert len(unreviewed) >= 2


@pytest.mark.asyncio
async def test_list_change_events_filter_by_source(db_session):
    src1 = await _make_source(db_session, source_code="filter_src1")
    src2 = await _make_source(db_session, source_code="filter_src2")
    await record_change_event(db_session, src1.id, {"event_type": "new_rule", "title": "A"})
    await record_change_event(db_session, src2.id, {"event_type": "new_rule", "title": "B"})
    events = await list_change_events(db_session, source_id=src1.id)
    assert len(events) == 1
    assert events[0].title == "A"


# ---------------------------------------------------------------------------
# Service tests — Commune
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_communal_adapters(db_session):
    await _make_adapter(db_session, commune_code="1001", canton_code="VD", commune_name="Alpha")
    await _make_adapter(db_session, commune_code="2002", canton_code="GE", commune_name="Beta")
    vd = await list_communal_adapters(db_session, canton_filter="VD")
    assert len(vd) == 1
    assert vd[0].commune_name == "Alpha"


@pytest.mark.asyncio
async def test_get_commune_overrides(db_session):
    await _make_override(db_session, commune_code="3003", override_type="heritage_constraint")
    await _make_override(db_session, commune_code="3003", override_type="local_procedure")
    await _make_override(db_session, commune_code="4004", override_type="stricter_threshold")
    overrides = await get_commune_overrides(db_session, "3003")
    assert len(overrides) == 2


@pytest.mark.asyncio
async def test_get_building_commune_context_not_found(db_session):
    result = await get_building_commune_context(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_building_commune_context_with_adapter(db_session, sample_building):
    # sample_building has city="Lausanne", canton="VD"
    await _make_adapter(
        db_session,
        commune_code="5586",
        commune_name="Lausanne",
        canton_code="VD",
    )
    await _make_override(
        db_session,
        commune_code="5586",
        canton_code="VD",
        override_type="heritage_constraint",
        impact_summary="Heritage constraint for Lausanne",
    )
    ctx = await get_building_commune_context(db_session, sample_building.id)
    assert ctx is not None
    assert ctx["city"] == "Lausanne"
    assert ctx["adapter"] is not None
    assert ctx["adapter"].commune_code == "5586"
    assert len(ctx["overrides"]) == 1


@pytest.mark.asyncio
async def test_get_building_commune_context_no_adapter(db_session, sample_building):
    # No adapter for Lausanne -> no overrides
    ctx = await get_building_commune_context(db_session, sample_building.id)
    assert ctx is not None
    assert ctx["adapter"] is None
    assert ctx["overrides"] == []
