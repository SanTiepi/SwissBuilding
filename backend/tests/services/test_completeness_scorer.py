"""Tests for 16-dimension Completeness Scorer (Programme I)."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.completeness_scorer import (
    DIMENSIONS,
    TOTAL_WEIGHT,
    _score_building_metadata,
    _score_energy_data,
    _score_environmental_exposure,
    _score_field_observations,
    _score_hazardous_materials,
    _score_legal_documents,
    _score_maintenance_manual,
    _score_materials_inventory,
    _score_owner_occupant,
    _score_photos_evidence,
    _score_post_works,
    _score_regulatory_compliance,
    _score_remediation_plan,
    _score_repair_history,
    _score_structural_health,
    _score_third_party_inspections,
    calculate_completeness,
    get_missing_items,
    get_recommended_actions,
    score_color,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, **overrides):
    defaults = dict(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    defaults.update(overrides)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, *, status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full_pollutant",
        status=status,
        date_inspection=date.today() - timedelta(days=30),
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, *, pollutant_type="asbestos", concentration=50.0, unit="mg/kg",
                          threshold_exceeded=False, risk_level="low"):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        location_floor="1",
        concentration=concentration,
        unit=unit,
        threshold_exceeded=threshold_exceeded,
        risk_level=risk_level,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_document(db, building_id, *, document_type="report"):
    d = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        document_type=document_type,
        file_name="test.pdf",
        file_path="/test/path",
    )
    db.add(d)
    await db.flush()
    return d


async def _create_zone(db, building_id):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="floor",
        name="Floor 1",
    )
    db.add(z)
    await db.flush()
    return z


async def _create_element(db, building_id):
    z = await _create_zone(db, building_id)
    e = BuildingElement(
        id=uuid.uuid4(),
        zone_id=z.id,
        element_type="wall",
        name="Test Wall",
    )
    db.add(e)
    await db.flush()
    return e


async def _create_intervention(db, building_id, *, status="completed"):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        title="Test Intervention",
        intervention_type="remediation",
        status=status,
    )
    db.add(i)
    await db.flush()
    return i


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDimensionConstants:
    def test_16_dimensions_defined(self):
        assert len(DIMENSIONS) == 16

    def test_total_weight_is_210(self):
        assert TOTAL_WEIGHT == 210

    def test_all_dimension_keys_unique(self):
        keys = [k for k, _, _ in DIMENSIONS]
        assert len(keys) == len(set(keys))


@pytest.mark.asyncio
class TestScoreColor:
    def test_green_at_90(self):
        assert score_color(90) == "green"

    def test_green_at_100(self):
        assert score_color(100) == "green"

    def test_yellow_at_70(self):
        assert score_color(70) == "yellow"

    def test_orange_at_50(self):
        assert score_color(50) == "orange"

    def test_red_at_49(self):
        assert score_color(49) == "red"

    def test_red_at_0(self):
        assert score_color(0) == "red"


@pytest.mark.asyncio
class TestBuildingMetadata:
    async def test_full_metadata(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        score, missing, actions = _score_building_metadata(b)
        assert score > 0
        assert isinstance(missing, list)
        assert isinstance(actions, list)

    async def test_empty_building_scores_low(self, db_session, admin_user):
        b = Building(id=uuid.uuid4(), created_by=admin_user.id, owner_id=admin_user.id, status="active")
        score, missing, _ = _score_building_metadata(b)
        assert score < 50
        assert len(missing) > 0


@pytest.mark.asyncio
class TestEnergyData:
    async def test_no_energy_data(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        score, missing, _ = _score_energy_data(b, [])
        assert score < 100
        assert len(missing) > 0

    async def test_with_energy_document(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        doc = await _create_document(db_session, b.id, document_type="cecb")
        score, _, _ = _score_energy_data(b, [doc])
        assert score > 0


@pytest.mark.asyncio
class TestHazardousMaterials:
    async def test_no_diagnostics(self, db_session, admin_user):
        score, missing, _ = _score_hazardous_materials([], [])
        assert score == 0.0
        assert any(m["field"] == "diagnostic" for m in missing)

    async def test_with_all_pollutants(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        diag = await _create_diagnostic(db_session, b.id)
        samples = []
        for p in ("asbestos", "pcb", "lead", "hap", "radon"):
            s = await _create_sample(db_session, diag.id, pollutant_type=p)
            samples.append(s)
        score, _missing, _ = _score_hazardous_materials(samples, [diag])
        assert score == 100.0

    async def test_partial_pollutants(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        diag = await _create_diagnostic(db_session, b.id)
        s = await _create_sample(db_session, diag.id, pollutant_type="asbestos")
        score, _missing, _ = _score_hazardous_materials([s], [diag])
        assert 0 < score < 100


@pytest.mark.asyncio
class TestStructuralHealth:
    async def test_no_data(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        score, missing, _ = _score_structural_health(b)
        assert score < 100
        assert len(missing) > 0


@pytest.mark.asyncio
class TestEnvironmentalExposure:
    async def test_no_data(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        score, _missing, _ = _score_environmental_exposure(b)
        assert score < 100


@pytest.mark.asyncio
class TestRegulatoryCompliance:
    async def test_no_samples_is_100(self):
        score, _, _ = _score_regulatory_compliance([], [])
        assert score == 100.0

    async def test_positive_asbestos_no_suva(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        diag = await _create_diagnostic(db_session, b.id)
        s = await _create_sample(db_session, diag.id, pollutant_type="asbestos", threshold_exceeded=True)
        score, missing, _ = _score_regulatory_compliance([s], [diag])
        assert score < 100
        assert any(m["field"] == "suva_notification" for m in missing)


@pytest.mark.asyncio
class TestMaterialsInventory:
    async def test_no_elements(self):
        score, missing, _actions = _score_materials_inventory([])
        assert score == 0.0
        assert len(missing) > 0

    async def test_10_elements_is_100(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        elements = []
        for _ in range(10):
            e = await _create_element(db_session, b.id)
            elements.append(e)
        score, _, _ = _score_materials_inventory(elements)
        assert score == 100.0


@pytest.mark.asyncio
class TestRepairHistory:
    async def test_no_interventions(self):
        score, _missing, _ = _score_repair_history([])
        assert score == 0.0

    async def test_completed_interventions(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        i = await _create_intervention(db_session, b.id, status="completed")
        score, _, _ = _score_repair_history([i])
        assert score == 100.0


@pytest.mark.asyncio
class TestOwnerOccupant:
    async def test_no_owner_name(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        score, _missing, _ = _score_owner_occupant(b)
        assert score < 100

    async def test_no_owner_fields_scores_zero(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        score, missing, _ = _score_owner_occupant(b)
        # Building model doesn't have owner_name/contact_email/contact_phone columns
        assert score == 0.0
        assert len(missing) == 3


@pytest.mark.asyncio
class TestLegalDocuments:
    async def test_no_docs(self):
        score, _missing, _ = _score_legal_documents([])
        assert score == 0.0

    async def test_with_permit(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        doc = await _create_document(db_session, b.id, document_type="building_permit")
        score, _, _ = _score_legal_documents([doc])
        assert score > 0


@pytest.mark.asyncio
class TestPhotosEvidence:
    async def test_no_photos(self):
        score, _, _ = _score_photos_evidence([])
        assert score == 0.0


@pytest.mark.asyncio
class TestFieldObservations:
    async def test_no_actions(self):
        score, _, _ = _score_field_observations([])
        assert score == 0.0


@pytest.mark.asyncio
class TestThirdPartyInspections:
    async def test_no_diagnostics(self):
        score, _missing, _ = _score_third_party_inspections([])
        assert score == 0.0

    async def test_completed_diagnostics(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        d1 = await _create_diagnostic(db_session, b.id)
        d2 = await _create_diagnostic(db_session, b.id)
        score, _, _ = _score_third_party_inspections([d1, d2])
        assert score == 100.0


@pytest.mark.asyncio
class TestRemediationPlan:
    async def test_no_data(self):
        score, _missing, _ = _score_remediation_plan([], [])
        assert score == 0.0

    async def test_with_plan(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        i = await _create_intervention(db_session, b.id, status="planned")
        doc = await _create_document(db_session, b.id, document_type="remediation_plan")
        score, _, _ = _score_remediation_plan([i], [doc])
        assert score == 100.0


@pytest.mark.asyncio
class TestPostWorks:
    async def test_no_data(self):
        score, _, _ = _score_post_works([], [])
        assert score == 0.0

    async def test_with_completion(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        i = await _create_intervention(db_session, b.id, status="completed")
        doc = await _create_document(db_session, b.id, document_type="completion_certificate")
        score, _, _ = _score_post_works([i], [doc])
        assert score == 100.0


@pytest.mark.asyncio
class TestMaintenanceManual:
    async def test_no_manual(self):
        score, _, _ = _score_maintenance_manual([])
        assert score == 0.0

    async def test_with_manual(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        doc = await _create_document(db_session, b.id, document_type="maintenance_manual")
        score, _, _ = _score_maintenance_manual([doc])
        assert score == 100.0


@pytest.mark.asyncio
class TestCalculateCompleteness:
    async def test_building_not_found(self, db_session, admin_user):
        result = await calculate_completeness(db_session, uuid.uuid4())
        assert result["overall_score"] == 0.0

    async def test_empty_building(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_completeness(db_session, b.id)
        assert 0 <= result["overall_score"] <= 100
        assert len(result["dimensions"]) == 16
        assert result["trend"] in ("improving", "stable", "declining")

    async def test_dimensions_have_required_keys(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        result = await calculate_completeness(db_session, b.id)
        for dim in result["dimensions"]:
            assert "key" in dim
            assert "label" in dim
            assert "score" in dim
            assert "max_weight" in dim
            assert "color" in dim
            assert "missing_items" in dim
            assert "required_actions" in dim

    async def test_well_documented_building(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        diag = await _create_diagnostic(db_session, b.id)
        for p in ("asbestos", "pcb", "lead", "hap", "radon"):
            await _create_sample(db_session, diag.id, pollutant_type=p)
        for dt in ("diagnostic_report", "cecb", "building_permit", "insurance", "photo"):
            await _create_document(db_session, b.id, document_type=dt)
        for _ in range(10):
            await _create_element(db_session, b.id)
        await _create_intervention(db_session, b.id, status="completed")

        result = await calculate_completeness(db_session, b.id)
        assert result["overall_score"] > 30  # well-documented = decent score


@pytest.mark.asyncio
class TestGetMissingItems:
    async def test_returns_list(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        items = await get_missing_items(db_session, b.id)
        assert isinstance(items, list)
        if items:
            assert "field" in items[0]
            assert "importance" in items[0]
            assert "dimension" in items[0]


@pytest.mark.asyncio
class TestGetRecommendedActions:
    async def test_returns_sorted(self, db_session, admin_user):
        b = await _create_building(db_session, admin_user)
        actions = await get_recommended_actions(db_session, b.id)
        assert isinstance(actions, list)
        # Should be sorted critical-first
        priorities = [a.get("priority", "") for a in actions]
        critical_indices = [i for i, p in enumerate(priorities) if p == "critical"]
        non_critical_indices = [i for i, p in enumerate(priorities) if p != "critical"]
        if critical_indices and non_critical_indices:
            assert max(critical_indices) < min(non_critical_indices)
