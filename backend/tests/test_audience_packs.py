"""Finance Surfaces — Audience Packs tests (service-layer + route-level)."""

import hashlib
import json
import uuid
from datetime import UTC, datetime

import pytest

from app.api.audience_packs import router as audience_packs_router
from app.main import app
from app.models.audience_pack import AudiencePack
from app.models.redaction_profile import DecisionCaveatProfile, ExternalAudienceRedactionProfile
from app.services.audience_pack_service import (
    _apply_redaction,
    _caveat_applies,
    _compute_hash,
    _compute_residual_risk_summary,
    _compute_trust_refs,
    compare_packs,
    evaluate_caveats,
    generate_pack,
    get_pack,
    get_redaction_profile_by_code,
    list_packs,
    list_redaction_profiles,
    share_pack,
)

# Register router for HTTP tests
app.include_router(audience_packs_router, prefix="/api/v1")


# ---- Fixtures ----


@pytest.fixture
async def redaction_profile_insurer(db_session):
    profile = ExternalAudienceRedactionProfile(
        id=uuid.uuid4(),
        profile_code="test-insurer",
        audience_type="insurer",
        allowed_sections=["building_identity", "diagnostics_summary", "obligations"],
        blocked_sections=["financial", "internal_notes"],
        redacted_fields=[{"section": "building_identity", "field": "cadastral_ref", "reason": "not relevant"}],
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.fixture
async def caveat_profile_unknown(db_session):
    profile = DecisionCaveatProfile(
        id=uuid.uuid4(),
        audience_type="insurer",
        caveat_type="unknown_disclosure",
        template_text="Building has unresolved unknowns.",
        severity="warning",
        applies_when={"has_unknowns": True},
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.fixture
async def caveat_profile_always(db_session):
    """Caveat that always applies (empty applies_when)."""
    profile = DecisionCaveatProfile(
        id=uuid.uuid4(),
        audience_type="transaction",
        caveat_type="regulatory_caveat",
        template_text="Regulatory caveat always applies.",
        severity="info",
        applies_when={},
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.fixture
async def sample_pack(db_session, sample_building, admin_user):
    sections = {"building_identity": {"address": "Rue Test 1", "city": "Lausanne"}}
    content_hash = hashlib.sha256(json.dumps(sections, sort_keys=True).encode()).hexdigest()
    pack = AudiencePack(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        pack_type="insurer",
        pack_version=1,
        status="draft",
        generated_by_user_id=admin_user.id,
        sections=sections,
        unknowns_summary=[],
        contradictions_summary=[],
        residual_risk_summary=[],
        trust_refs=[],
        proof_refs=[],
        content_hash=content_hash,
        generated_at=datetime.now(UTC),
    )
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)
    return pack


@pytest.fixture
async def sample_pack_transaction(db_session, sample_building, admin_user):
    sections = {"building_identity": {"address": "Rue Test 1"}, "obligations": []}
    content_hash = hashlib.sha256(json.dumps(sections, sort_keys=True).encode()).hexdigest()
    pack = AudiencePack(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        pack_type="transaction",
        pack_version=1,
        status="ready",
        generated_by_user_id=admin_user.id,
        sections=sections,
        content_hash=content_hash,
        generated_at=datetime.now(UTC),
    )
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)
    return pack


# ---- Service-layer: Pure function tests ----


class TestRedactionLogic:
    def test_apply_redaction_blocks_sections(self, redaction_profile_insurer):
        sections = {
            "building_identity": {"address": "Test", "cadastral_ref": "REF-123"},
            "financial": {"revenue": 100000},
            "diagnostics_summary": [{"type": "asbestos"}],
        }
        result = _apply_redaction(sections, redaction_profile_insurer)
        assert "financial" not in result
        assert "building_identity" in result
        assert "diagnostics_summary" in result

    def test_apply_redaction_removes_fields(self, redaction_profile_insurer):
        sections = {
            "building_identity": {"address": "Test", "cadastral_ref": "REF-123"},
            "diagnostics_summary": [],
        }
        result = _apply_redaction(sections, redaction_profile_insurer)
        assert "cadastral_ref" not in result["building_identity"]
        assert "address" in result["building_identity"]

    def test_apply_redaction_allowed_filter(self, redaction_profile_insurer):
        sections = {
            "building_identity": {"address": "Test"},
            "unknown_section": {"data": True},
        }
        result = _apply_redaction(sections, redaction_profile_insurer)
        assert "unknown_section" not in result


class TestCaveatLogic:
    def test_caveat_applies_true(self):
        assert _caveat_applies({"has_unknowns": True}, {"has_unknowns": True, "unknown_count": 3})

    def test_caveat_applies_false(self):
        assert not _caveat_applies({"has_unknowns": True}, {"has_unknowns": False, "unknown_count": 0})

    def test_caveat_applies_empty_conditions(self):
        assert _caveat_applies({}, {"has_unknowns": False})

    def test_caveat_applies_min_threshold(self):
        assert _caveat_applies({"min_unknowns": 2}, {"unknown_count": 5})
        assert not _caveat_applies({"min_unknowns": 10}, {"unknown_count": 5})


class TestContentHash:
    def test_compute_hash_deterministic(self):
        sections = {"a": 1, "b": 2}
        h1 = _compute_hash(sections, [], [])
        h2 = _compute_hash(sections, [], [])
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_hash_changes_with_content(self):
        h1 = _compute_hash({"a": 1}, [], [])
        h2 = _compute_hash({"a": 2}, [], [])
        assert h1 != h2


class TestRiskAndTrustComputation:
    def test_residual_risk_unvalidated_diagnostic(self):
        sections = {"diagnostics_summary": [{"diagnostic_type": "asbestos", "status": "draft"}]}
        risks = _compute_residual_risk_summary(sections)
        assert len(risks) == 1
        assert risks[0]["risk_type"] == "unvalidated_diagnostic"

    def test_residual_risk_validated_no_risk(self):
        sections = {"diagnostics_summary": [{"diagnostic_type": "asbestos", "status": "validated"}]}
        risks = _compute_residual_risk_summary(sections)
        assert len(risks) == 0

    def test_trust_refs_from_diagnostics(self):
        sections = {
            "diagnostics_summary": [
                {"id": "abc", "status": "validated", "date": "2025-01-01"},
                {"id": "def", "status": "draft", "date": "2025-06-01"},
            ]
        }
        refs = _compute_trust_refs(sections)
        assert len(refs) == 2
        assert refs[0]["confidence"] == "verified"
        assert refs[1]["confidence"] == "declared"


# ---- Service-layer: DB tests ----


@pytest.mark.asyncio
async def test_generate_pack(db_session, sample_building, admin_user):
    pack = await generate_pack(db_session, sample_building.id, "insurer", user_id=admin_user.id)
    assert pack.id is not None
    assert pack.pack_type == "insurer"
    assert pack.pack_version == 1
    assert pack.status == "draft"
    assert pack.content_hash is not None
    assert "building_identity" in pack.sections


@pytest.mark.asyncio
async def test_generate_pack_versioning(db_session, sample_building, admin_user):
    p1 = await generate_pack(db_session, sample_building.id, "insurer", user_id=admin_user.id)
    p2 = await generate_pack(db_session, sample_building.id, "insurer", user_id=admin_user.id)
    assert p1.pack_version == 1
    assert p2.pack_version == 2


@pytest.mark.asyncio
async def test_generate_pack_invalid_building(db_session, admin_user):
    with pytest.raises(ValueError, match="not found"):
        await generate_pack(db_session, uuid.uuid4(), "insurer", user_id=admin_user.id)


@pytest.mark.asyncio
async def test_list_packs(db_session, sample_building, sample_pack):
    packs = await list_packs(db_session, sample_building.id)
    assert len(packs) >= 1


@pytest.mark.asyncio
async def test_list_packs_filtered(db_session, sample_building, sample_pack, sample_pack_transaction):
    insurer_packs = await list_packs(db_session, sample_building.id, pack_type="insurer")
    assert all(p.pack_type == "insurer" for p in insurer_packs)
    assert len(insurer_packs) >= 1


@pytest.mark.asyncio
async def test_get_pack(db_session, sample_pack):
    pack = await get_pack(db_session, sample_pack.id)
    assert pack is not None
    assert pack.id == sample_pack.id


@pytest.mark.asyncio
async def test_get_pack_not_found(db_session):
    pack = await get_pack(db_session, uuid.uuid4())
    assert pack is None


@pytest.mark.asyncio
async def test_share_pack(db_session, sample_pack):
    shared = await share_pack(db_session, sample_pack.id)
    assert shared.status == "shared"


@pytest.mark.asyncio
async def test_share_pack_already_shared(db_session, sample_pack):
    await share_pack(db_session, sample_pack.id)
    with pytest.raises(ValueError, match="Cannot share"):
        await share_pack(db_session, sample_pack.id)


@pytest.mark.asyncio
async def test_share_pack_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await share_pack(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_compare_packs(db_session, sample_pack, sample_pack_transaction):
    result = await compare_packs(db_session, sample_pack.id, sample_pack_transaction.id)
    assert "section_diff" in result
    assert "caveat_diff" in result
    assert "obligations" in result["section_diff"]["only_in_2"]


@pytest.mark.asyncio
async def test_compare_packs_not_found(db_session, sample_pack):
    with pytest.raises(ValueError, match="not found"):
        await compare_packs(db_session, sample_pack.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_list_redaction_profiles(db_session, redaction_profile_insurer):
    profiles = await list_redaction_profiles(db_session)
    assert len(profiles) >= 1
    assert any(p.profile_code == "test-insurer" for p in profiles)


@pytest.mark.asyncio
async def test_get_redaction_profile_by_code(db_session, redaction_profile_insurer):
    profile = await get_redaction_profile_by_code(db_session, "test-insurer")
    assert profile is not None
    assert profile.audience_type == "insurer"


@pytest.mark.asyncio
async def test_get_redaction_profile_by_code_not_found(db_session):
    profile = await get_redaction_profile_by_code(db_session, "nonexistent")
    assert profile is None


@pytest.mark.asyncio
async def test_evaluate_caveats_with_unknowns(db_session, sample_building, caveat_profile_unknown):
    # Create an unknown issue to trigger the caveat
    from app.models.unknown_issue import UnknownIssue

    db_session.add(
        UnknownIssue(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            unknown_type="missing_data",
            title="Missing asbestos diagnostic",
            status="open",
        )
    )
    await db_session.flush()

    caveats = await evaluate_caveats(db_session, sample_building.id, "insurer")
    assert len(caveats) >= 1
    assert any(c["caveat_type"] == "unknown_disclosure" for c in caveats)


@pytest.mark.asyncio
async def test_evaluate_caveats_empty_conditions(db_session, sample_building, caveat_profile_always):
    caveats = await evaluate_caveats(db_session, sample_building.id, "transaction")
    assert len(caveats) >= 1
    assert any(c["caveat_type"] == "regulatory_caveat" for c in caveats)


@pytest.mark.asyncio
async def test_evaluate_caveats_no_match(db_session, sample_building, caveat_profile_unknown):
    # No unknowns → caveat should NOT fire
    caveats = await evaluate_caveats(db_session, sample_building.id, "insurer")
    assert not any(c["caveat_type"] == "unknown_disclosure" for c in caveats)


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_create_audience_pack(client, auth_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/audience-packs",
        json={"pack_type": "insurer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["pack_type"] == "insurer"
    assert body["status"] == "draft"
    assert "content_hash" in body
    assert "sections" in body


@pytest.mark.asyncio
async def test_api_create_audience_pack_invalid_type(client, auth_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/audience-packs",
        json={"pack_type": "invalid_type"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_create_audience_pack_building_not_found(client, auth_headers):
    resp = await client.post(
        f"/api/v1/buildings/{uuid.uuid4()}/audience-packs",
        json={"pack_type": "insurer"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_list_audience_packs(client, auth_headers, sample_building, sample_pack):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/audience-packs",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_api_list_audience_packs_filtered(client, auth_headers, sample_building, sample_pack):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/audience-packs?type=insurer",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert all(p["pack_type"] == "insurer" for p in body)


@pytest.mark.asyncio
async def test_api_get_audience_pack(client, auth_headers, sample_pack):
    resp = await client.get(
        f"/api/v1/audience-packs/{sample_pack.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(sample_pack.id)


@pytest.mark.asyncio
async def test_api_get_audience_pack_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/audience-packs/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_share_audience_pack(client, auth_headers, sample_pack):
    resp = await client.post(
        f"/api/v1/audience-packs/{sample_pack.id}/share",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "shared"


@pytest.mark.asyncio
async def test_api_redaction_profiles(client, auth_headers, redaction_profile_insurer):
    resp = await client.get("/api/v1/redaction-profiles", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_api_redaction_profile_by_code(client, auth_headers, redaction_profile_insurer):
    resp = await client.get("/api/v1/redaction-profiles/test-insurer", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_code"] == "test-insurer"


@pytest.mark.asyncio
async def test_api_redaction_profile_not_found(client, auth_headers):
    resp = await client.get("/api/v1/redaction-profiles/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_building_caveats(client, auth_headers, sample_building, caveat_profile_always):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/caveats?audience=transaction",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_api_building_caveats_building_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/caveats?audience=insurer",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_unauthorized(client):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/audience-packs")
    assert resp.status_code in (401, 403)
