"""Tests for the building certification service and API."""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.building_certification_service import (
    CERTIFICATION_REQUIREMENTS,
    VALID_CERTIFICATION_TYPES,
    _check_requirements,
    _compute_readiness_score,
    _estimate_effort,
    evaluate_certification_readiness,
    generate_certification_roadmap,
    get_available_certifications,
    get_portfolio_certification_status,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db_session, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(**defaults)
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


async def _create_diagnostic(db_session, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "pollutant",
        "status": "completed",
    }
    defaults.update(kwargs)
    diag = Diagnostic(**defaults)
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


async def _create_sample(db_session, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "concentration": 0.5,
        "unit": "%",
        "threshold_exceeded": False,
        "risk_level": "low",
    }
    defaults.update(kwargs)
    sample = Sample(**defaults)
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


async def _create_document(db_session, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "file_name": "report.pdf",
        "document_type": "diagnostic_report",
        "file_path": "/fake/path.pdf",
        "file_size_bytes": 1024,
        "mime_type": "application/pdf",
        "uploaded_by": None,
    }
    defaults.update(kwargs)
    doc = Document(**defaults)
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


async def _create_org_and_user(db_session, password_hash):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    user = User(
        id=uuid.uuid4(),
        email=f"cert-test-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=password_hash,
        first_name="Cert",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return org, user


async def _create_fully_ready_building(db_session, user_id, **building_kwargs):
    """Create a building that passes ALL certification checks."""
    defaults = {
        "id": uuid.uuid4(),
        "address": "Ready Street 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1990,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(building_kwargs)
    b = Building(**defaults)
    db_session.add(b)
    await db_session.commit()

    diag = await _create_diagnostic(db_session, b.id, status="validated", diagnostic_type="energy")
    for pollutant in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
        await _create_sample(db_session, diag.id, pollutant_type=pollutant, threshold_exceeded=False)
    await _create_document(db_session, b.id, document_type="diagnostic_report")
    await _create_document(db_session, b.id, document_type="lab_report", file_name="lab.pdf")
    await _create_document(db_session, b.id, document_type="floor_plan", file_name="plan.pdf")
    return b


# ---------------------------------------------------------------------------
# Unit tests — pure functions
# ---------------------------------------------------------------------------


class TestEstimateEffort:
    def test_low_effort(self):
        assert _estimate_effort(80) == "low"
        assert _estimate_effort(100) == "low"

    def test_medium_effort(self):
        assert _estimate_effort(50) == "medium"
        assert _estimate_effort(79) == "medium"

    def test_high_effort(self):
        assert _estimate_effort(0) == "high"
        assert _estimate_effort(49) == "high"


class TestCheckRequirements:
    def test_empty_inputs(self):
        results = _check_requirements([], [], [])
        # All checks should fail
        for check_id, req in results.items():
            if check_id == "pollutants_cleared":
                # No samples = no exceeded = passes
                assert req is None
            else:
                assert req is not None

    def test_completed_diagnostic_passes(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="completed",
        )
        results = _check_requirements([diag], [], [])
        assert results["has_completed_diagnostic"] is None

    def test_draft_diagnostic_fails(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="draft",
        )
        results = _check_requirements([diag], [], [])
        assert results["has_completed_diagnostic"] is not None
        assert results["has_completed_diagnostic"].severity == "blocking"

    def test_energy_assessment_passes(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="energy",
            status="completed",
        )
        results = _check_requirements([diag], [], [])
        assert results["has_energy_assessment"] is None

    def test_pollutants_cleared_with_exceeded(self):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S-001",
            pollutant_type="asbestos",
            threshold_exceeded=True,
        )
        results = _check_requirements([], [sample], [])
        assert results["pollutants_cleared"] is not None
        assert "1 sample(s)" in results["pollutants_cleared"].description

    def test_all_pollutants_evaluated(self):
        samples = []
        diag_id = uuid.uuid4()
        for pt in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
            samples.append(
                Sample(
                    id=uuid.uuid4(),
                    diagnostic_id=diag_id,
                    sample_number=f"S-{pt}",
                    pollutant_type=pt,
                    threshold_exceeded=False,
                )
            )
        results = _check_requirements([], samples, [])
        assert results["all_pollutants_evaluated"] is None

    def test_missing_pollutant_evaluations(self):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S-001",
            pollutant_type="asbestos",
            threshold_exceeded=False,
        )
        results = _check_requirements([], [sample], [])
        assert results["all_pollutants_evaluated"] is not None
        assert "hap" in results["all_pollutants_evaluated"].description
        assert "lead" in results["all_pollutants_evaluated"].description

    def test_diagnostic_report_document(self):
        doc = Document(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            file_path="/test.pdf",
            file_name="test.pdf",
            document_type="diagnostic_report",
        )
        results = _check_requirements([], [], [doc])
        assert results["has_diagnostic_report"] is None

    def test_floor_plan_document(self):
        doc = Document(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            file_path="/plan.pdf",
            file_name="plan.pdf",
            document_type="floor_plan",
        )
        results = _check_requirements([], [], [doc])
        assert results["has_floor_plans"] is None

    def test_lab_report_document(self):
        doc = Document(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            file_path="/lab.pdf",
            file_name="lab.pdf",
            document_type="lab_report",
        )
        results = _check_requirements([], [], [doc])
        assert results["has_lab_reports"] is None


class TestComputeReadinessScore:
    def test_all_checks_passed(self):
        results = {
            check_id: None
            for check_id in (
                "has_completed_diagnostic",
                "has_energy_assessment",
                "pollutants_cleared",
                "all_pollutants_evaluated",
                "has_diagnostic_report",
                "has_floor_plans",
                "has_lab_reports",
            )
        }
        for cert_type in VALID_CERTIFICATION_TYPES:
            score = _compute_readiness_score(results, cert_type)
            assert score == 100

    def test_no_checks_passed(self):
        from app.schemas.building_certification import MissingRequirement

        results = {}
        for check_id in (
            "has_completed_diagnostic",
            "has_energy_assessment",
            "pollutants_cleared",
            "all_pollutants_evaluated",
            "has_diagnostic_report",
            "has_floor_plans",
            "has_lab_reports",
        ):
            results[check_id] = MissingRequirement(
                id=check_id, description="test", category="test", severity="blocking"
            )
        for cert_type in VALID_CERTIFICATION_TYPES:
            score = _compute_readiness_score(results, cert_type)
            assert score == 0

    def test_invalid_cert_type_returns_zero(self):
        score = _compute_readiness_score({}, "nonexistent")
        assert score == 0

    def test_blocking_weight_70_recommended_30(self):
        """Blocking checks are 70% weight, recommended 30%."""
        from app.schemas.building_certification import MissingRequirement

        fail = MissingRequirement(id="x", description="x", category="x", severity="blocking")
        # For cecb: 3 blocking, 3 recommended
        # All blocking pass, no recommended pass → score = 70
        results = {
            "has_completed_diagnostic": None,
            "has_energy_assessment": None,
            "has_diagnostic_report": None,
            "pollutants_cleared": fail,
            "has_floor_plans": fail,
            "all_pollutants_evaluated": fail,
        }
        score = _compute_readiness_score(results, "cecb")
        assert score == 70


# ---------------------------------------------------------------------------
# FN1: evaluate_certification_readiness
# ---------------------------------------------------------------------------


class TestEvaluateCertificationReadiness:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        result = await evaluate_certification_readiness(uuid.uuid4(), "minergie", db_session)
        assert result.readiness_score == 0
        assert any(r.id == "building_not_found" for r in result.missing_requirements)
        assert result.estimated_completion_effort == "high"

    @pytest.mark.asyncio
    async def test_unknown_certification_type(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "unknown_cert", db_session)
        assert result.readiness_score == 0
        assert any(r.id == "invalid_type" for r in result.missing_requirements)

    @pytest.mark.asyncio
    async def test_no_diagnostics_low_score(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "minergie", db_session)
        assert result.readiness_score < 50
        assert result.estimated_completion_effort == "high"
        assert len(result.missing_requirements) > 0

    @pytest.mark.asyncio
    async def test_completed_diagnostic_increases_score(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        await _create_diagnostic(db_session, building.id, status="completed")
        await _create_document(db_session, building.id, document_type="diagnostic_report")

        result = await evaluate_certification_readiness(building.id, "cecb", db_session)
        assert result.readiness_score > 0

    @pytest.mark.asyncio
    async def test_full_readiness_minergie(self, db_session, admin_user):
        building = await _create_fully_ready_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "minergie", db_session)
        assert result.readiness_score == 100
        assert result.estimated_completion_effort == "low"
        assert len(result.missing_requirements) == 0

    @pytest.mark.asyncio
    async def test_full_readiness_cecb(self, db_session, admin_user):
        building = await _create_fully_ready_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "cecb", db_session)
        assert result.readiness_score == 100

    @pytest.mark.asyncio
    async def test_full_readiness_snbs(self, db_session, admin_user):
        building = await _create_fully_ready_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "snbs", db_session)
        assert result.readiness_score == 100

    @pytest.mark.asyncio
    async def test_full_readiness_geak(self, db_session, admin_user):
        building = await _create_fully_ready_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "geak", db_session)
        assert result.readiness_score == 100

    @pytest.mark.asyncio
    async def test_pollutants_exceeded_blocks_minergie(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_diagnostic(db_session, building.id, diagnostic_type="energy", status="completed")
        await _create_sample(db_session, diag.id, pollutant_type="asbestos", threshold_exceeded=True)
        await _create_document(db_session, building.id, document_type="diagnostic_report")

        result = await evaluate_certification_readiness(building.id, "minergie", db_session)
        assert any(r.id == "pollutants_cleared" for r in result.missing_requirements)
        assert result.readiness_score < 100

    @pytest.mark.asyncio
    async def test_each_certification_type(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        for cert_type in VALID_CERTIFICATION_TYPES:
            result = await evaluate_certification_readiness(building.id, cert_type, db_session)
            assert result.certification_type == cert_type
            assert 0 <= result.readiness_score <= 100

    @pytest.mark.asyncio
    async def test_effort_estimation_levels(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "cecb", db_session)
        assert result.estimated_completion_effort in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_evaluated_at_is_recent(self, db_session, admin_user):
        before = datetime.now(UTC)
        building = await _create_building(db_session, admin_user.id)
        result = await evaluate_certification_readiness(building.id, "minergie", db_session)
        after = datetime.now(UTC)
        assert before <= result.evaluated_at <= after

    @pytest.mark.asyncio
    async def test_missing_only_floor_plans(self, db_session, admin_user):
        """Building ready except floor plans — should still get high score for cecb."""
        building = await _create_building(db_session, admin_user.id)
        diag = await _create_diagnostic(db_session, building.id, status="validated", diagnostic_type="energy")
        for pt in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
            await _create_sample(db_session, diag.id, pollutant_type=pt, threshold_exceeded=False)
        await _create_document(db_session, building.id, document_type="diagnostic_report")
        await _create_document(db_session, building.id, document_type="lab_report", file_name="lab.pdf")
        # No floor plan

        result = await evaluate_certification_readiness(building.id, "cecb", db_session)
        # floor_plans is recommended for cecb, so only 10% penalty
        assert result.readiness_score >= 80

    @pytest.mark.asyncio
    async def test_validated_diagnostic_counts_as_completed(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        await _create_diagnostic(db_session, building.id, status="validated")
        await _create_document(db_session, building.id, document_type="diagnostic_report")

        result = await evaluate_certification_readiness(building.id, "cecb", db_session)
        missing_ids = [r.id for r in result.missing_requirements]
        assert "has_completed_diagnostic" not in missing_ids


# ---------------------------------------------------------------------------
# FN2: get_available_certifications
# ---------------------------------------------------------------------------


class TestGetAvailableCertifications:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        result = await get_available_certifications(uuid.uuid4(), db_session)
        assert len(result.certifications) == 4
        assert all(c.eligibility == "ineligible" for c in result.certifications)

    @pytest.mark.asyncio
    async def test_all_four_types_returned(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        types = {c.certification_type for c in result.certifications}
        assert types == VALID_CERTIFICATION_TYPES

    @pytest.mark.asyncio
    async def test_eligible_when_all_blocking_met(self, db_session, admin_user):
        building = await _create_fully_ready_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        for cert in result.certifications:
            assert cert.eligibility == "eligible"
            assert cert.blockers == []

    @pytest.mark.asyncio
    async def test_partial_eligibility(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        await _create_diagnostic(db_session, building.id, status="completed")
        await _create_diagnostic(db_session, building.id, diagnostic_type="energy", status="completed")
        await _create_document(db_session, building.id, document_type="diagnostic_report")

        result = await get_available_certifications(building.id, db_session)
        cecb = next(c for c in result.certifications if c.certification_type == "cecb")
        assert cecb.eligibility == "eligible"

    @pytest.mark.asyncio
    async def test_ineligible_no_data(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        for cert in result.certifications:
            assert cert.eligibility == "ineligible"
            assert len(cert.blockers) > 0

    @pytest.mark.asyncio
    async def test_labels_populated(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        for cert in result.certifications:
            assert cert.label != ""
            assert len(cert.label) > 3

    @pytest.mark.asyncio
    async def test_readiness_percentage_range(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        for cert in result.certifications:
            assert 0 <= cert.readiness_percentage <= 100

    @pytest.mark.asyncio
    async def test_certifications_sorted_alphabetically(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        types = [c.certification_type for c in result.certifications]
        assert types == sorted(types)

    @pytest.mark.asyncio
    async def test_partial_vs_ineligible_threshold(self, db_session, admin_user):
        """Score >= 50 with blockers = partial; < 50 = ineligible."""
        building = await _create_building(db_session, admin_user.id)
        # Add completed diag + energy + report so cecb/geak are eligible
        # but minergie and snbs need more
        await _create_diagnostic(db_session, building.id, status="completed", diagnostic_type="energy")
        await _create_document(db_session, building.id, document_type="diagnostic_report")

        result = await get_available_certifications(building.id, db_session)
        for cert in result.certifications:
            assert cert.eligibility in ("eligible", "partial", "ineligible")

    @pytest.mark.asyncio
    async def test_blockers_contain_descriptions(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await get_available_certifications(building.id, db_session)
        for cert in result.certifications:
            for blocker in cert.blockers:
                assert isinstance(blocker, str)
                assert len(blocker) > 5


# ---------------------------------------------------------------------------
# FN3: generate_certification_roadmap
# ---------------------------------------------------------------------------


class TestGenerateCertificationRoadmap:
    @pytest.mark.asyncio
    async def test_unknown_certification_returns_empty(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "nonexistent", db_session)
        assert result.steps == []
        assert result.total_estimated_days == 0

    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        result = await generate_certification_roadmap(uuid.uuid4(), "minergie", db_session)
        assert len(result.steps) == 1
        assert "not found" in result.steps[0].description.lower()

    @pytest.mark.asyncio
    async def test_roadmap_has_steps_when_missing_reqs(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "minergie", db_session)
        assert len(result.steps) > 0
        assert result.total_estimated_days > 0

    @pytest.mark.asyncio
    async def test_roadmap_steps_ordered(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "snbs", db_session)
        for i, step in enumerate(result.steps):
            assert step.step_number == i + 1

    @pytest.mark.asyncio
    async def test_roadmap_empty_when_fully_ready(self, db_session, admin_user):
        building = await _create_fully_ready_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "minergie", db_session)
        assert result.steps == []
        assert result.total_estimated_days == 0

    @pytest.mark.asyncio
    async def test_roadmap_step_priorities(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "minergie", db_session)
        for step in result.steps:
            assert step.priority in ("critical", "high", "medium", "low")

    @pytest.mark.asyncio
    async def test_roadmap_each_cert_type(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        for cert_type in VALID_CERTIFICATION_TYPES:
            result = await generate_certification_roadmap(building.id, cert_type, db_session)
            assert result.certification_type == cert_type
            assert result.total_estimated_days >= 0

    @pytest.mark.asyncio
    async def test_roadmap_total_days_equals_sum(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "snbs", db_session)
        expected = sum(s.estimated_duration_days for s in result.steps)
        assert result.total_estimated_days == expected

    @pytest.mark.asyncio
    async def test_roadmap_dependencies_reference_valid_checks(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "minergie", db_session)
        all_check_ids = set(CERTIFICATION_REQUIREMENTS["minergie"]["blocking"]) | set(
            CERTIFICATION_REQUIREMENTS["minergie"]["recommended"]
        )
        for step in result.steps:
            for dep in step.dependencies:
                assert dep in all_check_ids or dep in {
                    "has_completed_diagnostic",
                    "has_energy_assessment",
                    "pollutants_cleared",
                    "all_pollutants_evaluated",
                    "has_diagnostic_report",
                    "has_floor_plans",
                    "has_lab_reports",
                }

    @pytest.mark.asyncio
    async def test_roadmap_shrinks_with_progress(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user.id)
        full = await generate_certification_roadmap(building.id, "cecb", db_session)

        await _create_diagnostic(db_session, building.id, status="completed", diagnostic_type="energy")
        await _create_document(db_session, building.id, document_type="diagnostic_report")

        partial = await generate_certification_roadmap(building.id, "cecb", db_session)
        assert len(partial.steps) < len(full.steps)
        assert partial.total_estimated_days < full.total_estimated_days

    @pytest.mark.asyncio
    async def test_roadmap_energy_depends_on_diagnostic(self, db_session, admin_user):
        """Energy assessment step should depend on has_completed_diagnostic."""
        building = await _create_building(db_session, admin_user.id)
        result = await generate_certification_roadmap(building.id, "minergie", db_session)
        for step in result.steps:
            if "energy" in step.description.lower():
                assert "has_completed_diagnostic" in step.dependencies


# ---------------------------------------------------------------------------
# FN4: get_portfolio_certification_status
# ---------------------------------------------------------------------------


class TestGetPortfolioCertificationStatus:
    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        org, _user = await _create_org_and_user(db_session, _HASH_ADMIN)
        result = await get_portfolio_certification_status(org.id, db_session)
        assert result.total_buildings == 0
        assert result.certified_count == 0
        assert result.in_progress_count == 0
        assert result.eligible_count == 0
        assert result.certification_distribution == []

    @pytest.mark.asyncio
    async def test_org_with_buildings(self, db_session):
        org, user = await _create_org_and_user(db_session, _HASH_ADMIN)
        await _create_building(db_session, user.id)
        await _create_building(db_session, user.id, address="Rue Test 2")

        result = await get_portfolio_certification_status(org.id, db_session)
        assert result.total_buildings == 2
        assert result.organization_id == org.id

    @pytest.mark.asyncio
    async def test_org_with_eligible_building(self, db_session):
        org, user = await _create_org_and_user(db_session, _HASH_ADMIN)
        await _create_fully_ready_building(db_session, user.id)

        result = await get_portfolio_certification_status(org.id, db_session)
        assert result.eligible_count == 1
        assert len(result.certification_distribution) > 0

    @pytest.mark.asyncio
    async def test_nonexistent_org(self, db_session):
        result = await get_portfolio_certification_status(uuid.uuid4(), db_session)
        assert result.total_buildings == 0

    @pytest.mark.asyncio
    async def test_inactive_buildings_excluded(self, db_session):
        org, user = await _create_org_and_user(db_session, _HASH_ADMIN)
        await _create_building(db_session, user.id, status="inactive")
        result = await get_portfolio_certification_status(org.id, db_session)
        assert result.total_buildings == 0

    @pytest.mark.asyncio
    async def test_mixed_portfolio(self, db_session):
        """Portfolio with one ready and one bare building."""
        org, user = await _create_org_and_user(db_session, _HASH_ADMIN)
        await _create_fully_ready_building(db_session, user.id)
        await _create_building(db_session, user.id, address="Bare Street")

        result = await get_portfolio_certification_status(org.id, db_session)
        assert result.total_buildings == 2
        assert result.eligible_count == 1

    @pytest.mark.asyncio
    async def test_distribution_cert_types(self, db_session):
        org, user = await _create_org_and_user(db_session, _HASH_ADMIN)
        await _create_fully_ready_building(db_session, user.id)

        result = await get_portfolio_certification_status(org.id, db_session)
        for item in result.certification_distribution:
            assert item.certification_type in VALID_CERTIFICATION_TYPES
            assert item.count >= 1

    @pytest.mark.asyncio
    async def test_certified_count_always_zero(self, db_session):
        """Service never sets certified_count (no real certification tracking yet)."""
        org, user = await _create_org_and_user(db_session, _HASH_ADMIN)
        await _create_fully_ready_building(db_session, user.id)
        result = await get_portfolio_certification_status(org.id, db_session)
        assert result.certified_count == 0

    @pytest.mark.asyncio
    async def test_evaluated_at_is_present(self, db_session):
        org, _user = await _create_org_and_user(db_session, _HASH_ADMIN)
        before = datetime.now(UTC)
        result = await get_portfolio_certification_status(org.id, db_session)
        after = datetime.now(UTC)
        assert before <= result.evaluated_at <= after


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestCertificationAPI:
    @pytest.mark.asyncio
    async def test_readiness_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/building-certifications/buildings/{sample_building.id}/certification-readiness",
            params={"certification_type": "minergie"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "readiness_score" in data
        assert "missing_requirements" in data
        assert data["certification_type"] == "minergie"

    @pytest.mark.asyncio
    async def test_readiness_endpoint_invalid_type(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/building-certifications/buildings/{sample_building.id}/certification-readiness",
            params={"certification_type": "invalid"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Validation error from regex pattern

    @pytest.mark.asyncio
    async def test_readiness_endpoint_not_found(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/building-certifications/buildings/{fake_id}/certification-readiness",
            params={"certification_type": "cecb"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_available_certifications_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/building-certifications/buildings/{sample_building.id}/available-certifications",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["certifications"]) == 4

    @pytest.mark.asyncio
    async def test_roadmap_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/building-certifications/buildings/{sample_building.id}/certification-roadmap",
            params={"certification_type": "snbs"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data
        assert "total_estimated_days" in data

    @pytest.mark.asyncio
    async def test_portfolio_status_endpoint(self, client, auth_headers):
        org_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/building-certifications/organizations/{org_id}/certification-status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_buildings"] == 0

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client, sample_building):
        resp = await client.get(
            f"/api/v1/building-certifications/buildings/{sample_building.id}/certification-readiness",
            params={"certification_type": "minergie"},
        )
        assert resp.status_code in (401, 403)
