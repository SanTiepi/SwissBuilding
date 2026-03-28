"""BatiConnect — Conformance Check service + route + seed tests."""

import uuid

import pytest

from app.seeds.seed_conformance import seed_conformance_profiles
from app.services.conformance_service import (
    create_profile,
    get_building_checks,
    get_check_summary,
    get_profile_by_name,
    list_profiles,
    run_conformance_check,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_test_profile(db, **overrides):
    """Create a minimal test profile with sensible defaults."""
    defaults = {
        "name": f"test_profile_{uuid.uuid4().hex[:8]}",
        "description": "Test profile",
        "profile_type": "pack",
    }
    defaults.update(overrides)
    return await create_profile(db, defaults)


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_profile(db_session):
    profile = await _create_test_profile(
        db_session,
        name="authority_test",
        profile_type="pack",
        required_sections=["passport_summary", "pollutant_inventory"],
        minimum_completeness=0.80,
    )
    assert profile.id is not None
    assert profile.name == "authority_test"
    assert profile.active is True
    assert profile.required_sections == ["passport_summary", "pollutant_inventory"]
    assert profile.minimum_completeness == 0.80


@pytest.mark.asyncio
async def test_get_profile_by_name(db_session):
    await _create_test_profile(db_session, name="named_profile")
    await db_session.flush()

    found = await get_profile_by_name(db_session, "named_profile")
    assert found is not None
    assert found.name == "named_profile"

    missing = await get_profile_by_name(db_session, "nonexistent")
    assert missing is None


@pytest.mark.asyncio
async def test_list_profiles_all(db_session):
    await _create_test_profile(db_session, name="p1", profile_type="pack")
    await _create_test_profile(db_session, name="p2", profile_type="import")
    await _create_test_profile(db_session, name="p3", profile_type="pack")
    await db_session.flush()

    all_profiles = await list_profiles(db_session)
    assert len(all_profiles) >= 3

    pack_profiles = await list_profiles(db_session, profile_type="pack")
    assert all(p.profile_type == "pack" for p in pack_profiles)
    assert len(pack_profiles) >= 2


@pytest.mark.asyncio
async def test_list_profiles_filters_inactive(db_session):
    profile = await _create_test_profile(db_session, name="inactive_one")
    profile.active = False
    await db_session.flush()

    active = await list_profiles(db_session, active_only=True)
    names = [p.name for p in active]
    assert "inactive_one" not in names


# ---------------------------------------------------------------------------
# Conformance Check — service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_check_pass(db_session, sample_building):
    """A lenient profile should pass for any building with basic fields."""
    await _create_test_profile(
        db_session,
        name="lenient",
        profile_type="pack",
        required_fields=["address", "canton"],
        minimum_completeness=None,
        minimum_trust=None,
    )
    await db_session.flush()

    check = await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="lenient",
        target_type="pack",
    )
    assert check.id is not None
    assert check.result == "pass"
    assert check.score == 1.0
    assert len(check.checks_passed) == 2  # address + canton
    assert len(check.checks_failed) == 0


@pytest.mark.asyncio
async def test_run_check_fail_missing_field(db_session, sample_building):
    """A profile requiring a nonexistent field should fail."""
    await _create_test_profile(
        db_session,
        name="strict_fields",
        profile_type="pack",
        required_fields=["address", "nonexistent_field"],
    )
    await db_session.flush()

    check = await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="strict_fields",
        target_type="pack",
    )
    assert check.result == "fail"
    assert check.score < 1.0
    assert any(c["check"] == "field:nonexistent_field" for c in check.checks_failed)


@pytest.mark.asyncio
async def test_run_check_max_unknowns(db_session, sample_building):
    """max_unknowns=0 should pass when there are no unknowns."""
    await _create_test_profile(
        db_session,
        name="zero_unknowns",
        profile_type="pack",
        max_unknowns=0,
    )
    await db_session.flush()

    check = await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="zero_unknowns",
        target_type="pack",
    )
    assert check.result == "pass"
    assert any(c["check"] == "max_unknowns" for c in check.checks_passed)


