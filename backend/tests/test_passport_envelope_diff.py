"""Tests for passport envelope diffing, machine-readable export, transfer manifest, and reimport validation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.organization import Organization
from app.models.passport_envelope import BuildingPassportEnvelope
from app.models.user import User
from app.services.passport_exchange_service import (
    diff_envelopes,
    export_machine_readable,
    generate_transfer_manifest,
    validate_reimport,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_org(db_session: AsyncSession) -> Organization:
    org = Organization(id=uuid.uuid4(), name="Diff Test Org", type="property_management")
    db_session.add(org)
    return org


def _make_building(db_session: AsyncSession, *, created_by: uuid.UUID, org_id: uuid.UUID) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address="Rue du Diff 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1980,
        building_type="residential",
        created_by=created_by,
        organization_id=org_id,
        status="active",
    )
    db_session.add(b)
    return b


def _make_envelope(
    db_session: AsyncSession,
    *,
    building_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    version: int = 1,
    passport_data: dict | None = None,
    redaction_profile: str = "none",
    financials_redacted: bool = False,
    personal_data_redacted: bool = False,
    status: str = "draft",
) -> BuildingPassportEnvelope:
    data = passport_data or {
        "passport_grade": "B",
        "knowledge_state": {"overall_trust": 0.72, "proven_pct": 40.0, "inferred_pct": 30.0},
        "completeness": {"overall_score": 65.0},
        "readiness": {"safe_to_start": {"status": "blocked", "score": 30}},
        "blind_spots": {"total_open": 5},
        "contradictions": {"total": 2, "unresolved": 1},
        "evidence_coverage": {"diagnostics_count": 3},
    }
    env = BuildingPassportEnvelope(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org_id,
        created_by_id=user_id,
        version=version,
        passport_data=data,
        sections_included=list(data.keys()),
        content_hash="a" * 64,
        redaction_profile=redaction_profile,
        financials_redacted=financials_redacted,
        personal_data_redacted=personal_data_redacted,
        is_sovereign=True,
        status=status,
    )
    db_session.add(env)
    return env


# ---------------------------------------------------------------------------
# Tests — diff_envelopes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diff_identical_envelopes(db_session: AsyncSession, admin_user: User):
    """Diff of two identical envelopes should show zero changes."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    same_data = {
        "passport_grade": "A",
        "knowledge_state": {"overall_trust": 0.9},
        "completeness": {"overall_score": 90.0},
    }
    env_a = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=1, passport_data=same_data
    )
    env_b = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=2, passport_data=same_data
    )
    await db_session.commit()

    result = await diff_envelopes(db_session, env_a.id, env_b.id)
    assert result["summary"]["total_changes"] == 0
    assert len(result["changes"]) == 0
    assert result["grade_delta"]["old_grade"] == "A"
    assert result["grade_delta"]["new_grade"] == "A"


@pytest.mark.asyncio
async def test_diff_detects_added_section(db_session: AsyncSession, admin_user: User):
    """Diff should detect a section added in the newer envelope."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    data_a = {"passport_grade": "C", "completeness": {"overall_score": 50.0}}
    data_b = {**data_a, "blind_spots": {"total_open": 3}}

    env_a = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=1, passport_data=data_a
    )
    env_b = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=2, passport_data=data_b
    )
    await db_session.commit()

    result = await diff_envelopes(db_session, env_a.id, env_b.id)
    assert "blind_spots" in result["summary"]["sections_added"]
    assert any(c["section"] == "blind_spots" and c["change_type"] == "added" for c in result["changes"])


@pytest.mark.asyncio
async def test_diff_detects_removed_section(db_session: AsyncSession, admin_user: User):
    """Diff should detect a section removed in the newer envelope."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    data_a = {"passport_grade": "B", "blind_spots": {"total_open": 5}}
    data_b = {"passport_grade": "B"}

    env_a = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=1, passport_data=data_a
    )
    env_b = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=2, passport_data=data_b
    )
    await db_session.commit()

    result = await diff_envelopes(db_session, env_a.id, env_b.id)
    assert "blind_spots" in result["summary"]["sections_removed"]


