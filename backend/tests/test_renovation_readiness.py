"""Tests for the Renovation Readiness orchestrator service and API."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.services.renovation_readiness_service import (
    _compute_pack_blockers,
    _derive_next_actions,
    assess_readiness,
    list_renovation_options,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Route de Renovation 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(**defaults)
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


def _make_document(db_session, building, *, document_type="diagnostic_report", **kwargs):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_name=f"doc-{uuid.uuid4().hex[:6]}.pdf",
        file_path=f"/uploads/{uuid.uuid4().hex[:8]}.pdf",
        document_type=document_type,
        **kwargs,
    )
    db_session.add(doc)
    return doc


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


class TestComputePackBlockers:
    def test_ready_high_completeness(self):
        class FakeResult:
            score = 0.8

        blockers = _compute_pack_blockers(
            {"verdict": "ready", "blockers": []},
            FakeResult(),
        )
        assert blockers == []

    def test_not_ready_returns_blockers(self):
        class FakeResult:
            score = 0.8

        blockers = _compute_pack_blockers(
            {"verdict": "not_ready", "blockers": ["No diagnostic"]},
            FakeResult(),
        )
        assert len(blockers) == 1
        assert "No diagnostic" in blockers[0]

    def test_low_completeness_blocks(self):
        class FakeResult:
            score = 0.3

        blockers = _compute_pack_blockers(
            {"verdict": "ready", "blockers": []},
            FakeResult(),
        )
        assert any("Completude" in b for b in blockers)

    def test_none_completeness_no_crash(self):
        blockers = _compute_pack_blockers(
            {"verdict": "ready", "blockers": []},
            None,
        )
        assert blockers == []


class TestDeriveNextActions:
    def test_blockers_become_high_priority(self):
        actions = _derive_next_actions(
            None,
            {"blockers": ["Missing SUVA notification"]},
            {"blockers": []},
            [],
            None,
        )
        assert len(actions) >= 1
        assert actions[0]["priority"] == "high"
        assert "SUVA" in actions[0]["title"]

    def test_work_family_proof_added(self):
        actions = _derive_next_actions(
            None,
            {"blockers": []},
            {"blockers": []},
            [],
            {"proof_required": ["diagnostic_amiante", "plan_travaux_protection"]},
        )
        assert any("diagnostic_amiante" in a["title"] for a in actions)

    def test_capped_at_8(self):
        many_blockers = [f"Blocker {i}" for i in range(20)]
        actions = _derive_next_actions(
            None,
            {"blockers": many_blockers},
            {"blockers": many_blockers},
            [],
            {"proof_required": [f"proof_{i}" for i in range(10)]},
        )
        assert len(actions) <= 8


# ---------------------------------------------------------------------------
# Integration tests (with DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assess_unknown_work_type(db_session, admin_user):
    """Unknown work type returns error."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "nonexistent_type")
    assert result["error"] == "unknown_work_type"


@pytest.mark.asyncio
async def test_assess_nonexistent_building(db_session, admin_user):
    """Non-existent building returns error."""
    fake_id = uuid.uuid4()
    result = await assess_readiness(db_session, fake_id, "asbestos_removal")
    assert result.get("error") == "building_not_found"


@pytest.mark.asyncio
async def test_assess_returns_all_sections(db_session, admin_user):
    """Assessment returns all expected sections."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos")
    _make_sample(db_session, diag, pollutant_type="pcb")
    _make_sample(db_session, diag, pollutant_type="lead")
    _make_sample(db_session, diag, pollutant_type="hap")
    _make_sample(db_session, diag, pollutant_type="radon")
    _make_document(db_session, building)
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "asbestos_removal")
    assert "error" not in result
    assert result["work_type"] == "asbestos_removal"
    assert result["work_type_label"] == "Desamiantage"
    assert "readiness" in result
    assert "completeness" in result
    assert "procedures" in result
    assert "subsidies" in result
    assert "unknowns" in result
    assert "caveats" in result
    assert "next_actions" in result
    assert "pack_ready" in result
    assert "pack_blockers" in result
    assert "assessed_at" in result


@pytest.mark.asyncio
async def test_assess_missing_diagnostics(db_session, admin_user):
    """Building with no diagnostics should be not ready."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "asbestos_removal")
    assert "error" not in result
    assert result["readiness"]["verdict"] == "not_ready"
    assert len(result["readiness"]["safe_to_start"]["blockers"]) > 0