@pytest.mark.asyncio
async def test_run_check_max_contradictions(db_session, sample_building):
    """max_contradictions=0 should pass when there are no contradictions."""
    await _create_test_profile(
        db_session,
        name="zero_contradictions",
        profile_type="pack",
        max_contradictions=0,
    )
    await db_session.flush()

    check = await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="zero_contradictions",
        target_type="pack",
    )
    assert check.result == "pass"
    assert any(c["check"] == "max_contradictions" for c in check.checks_passed)


@pytest.mark.asyncio
async def test_run_check_profile_not_found(db_session, sample_building):
    """ValueError raised for unknown profile name."""
    with pytest.raises(ValueError, match="not found"):
        await run_conformance_check(
            db_session,
            building_id=sample_building.id,
            profile_name="does_not_exist",
            target_type="pack",
        )


@pytest.mark.asyncio
async def test_run_check_summary_text(db_session, sample_building):
    """Check summary is populated with profile name and result."""
    await _create_test_profile(db_session, name="summary_test")
    await db_session.flush()

    check = await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="summary_test",
        target_type="pack",
    )
    assert "summary_test" in check.summary
    assert check.summary is not None


@pytest.mark.asyncio
async def test_run_check_with_checked_by(db_session, sample_building, admin_user):
    """checked_by_id is persisted."""
    await _create_test_profile(db_session, name="checked_by_test")
    await db_session.flush()

    check = await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="checked_by_test",
        target_type="passport",
        checked_by_id=admin_user.id,
    )
    assert check.checked_by_id == admin_user.id


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_building_checks(db_session, sample_building):
    await _create_test_profile(db_session, name="list_test")
    await db_session.flush()

    # Run 3 checks
    for _ in range(3):
        await run_conformance_check(
            db_session,
            building_id=sample_building.id,
            profile_name="list_test",
            target_type="pack",
        )
    await db_session.flush()

    checks = await get_building_checks(db_session, sample_building.id)
    assert len(checks) == 3


@pytest.mark.asyncio
async def test_get_check_summary(db_session, sample_building):
    await _create_test_profile(
        db_session,
        name="summary_count_test",
        required_fields=["address"],
    )
    await db_session.flush()

    await run_conformance_check(
        db_session,
        building_id=sample_building.id,
        profile_name="summary_count_test",
        target_type="pack",
    )
    await db_session.flush()

    summary = await get_check_summary(db_session, sample_building.id)
    assert summary["total_checks"] >= 1
    assert summary["latest_check"] is not None


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_conformance_profiles(db_session):
    """Seed creates 5 profiles, second call is idempotent."""
    created = await seed_conformance_profiles(db_session)
    assert created == 5

    # Idempotent
    created_again = await seed_conformance_profiles(db_session)
    assert created_again == 0


@pytest.mark.asyncio
async def test_seed_profiles_are_queryable(db_session):
    """All 5 seeded profiles are fetchable by name."""
    await seed_conformance_profiles(db_session)
    await db_session.flush()

    expected_names = ["authority_pack", "insurer_pack", "transfer", "import", "publication"]
    for name in expected_names:
        profile = await get_profile_by_name(db_session, name)
        assert profile is not None, f"Profile '{name}' not found"
        assert profile.active is True


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_list_profiles(client, auth_headers, db_session):
    await seed_conformance_profiles(db_session)
    await db_session.commit()

    resp = await client.get("/api/v1/conformance/profiles", headers=auth_headers)
    assert resp.status_code == 200
    profiles = resp.json()
    assert len(profiles) >= 5


@pytest.mark.asyncio
async def test_api_create_profile(client, auth_headers):
    resp = await client.post(
        "/api/v1/conformance/profiles",
        json={
            "name": "api_created_profile",
            "description": "Created via API",
            "profile_type": "pack",
            "required_sections": ["passport_summary"],
            "minimum_completeness": 0.50,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "api_created_profile"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_api_run_check(client, auth_headers, sample_building, db_session):
    await seed_conformance_profiles(db_session)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/conformance/check",
        json={
            "profile_name": "import",
            "target_type": "import",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["result"] in ("pass", "fail", "partial")
    assert "score" in data
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_list_checks(client, auth_headers, sample_building, db_session):
    await seed_conformance_profiles(db_session)
    await db_session.commit()

    # Run a check first
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/conformance/check",
        json={"profile_name": "import", "target_type": "import"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/conformance/checks",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_check_summary(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/conformance/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "total_checks" in data
