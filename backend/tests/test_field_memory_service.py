"""Tests for collective field memory service — pattern detection and cross-building search."""

import json
import uuid

import pytest

from app.models.building import Building
from app.services.field_memory_service import (
    get_building_observations,
    get_pattern_insights,
    record_observation,
    search_observations,
    upvote_observation,
    verify_observation,
)


@pytest.fixture
async def building_vd(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue du Champ 10",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1972,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_ge(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue de Geneve 5",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=1968,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


# --- Record observation ---


@pytest.mark.asyncio
async def test_record_observation(db_session, building_vd, admin_user):
    obs = await record_observation(
        db_session,
        building_id=building_vd.id,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="pattern",
        title="PCB in joint sealants",
        description="Found PCB in joint sealants of 1970s flat-roof building",
        tags=["pcb", "joint_sealant", "1970s", "flat_roof"],
        context={
            "canton": "VD",
            "construction_year_min": 1960,
            "construction_year_max": 1975,
            "pollutant": "pcb",
            "material": "joint_sealant",
        },
        confidence="certain",
    )
    assert obs.id is not None
    assert obs.title == "PCB in joint sealants"
    assert obs.confidence == "certain"
    assert obs.status == "active"
    assert obs.upvotes == 0
    assert obs.is_verified is False
    assert json.loads(obs.tags) == ["pcb", "joint_sealant", "1970s", "flat_roof"]
    ctx = json.loads(obs.context_json)
    assert ctx["canton"] == "VD"
    assert ctx["pollutant"] == "pcb"


@pytest.mark.asyncio
async def test_record_general_observation(db_session, admin_user):
    """General observation without building_id."""
    obs = await record_observation(
        db_session,
        building_id=None,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="tip",
        title="Always check behind radiators",
        description="Lead paint often hides behind old radiators",
        tags=["lead", "radiator"],
        context={"pollutant": "lead"},
        confidence="likely",
    )
    assert obs.building_id is None
    assert obs.title == "Always check behind radiators"


# --- Search by tags ---


@pytest.mark.asyncio
async def test_search_by_tags(db_session, building_vd, admin_user):
    for title, tags in [
        ("Obs A", ["pcb", "joint_sealant"]),
        ("Obs B", ["pcb", "flat_roof"]),
        ("Obs C", ["lead", "paint"]),
    ]:
        await record_observation(
            db_session,
            building_id=building_vd.id,
            observer_id=admin_user.id,
            observer_role="diagnostician",
            observation_type="pattern",
            title=title,
            description=None,
            tags=tags,
            context=None,
            confidence="likely",
        )

    results, total = await search_observations(db_session, tags=["pcb"])
    assert total == 2
    titles = {r.title for r in results}
    assert "Obs A" in titles
    assert "Obs B" in titles


# --- Search by canton + year range ---


@pytest.mark.asyncio
async def test_search_by_canton(db_session, building_vd, building_ge, admin_user):
    await record_observation(
        db_session,
        building_id=building_vd.id,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="pattern",
        title="VD observation",
        description=None,
        tags=["pcb"],
        context={"canton": "VD", "construction_year_min": 1960, "construction_year_max": 1975},
        confidence="likely",
    )
    await record_observation(
        db_session,
        building_id=building_ge.id,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="pattern",
        title="GE observation",
        description=None,
        tags=["pcb"],
        context={"canton": "GE", "construction_year_min": 1965, "construction_year_max": 1980},
        confidence="likely",
    )

    results, total = await search_observations(db_session, canton="VD")
    assert total == 1
    assert results[0].title == "VD observation"


# --- Pattern detection ---


@pytest.mark.asyncio
async def test_pattern_detection(db_session, building_vd, building_ge, admin_user):
    """Create multiple similar observations and verify pattern emerges."""
    # Create 3 observations with same context signature
    for i in range(3):
        b_id = building_vd.id if i < 2 else building_ge.id
        await record_observation(
            db_session,
            building_id=b_id,
            observer_id=admin_user.id,
            observer_role="diagnostician",
            observation_type="pattern",
            title=f"PCB in joints obs {i}",
            description=None,
            tags=["pcb", "joint_sealant"],
            context={
                "canton": "VD",
                "construction_year_min": 1960,
                "construction_year_max": 1975,
                "pollutant": "pcb",
                "material": "joint_sealant",
            },
            confidence="likely",
        )

    patterns = await get_pattern_insights(db_session)
    assert len(patterns) >= 1
    top = patterns[0]
    assert top["occurrences"] >= 3
    assert "pcb" in top["pattern"].lower() or "PCB" in top["pattern"]
    assert top["buildings_count"] >= 1
    assert top["confidence"] in ("low", "medium", "high")
    assert "joint_sealant" in top["tags"] or "pcb" in top["tags"]


@pytest.mark.asyncio
async def test_pattern_detection_needs_minimum(db_session, building_vd, admin_user):
    """Single observation should not produce a pattern."""
    await record_observation(
        db_session,
        building_id=building_vd.id,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="tip",
        title="Lone observation",
        description=None,
        tags=["unique_tag"],
        context={"canton": "ZH", "pollutant": "radon"},
        confidence="speculation",
    )
    patterns = await get_pattern_insights(db_session)
    # Should have no pattern from a single observation
    zh_patterns = [p for p in patterns if "ZH" in p.get("pattern", "")]
    assert len(zh_patterns) == 0


# --- Upvote ---


@pytest.mark.asyncio
async def test_upvote_increments(db_session, building_vd, admin_user):
    obs = await record_observation(
        db_session,
        building_id=building_vd.id,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="tip",
        title="Upvote test",
        description=None,
        tags=[],
        context=None,
        confidence="likely",
    )
    assert obs.upvotes == 0

    updated = await upvote_observation(db_session, obs.id, admin_user.id)
    assert updated is not None
    assert updated.upvotes == 1

    updated2 = await upvote_observation(db_session, updated.id, admin_user.id)
    assert updated2.upvotes == 2


@pytest.mark.asyncio
async def test_upvote_not_found(db_session, admin_user):
    result = await upvote_observation(db_session, uuid.uuid4(), admin_user.id)
    assert result is None


# --- Verify ---


@pytest.mark.asyncio
async def test_verify_marks_as_verified(db_session, building_vd, admin_user):
    obs = await record_observation(
        db_session,
        building_id=building_vd.id,
        observer_id=admin_user.id,
        observer_role="diagnostician",
        observation_type="anomaly",
        title="Verify test",
        description=None,
        tags=[],
        context=None,
        confidence="possible",
    )
    assert obs.is_verified is False

    verified = await verify_observation(db_session, obs.id, admin_user.id)
    assert verified is not None
    assert verified.is_verified is True
    assert verified.verified is True
    assert verified.verified_by_id == admin_user.id
    assert verified.verified_at is not None


@pytest.mark.asyncio
async def test_verify_not_found(db_session, admin_user):
    result = await verify_observation(db_session, uuid.uuid4(), admin_user.id)
    assert result is None


# --- Building observations ---


@pytest.mark.asyncio
async def test_get_building_observations(db_session, building_vd, admin_user):
    for i in range(3):
        await record_observation(
            db_session,
            building_id=building_vd.id,
            observer_id=admin_user.id,
            observer_role="diagnostician",
            observation_type="tip",
            title=f"Building obs {i}",
            description=None,
            tags=[],
            context=None,
            confidence="likely",
        )

    items, total = await get_building_observations(db_session, building_vd.id)
    assert total == 3
    assert len(items) == 3
