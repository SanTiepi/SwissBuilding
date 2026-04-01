"""Tests for the compliance scanner service (Programme N — Compliance)."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.models.sample import Sample
from app.services.compliance_scanner_service import (
    compute_regulatory_deadlines,
    detect_regulatory_anomalies,
    scan_building_compliance,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, *, construction_year=1970, floors_below=0):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
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


# ---------------------------------------------------------------------------
# Tests: scan_building_compliance
# ---------------------------------------------------------------------------


class TestScanBuildingCompliance:
    async def test_clean_building_high_score(self, db_session, admin_user):
        """Building with completed diag and all pollutants tested → high score."""
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)

        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon", "pfas"):
            await _create_sample(db_session, diag.id, pollutant_type=pollutant)

        await db_session.commit()
        result = await scan_building_compliance(db_session, building.id)

        assert result["score"] >= 80
        assert result["grade"] in ("A", "B")
        assert isinstance(result["non_conformities"], list)
        assert isinstance(result["missing_diagnostics"], list)

    async def test_pre1990_no_diagnostic_low_score(self, db_session, admin_user):
        """Pre-1990 building with no diagnostic → low score."""
        building = await _create_building(db_session, admin_user, construction_year=1975)
        await db_session.commit()

        result = await scan_building_compliance(db_session, building.id)

        assert result["score"] < 80
        # Should have non-conformity for missing diagnostic
        nc_rules = [nc["rule"] for nc in result["non_conformities"]]
        assert "OTConst Art. 60a" in nc_rules

    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await scan_building_compliance(db_session, uuid.uuid4())

    async def test_score_never_negative(self, db_session, admin_user):
        """Score should never go below 0 even with many issues."""
        building = await _create_building(db_session, admin_user, construction_year=1960, floors_below=1)
        await db_session.commit()

        result = await scan_building_compliance(db_session, building.id)
        assert result["score"] >= 0

    async def test_grade_mapping(self, db_session, admin_user):
        """Verify grade is always A-F."""
        building = await _create_building(db_session, admin_user, construction_year=2020)
        await db_session.commit()

        result = await scan_building_compliance(db_session, building.id)
        assert result["grade"] in ("A", "B", "C", "D", "E", "F")

    async def test_positive_asbestos_without_suva_notification(self, db_session, admin_user):
        """Positive asbestos without SUVA notification → non-conformity."""
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="high",
        )
        await db_session.commit()

        result = await scan_building_compliance(db_session, building.id)
        nc_rules = [nc["rule"] for nc in result["non_conformities"]]
        assert "OTConst Art. 82-86" in nc_rules

    async def test_missing_waste_classification(self, db_session, admin_user):
        """Positive samples without waste classification → non-conformity."""
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="pcb",
            threshold_exceeded=True,
            risk_level="high",
        )
        await db_session.commit()

        result = await scan_building_compliance(db_session, building.id)
        nc_rules = [nc["rule"] for nc in result["non_conformities"]]
        assert "OLED" in nc_rules


# ---------------------------------------------------------------------------
# Tests: compute_regulatory_deadlines
# ---------------------------------------------------------------------------


class TestComputeRegulatoryDeadlines:
    async def test_pre1990_asbestos_deadline(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1975)
        await db_session.commit()

        deadlines = await compute_regulatory_deadlines(db_session, building.id)
        asbestos_rules = [d for d in deadlines if "OTConst Art. 82" in d["rule"]]
        assert len(asbestos_rules) >= 1
        assert asbestos_rules[0]["status"] == "required_before_works"

    async def test_asbestos_met_with_diagnostic(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1975)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(db_session, diag.id, pollutant_type="asbestos")
        await db_session.commit()

        deadlines = await compute_regulatory_deadlines(db_session, building.id)
        asbestos_rules = [d for d in deadlines if "OTConst Art. 82" in d["rule"]]
        assert len(asbestos_rules) >= 1
        assert asbestos_rules[0]["status"] == "met"

    async def test_pcb_deadline_for_1960s_building(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1965)
        await db_session.commit()

        deadlines = await compute_regulatory_deadlines(db_session, building.id)
        pcb_rules = [d for d in deadlines if "ORRChim" in d["rule"] and "2.15" in d.get("article", "")]
        assert len(pcb_rules) >= 1
        assert pcb_rules[0]["status"] == "required_before_works"

    async def test_radon_for_basement_building(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=2000, floors_below=1)
        await db_session.commit()

        deadlines = await compute_regulatory_deadlines(db_session, building.id)
        radon_rules = [d for d in deadlines if "ORaP" in d["rule"]]
        assert len(radon_rules) >= 1

    async def test_obligation_based_deadlines(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=2000)
        obl = Obligation(
            id=uuid.uuid4(),
            building_id=building.id,
            title="Annual fire inspection",
            obligation_type="regulatory_inspection",
            due_date=date.today() + timedelta(days=15),
            status="upcoming",
            priority="high",
        )
        db_session.add(obl)
        await db_session.commit()

        deadlines = await compute_regulatory_deadlines(db_session, building.id)
        obl_deadlines = [d for d in deadlines if d["rule"] == "regulatory_inspection"]
        assert len(obl_deadlines) == 1
        assert obl_deadlines[0]["status"] == "due_soon"

    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await compute_regulatory_deadlines(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests: detect_regulatory_anomalies
# ---------------------------------------------------------------------------


class TestDetectRegulatoryAnomalies:
    async def test_missing_asbestos_for_1970_building(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1970)
        await db_session.commit()

        anomalies = await detect_regulatory_anomalies(db_session, building.id)
        types = [a["anomaly_type"] for a in anomalies]
        assert "missing_asbestos_diagnostic" in types

    async def test_missing_pcb_for_1965_building(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1965)
        await db_session.commit()

        anomalies = await detect_regulatory_anomalies(db_session, building.id)
        types = [a["anomaly_type"] for a in anomalies]
        assert "missing_pcb_diagnostic" in types

    async def test_missing_radon_with_basement(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=2000, floors_below=2)
        await db_session.commit()

        anomalies = await detect_regulatory_anomalies(db_session, building.id)
        types = [a["anomaly_type"] for a in anomalies]
        assert "missing_radon_measurement" in types

    async def test_no_anomaly_for_modern_building(self, db_session, admin_user):
        """Post-1990 building without basement should have fewer anomalies."""
        building = await _create_building(db_session, admin_user, construction_year=2020, floors_below=0)
        await db_session.commit()

        anomalies = await detect_regulatory_anomalies(db_session, building.id)
        types = [a["anomaly_type"] for a in anomalies]
        assert "missing_asbestos_diagnostic" not in types
        assert "missing_pcb_diagnostic" not in types
        assert "missing_radon_measurement" not in types

    async def test_unaddressed_high_risk_samples(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="critical",
        )
        await db_session.commit()

        anomalies = await detect_regulatory_anomalies(db_session, building.id)
        types = [a["anomaly_type"] for a in anomalies]
        assert "unaddressed_high_risk" in types

    async def test_high_risk_addressed_with_intervention(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, construction_year=1970)
        diag = await _create_diagnostic(db_session, building.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="critical",
        )
        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=building.id,
            intervention_type="asbestos_removal",
            title="Asbestos removal",
            status="planned",
        )
        db_session.add(intervention)
        await db_session.commit()

        anomalies = await detect_regulatory_anomalies(db_session, building.id)
        types = [a["anomaly_type"] for a in anomalies]
        assert "unaddressed_high_risk" not in types

    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await detect_regulatory_anomalies(db_session, uuid.uuid4())
