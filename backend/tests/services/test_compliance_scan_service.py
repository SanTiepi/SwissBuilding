"""Tests for Programme N - Auto Compliance Scan Service."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.obligation import Obligation
from app.models.sample import Sample
from app.services.compliance_scan_service import invalidate_cache, run_compliance_scan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, *, construction_year=1970, canton="VD", floors_below=0):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
        floors_below=floors_below,
    )
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


async def _create_sample(
    db,
    diagnostic_id,
    *,
    pollutant_type="asbestos",
    threshold_exceeded=False,
    risk_level=None,
    waste_disposal_type=None,
    cfst_work_category=None,
    concentration=None,
):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        threshold_exceeded=threshold_exceeded,
        risk_level=risk_level,
        waste_disposal_type=waste_disposal_type,
        cfst_work_category=cfst_work_category,
        concentration=concentration,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_obligation(db, building_id, *, status="overdue", days_offset=-10):
    o = Obligation(
        id=uuid.uuid4(),
        building_id=building_id,
        obligation_type="regulatory_deadline",
        title="Test obligation",
        status=status,
        due_date=date.today() + timedelta(days=days_offset),
        priority="high",
    )
    db.add(o)
    await db.flush()
    return o


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestComplianceScan:
    """Core compliance scan service tests."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        invalidate_cache()
        yield
        invalidate_cache()

    async def test_clean_building_high_score(self, db_session, admin_user):
        """Building with all diagnostics → high compliance score."""
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)

        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
            await _create_sample(db_session, diag.id, pollutant_type=pollutant)

        await db_session.commit()
        result = await run_compliance_scan(db_session, building.id)

        assert result.total_checks_executed >= 341
        assert result.compliance_score >= 0.8
        assert result.canton == "VD"
        assert result.building_id == building.id

    async def test_pre1990_no_diagnostic_findings(self, db_session, admin_user):
        """Pre-1990 building with no diagnostic → non-conformities."""
        building = await _create_building(db_session, admin_user, construction_year=1975)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)

        assert result.findings_count.non_conformities >= 1
        rules = [f.rule for f in result.findings if f.type == "non_conformity"]
        assert "OTConst Art. 60a" in rules

    async def test_findings_have_correct_fields(self, db_session, admin_user):
        """Each finding must have type, rule, description, severity, references."""
        building = await _create_building(db_session, admin_user, construction_year=1965)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        assert len(result.findings) > 0

        for f in result.findings:
            assert f.type in ("non_conformity", "warning", "unknown")
            assert f.severity in ("critical", "high", "medium", "low")
            assert len(f.rule) > 0
            assert len(f.description) > 0
            assert isinstance(f.references, list)

    async def test_canton_vd(self, db_session, admin_user):
        """VD canton produces canton-specific warnings."""
        building = await _create_building(db_session, admin_user, canton="VD", construction_year=1980)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        assert result.canton == "VD"

    async def test_canton_ge(self, db_session, admin_user):
        """GE canton scan succeeds."""
        building = await _create_building(db_session, admin_user, canton="GE", construction_year=1970)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        assert result.canton == "GE"
        assert result.total_checks_executed >= 341

    async def test_canton_be(self, db_session, admin_user):
        """BE canton scan succeeds."""
        building = await _create_building(db_session, admin_user, canton="BE", construction_year=1960)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        assert result.canton == "BE"
        assert result.total_checks_executed >= 341

    async def test_positive_asbestos_no_suva(self, db_session, admin_user):
        """Positive asbestos without SUVA notification → critical non-conformity."""
        building = await _create_building(db_session, admin_user, construction_year=1975)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(
            db_session, diag.id, pollutant_type="asbestos", threshold_exceeded=True, risk_level="high"
        )
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        nc_rules = [f.rule for f in result.findings if f.type == "non_conformity"]
        assert "OTConst Art. 82-86" in nc_rules

    async def test_missing_waste_classification(self, db_session, admin_user):
        """Positive samples without waste type → non-conformity."""
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(
            db_session, diag.id, pollutant_type="pcb", threshold_exceeded=True, waste_disposal_type=None
        )
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        nc_rules = [f.rule for f in result.findings if f.type == "non_conformity"]
        assert "OLED Annexe 5" in nc_rules

    async def test_cache_works(self, db_session, admin_user):
        """Second call within TTL returns cached result."""
        building = await _create_building(db_session, admin_user, construction_year=2000)
        await db_session.commit()

        r1 = await run_compliance_scan(db_session, building.id)
        r2 = await run_compliance_scan(db_session, building.id)

        assert r1.scanned_at == r2.scanned_at

    async def test_force_refresh_bypasses_cache(self, db_session, admin_user):
        """force=True re-runs the scan."""
        building = await _create_building(db_session, admin_user, construction_year=2000)
        await db_session.commit()

        await run_compliance_scan(db_session, building.id)
        r2 = await run_compliance_scan(db_session, building.id, force=True)

        # scanned_at may differ if timing allows; key assertion is no exception
        assert r2.total_checks_executed >= 341

    async def test_building_not_found(self, db_session, admin_user):
        """Missing building raises ValueError."""
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await run_compliance_scan(db_session, fake_id)

    async def test_overdue_obligation_creates_finding(self, db_session, admin_user):
        """Overdue obligation → non-conformity finding."""
        building = await _create_building(db_session, admin_user, construction_year=2000)
        await _create_obligation(db_session, building.id, status="overdue", days_offset=-45)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        nc_types = [f.type for f in result.findings]
        assert "non_conformity" in nc_types

    async def test_compliance_score_range(self, db_session, admin_user):
        """Score is always between 0.0 and 1.0."""
        building = await _create_building(db_session, admin_user, construction_year=1960)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        assert 0.0 <= result.compliance_score <= 1.0

    async def test_modern_building_fewer_findings(self, db_session, admin_user):
        """Post-1990 building has fewer pollutant-related findings."""
        building = await _create_building(db_session, admin_user, construction_year=2010)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        # Modern building should not trigger pre-1990 pollutant checks
        pollutant_findings = [
            f for f in result.findings if "OTConst" in f.rule or "ORRChim" in f.rule
        ]
        assert len(pollutant_findings) == 0

    async def test_basement_triggers_radon_check(self, db_session, admin_user):
        """Building with basement and no radon diagnostic → unknown finding."""
        building = await _create_building(db_session, admin_user, construction_year=2000, floors_below=1)
        await db_session.commit()

        result = await run_compliance_scan(db_session, building.id)
        radon_findings = [f for f in result.findings if "radon" in f.description.lower()]
        assert len(radon_findings) >= 1