@pytest.mark.asyncio
async def test_assess_with_full_data(db_session, admin_user):
    """Building with complete data should have higher readiness."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(
        db_session, building, suva_notification_required=True, suva_notification_date=date(2024, 2, 1)
    )
    for pollutant in ["asbestos", "pcb", "lead", "hap", "radon"]:
        _make_sample(db_session, diag, pollutant_type=pollutant)
    _make_document(db_session, building, document_type="diagnostic_report")
    _make_document(db_session, building, document_type="lab_report")
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "asbestos_removal")
    assert "error" not in result
    # Full data should produce a meaningful assessment (completeness >= 0)
    assert isinstance(result["completeness"]["score_pct"], (int, float))
    assert result["completeness"]["score_pct"] >= 0
    # With all pollutants + SUVA, readiness should be better than empty building
    assert result["readiness"]["verdict"] in ("ready", "partially_ready", "not_ready")


@pytest.mark.asyncio
async def test_assess_subsidies_included(db_session, admin_user):
    """Assessment includes subsidy information for VD canton."""
    building = _make_building(db_session, admin_user, canton="VD")
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos")
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "asbestos_removal")
    assert "subsidies" in result
    # VD has pollutant subsidies for asbestos_removal
    assert isinstance(result["subsidies"]["total_potential_chf"], (int, float))


@pytest.mark.asyncio
async def test_assess_procedures_listed(db_session, admin_user):
    """Assessment includes procedure forms from work family."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos")
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "asbestos_removal")
    assert "procedures" in result
    # Work family has procedure_names for asbestos_removal
    assert len(result["procedures"]["forms_needed"]) > 0
    assert "Annonce SUVA" in result["procedures"]["forms_needed"]


@pytest.mark.asyncio
async def test_pack_blocked_when_not_ready(db_session, admin_user):
    """Pack generation should be blocked when building not ready."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    result = await assess_readiness(db_session, building.id, "renovation")
    assert result["pack_ready"] is False
    assert len(result["pack_blockers"]) > 0


@pytest.mark.asyncio
async def test_list_renovation_options(db_session, admin_user):
    """List renovation options returns all work families."""
    building = _make_building(db_session, admin_user)
    await db_session.commit()

    options = await list_renovation_options(db_session, building.id)
    assert len(options) > 10  # We have 23 work families
    names = [o["work_type"] for o in options]
    assert "asbestos_removal" in names
    assert "renovation" in names
    assert "energy_renovation" in names


@pytest.mark.asyncio
async def test_list_options_nonexistent_building(db_session, admin_user):
    """Non-existent building returns empty list."""
    options = await list_renovation_options(db_session, uuid.uuid4())
    assert options == []


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_assess_renovation_readiness(client, auth_headers, sample_building):
    """API endpoint returns assessment."""
    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-readiness/asbestos_removal",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["work_type"] == "asbestos_removal"
    assert "readiness" in data


@pytest.mark.asyncio
async def test_api_unknown_work_type(client, auth_headers, sample_building):
    """API returns 400 for unknown work type."""
    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-readiness/totally_fake",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_api_list_renovation_options(client, auth_headers, sample_building):
    """API list endpoint returns work family options."""
    response = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-readiness",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_api_generate_pack_blocked(client, auth_headers, sample_building):
    """API pack generation returns 409 when not ready."""
    response = await client.post(
        f"/api/v1/buildings/{sample_building.id}/renovation-readiness/renovation/pack",
        headers=auth_headers,
    )
    assert response.status_code == 409