@pytest.mark.asyncio
async def test_diff_detects_modified_fields(db_session: AsyncSession, admin_user: User):
    """Diff should detect modified fields within a section."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    data_a = {"knowledge_state": {"overall_trust": 0.5, "proven_pct": 30.0}}
    data_b = {"knowledge_state": {"overall_trust": 0.8, "proven_pct": 30.0}}

    env_a = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=1, passport_data=data_a
    )
    env_b = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=2, passport_data=data_b
    )
    await db_session.commit()

    result = await diff_envelopes(db_session, env_a.id, env_b.id)
    trust_changes = [c for c in result["changes"] if "overall_trust" in c["field"]]
    assert len(trust_changes) == 1
    assert trust_changes[0]["change_type"] == "modified"
    assert result["trust_delta"]["trust_change"] == pytest.approx(0.3, abs=0.01)


@pytest.mark.asyncio
async def test_diff_grade_delta(db_session: AsyncSession, admin_user: User):
    """Diff should report grade changes."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    data_a = {"passport_grade": "D"}
    data_b = {"passport_grade": "B"}

    env_a = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=1, passport_data=data_a
    )
    env_b = _make_envelope(
        db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id, version=2, passport_data=data_b
    )
    await db_session.commit()

    result = await diff_envelopes(db_session, env_a.id, env_b.id)
    assert result["grade_delta"]["old_grade"] == "D"
    assert result["grade_delta"]["new_grade"] == "B"


@pytest.mark.asyncio
async def test_diff_nonexistent_envelope(db_session: AsyncSession, admin_user: User):
    """Diff with a nonexistent envelope raises ValueError."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="not found"):
        await diff_envelopes(db_session, env.id, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — export_machine_readable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_json_format(db_session: AsyncSession, admin_user: User):
    """Export in JSON format should include provenance and full data."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    result = await export_machine_readable(db_session, env.id, format="json")
    assert isinstance(result, dict)
    assert result["format"] == "json"
    assert result["schema_version"] == "1.0.0"
    assert result["source_system"] == "BatiConnect"
    assert result["envelope"]["id"] == str(env.id)
    assert result["envelope"]["version"] == 1
    assert result["provenance"]["created_by_id"] == str(admin_user.id)
    assert result["redaction"]["profile"] == "none"
    assert "passport_data" in result
    assert result["reimport"]["reimportable"] is True


@pytest.mark.asyncio
async def test_export_csv_format(db_session: AsyncSession, admin_user: User):
    """Export in CSV format should return a CSV string."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    result = await export_machine_readable(db_session, env.id, format="csv-summary")
    assert isinstance(result, str)
    assert "section,key,value" in result
    assert "_metadata" in result
    assert str(env.id) in result


@pytest.mark.asyncio
async def test_export_nonexistent(db_session: AsyncSession):
    """Export for nonexistent envelope raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await export_machine_readable(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — generate_transfer_manifest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transfer_manifest_basic(db_session: AsyncSession, admin_user: User):
    """Generate a transfer manifest for a draft envelope."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    result = await generate_transfer_manifest(db_session, env.id)
    assert result["envelope_id"] == str(env.id)
    assert result["building_id"] == str(building.id)
    assert result["version"] == 1
    assert result["status"] == "draft"
    assert result["redaction"]["financials_redacted"] is False
    assert result["recipient_receives"]["section_count"] > 0
    assert result["acknowledgment_required"]["must_acknowledge_receipt"] is True
    assert "generated_at" in result


@pytest.mark.asyncio
async def test_transfer_manifest_with_redaction(db_session: AsyncSession, admin_user: User):
    """Manifest should list redacted categories."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    env = _make_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        user_id=admin_user.id,
        redaction_profile="detailed",
        financials_redacted=True,
        personal_data_redacted=True,
    )
    await db_session.commit()

    result = await generate_transfer_manifest(db_session, env.id)
    assert "financial" in result["redaction"]["redacted_categories"]
    assert "personal_data" in result["redaction"]["redacted_categories"]


