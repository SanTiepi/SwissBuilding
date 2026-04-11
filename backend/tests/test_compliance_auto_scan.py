"""Tests for compliance_auto_scan_service."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.services.compliance_auto_scan_service import scan_compliance


async def _create_building(db, admin_user, *, construction_year=1970, canton="VD", cecb_class=None):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        cecb_class=cecb_class,
    )
    db.add(b)
    await db.flush()
    return b


async def _add_diagnostic(db, building_id, diag_type, *, status="completed", conclusion="positive"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=diag_type,
        status=status,
        conclusion=conclusion,
    )
    db.add(d)
    await db.flush()
    return d


@pytest.mark.asyncio
class TestComplianceAutoScan:
    async def test_scan_nonexistent_building(self, db_session):
        """Scan returns None for a nonexistent building."""
        result = await scan_compliance(db_session, uuid.uuid4())
        assert result is None

    async def test_scan_old_building_no_evidence(self, db_session, admin_user):
        """Old building (pre-1960) with no diagnostics → many non-conformities."""
        building = await _create_building(db_session, admin_user, construction_year=1950)

        result = await scan_compliance(db_session, building.id)
        assert result is not None
        assert result.building_id == building.id
        assert result.canton == "VD"
        assert result.total_rules_applicable > 0
        assert result.non_compliant > 0
        assert result.score < 100
        assert len(result.non_conformities) == result.non_compliant
        assert len(result.obligations) == result.non_compliant

    async def test_scan_new_building_fewer_rules(self, db_session, admin_user):
        """New building (post-1991) → asbestos/PCB/lead rules don't apply."""
        building = await _create_building(
            db_session, admin_user, construction_year=2020, cecb_class="B"
        )

        result = await scan_compliance(db_session, building.id)
        assert result is not None
        # Asbestos (max_year=1991), PCB (1990), lead (1960) should NOT apply
        rule_names = [nc.rule for nc in result.non_conformities]
        assert not any("amiante" in r.lower() for r in rule_names)
        assert not any("PCB" in r for r in rule_names)
        assert not any("plomb" in r.lower() for r in rule_names)

    async def test_scan_with_diagnostics_improves_score(self, db_session, admin_user):
        """Adding diagnostics should improve the compliance score."""
        building = await _create_building(db_session, admin_user, construction_year=1970)

        result_before = await scan_compliance(db_session, building.id)
        assert result_before is not None
        score_before = result_before.score

        # Add asbestos, pcb, and lead diagnostics
        await _add_diagnostic(db_session, building.id, "asbestos", conclusion="negative")
        await _add_diagnostic(db_session, building.id, "pcb", conclusion="negative")
        await _add_diagnostic(db_session, building.id, "lead", conclusion="negative")

        result_after = await scan_compliance(db_session, building.id)
        assert result_after is not None
        assert result_after.score > score_before
        assert result_after.compliant > result_before.compliant