@pytest.mark.asyncio
async def test_transfer_manifest_nonexistent(db_session: AsyncSession):
    """Manifest for nonexistent envelope raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await generate_transfer_manifest(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — validate_reimport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_reimport_valid(db_session: AsyncSession):
    """Valid envelope data should pass validation."""
    data = {
        "passport_data": {
            "passport_grade": "B",
            "knowledge_state": {"overall_trust": 0.72},
        },
        "content_hash": "a" * 64,
        "sections_included": ["knowledge_state", "passport_grade"],
        "version": 1,
        "redaction_profile": "none",
    }
    result = await validate_reimport(db_session, data)
    assert result["valid"] is True
    assert len(result["issues"]) == 0
    assert "knowledge_state" in result["sections_found"]
    assert "passport_grade" in result["sections_found"]


@pytest.mark.asyncio
async def test_validate_reimport_missing_passport_data(db_session: AsyncSession):
    """Missing passport_data should be an issue."""
    data = {"content_hash": "abc123"}
    result = await validate_reimport(db_session, data)
    assert result["valid"] is False
    assert any("passport_data" in i for i in result["issues"])


@pytest.mark.asyncio
async def test_validate_reimport_missing_content_hash(db_session: AsyncSession):
    """Missing content_hash should be an issue."""
    data = {"passport_data": {"passport_grade": "A"}}
    result = await validate_reimport(db_session, data)
    assert result["valid"] is False
    assert any("content_hash" in i for i in result["issues"])


@pytest.mark.asyncio
async def test_validate_reimport_bad_passport_data_type(db_session: AsyncSession):
    """Non-dict passport_data should be an issue."""
    data = {"passport_data": "not a dict", "content_hash": "a" * 64}
    result = await validate_reimport(db_session, data)
    assert result["valid"] is False
    assert any("dict" in i for i in result["issues"])


@pytest.mark.asyncio
async def test_validate_reimport_no_recognized_sections(db_session: AsyncSession):
    """No recognized sections should produce a warning (not an issue)."""
    data = {
        "passport_data": {"some_unknown_field": 42},
        "content_hash": "a" * 64,
    }
    result = await validate_reimport(db_session, data)
    assert result["valid"] is True
    assert any("No recognized" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_validate_reimport_short_hash_warning(db_session: AsyncSession):
    """Short content hash should produce a warning."""
    data = {
        "passport_data": {"passport_grade": "A"},
        "content_hash": "abc",
    }
    result = await validate_reimport(db_session, data)
    assert result["valid"] is True
    assert any("short" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_validate_reimport_bad_redaction_profile(db_session: AsyncSession):
    """Unrecognized redaction profile should produce a warning."""
    data = {
        "passport_data": {"passport_grade": "A"},
        "content_hash": "a" * 64,
        "redaction_profile": "super_secret",
    }
    result = await validate_reimport(db_session, data)
    assert result["valid"] is True
    assert any("redaction_profile" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_diff_200(client: AsyncClient, auth_headers: dict, db_session: AsyncSession, admin_user: User):
    """API: GET diff between two envelopes returns 200."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()

    env_a = _make_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        user_id=admin_user.id,
        version=1,
        passport_data={"passport_grade": "C"},
    )
    env_b = _make_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        user_id=admin_user.id,
        version=2,
        passport_data={"passport_grade": "A"},
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/passport-envelope/{env_a.id}/diff/{env_b.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "changes" in data
    assert "grade_delta" in data


@pytest.mark.asyncio
async def test_api_diff_404(client: AsyncClient, auth_headers: dict):
    """API: Diff with nonexistent envelope returns 404."""
    resp = await client.get(
        f"/api/v1/passport-envelope/{uuid.uuid4()}/diff/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_export_json_200(client: AsyncClient, auth_headers: dict, db_session: AsyncSession, admin_user: User):
    """API: GET export in JSON format returns 200."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()
    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/passport-envelope/{env.id}/export",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "json"
    assert data["source_system"] == "BatiConnect"


@pytest.mark.asyncio
async def test_api_export_csv_200(client: AsyncClient, auth_headers: dict, db_session: AsyncSession, admin_user: User):
    """API: GET export in CSV format returns 200 with content wrapper."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()
    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/passport-envelope/{env.id}/export",
        params={"format": "csv-summary"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "csv-summary"
    assert "section,key,value" in data["content"]


@pytest.mark.asyncio
async def test_api_export_404(client: AsyncClient, auth_headers: dict):
    """API: Export nonexistent envelope returns 404."""
    resp = await client.get(
        f"/api/v1/passport-envelope/{uuid.uuid4()}/export",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_transfer_manifest_200(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, admin_user: User
):
    """API: GET transfer manifest returns 200."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.flush()
    env = _make_envelope(db_session, building_id=building.id, org_id=org.id, user_id=admin_user.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/passport-envelope/{env.id}/transfer-manifest",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["envelope_id"] == str(env.id)
    assert "recipient_receives" in data
    assert "acknowledgment_required" in data


@pytest.mark.asyncio
async def test_api_validate_reimport_valid(client: AsyncClient, auth_headers: dict):
    """API: POST validate-reimport with valid data returns valid=true."""
    resp = await client.post(
        "/api/v1/passport-envelope/validate-reimport",
        json={
            "envelope_data": {
                "passport_data": {"passport_grade": "A", "knowledge_state": {"overall_trust": 0.9}},
                "content_hash": "a" * 64,
            }
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_api_validate_reimport_invalid(client: AsyncClient, auth_headers: dict):
    """API: POST validate-reimport with missing keys returns valid=false."""
    resp = await client.post(
        "/api/v1/passport-envelope/validate-reimport",
        json={"envelope_data": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert len(data["issues"]) > 0


@pytest.mark.asyncio
async def test_api_diff_unauthenticated(client: AsyncClient):
    """API: Diff without auth returns 401."""
    resp = await client.get(
        f"/api/v1/passport-envelope/{uuid.uuid4()}/diff/{uuid.uuid4()}",
    )
    assert resp.status_code == 401
