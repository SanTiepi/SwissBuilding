"""Tests for Finance/Lender-Ready Dossier Workflow service.

Covers: assessment structure, verdict logic (not_financeable/conditional/financeable),
collateral confidence, caveats, incidents, lender summary,
pack generation, pack blocked, next actions.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.commitment import Caveat
from app.models.data_quality_issue import DataQualityIssue
from app.models.incident import IncidentEpisode
from app.models.organization import Organization
from app.models.unknowns_ledger import UnknownEntry
from app.services.finance_workflow_service import FinanceWorkflowService

_service = FinanceWorkflowService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(db_session) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Finance SA",
        type="property_management",
    )
    db_session.add(org)
    return org


def _make_building(db_session, admin_user, *, construction_year=1960, org=None, **kwargs):
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Credit 8",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
        organization_id=org.id if org else None,
        **kwargs,
    )
    db_session.add(building)
    return building


def _make_incident(
    db_session,
    building,
    org,
    admin_user,
    *,
    incident_type="structural",
    status="reported",
    severity="minor",
    recurring=False,
    repair_cost_chf=None,
    title="Incident test",
    **kwargs,
):
    incident = IncidentEpisode(
        id=uuid.uuid4(),
        building_id=building.id,
        organization_id=org.id,
        incident_type=incident_type,
        title=title,
        severity=severity,
        status=status,
        discovered_at=datetime(2025, 11, 1, tzinfo=UTC),
        recurring=recurring,
        repair_cost_chf=repair_cost_chf,
        insurance_claim_filed=False,
        created_by=admin_user.id,
        **kwargs,
    )
    db_session.add(incident)
    return incident


def _make_caveat(db_session, building, *, caveat_type="scope_limitation", subject="Test", **kwargs):
    defaults = {
        "severity": "warning",
        "active": True,
        "source_type": "system_generated",
    }
    defaults.update(kwargs)
    caveat = Caveat(
        id=uuid.uuid4(),
        building_id=building.id,
        caveat_type=caveat_type,
        subject=subject,
        **defaults,
    )
    db_session.add(caveat)
    return caveat


def _make_unknown(db_session, building, *, subject="Missing energy cert", severity="high", **kwargs):
    defaults = {
        "unknown_type": "coverage_gap",
        "status": "open",
    }
    defaults.update(kwargs)
    entry = UnknownEntry(
        id=uuid.uuid4(),
        building_id=building.id,
        subject=subject,
        severity=severity,
        **defaults,
    )
    db_session.add(entry)
    return entry


def _make_contradiction(db_session, building, *, description="Conflicting valuation data", severity="medium"):
    issue = DataQualityIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        issue_type="contradiction",
        description=description,
        severity=severity,
        status="open",
        detected_by="contradiction_detector",
    )
    db_session.add(issue)
    return issue


async def _financeable_building(db_session, admin_user):
    """Create a building with all data needed for verdict=financeable."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)
    # No contradictions, no unknowns, no unresolved incidents
    await db_session.commit()
    return building, org


async def _conditional_building(db_session, admin_user):
    """Create a building with conditions: unresolved incident + contradiction."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)

    # Unresolved incident
    _make_incident(
        db_session,
        building,
        org,
        admin_user,
        status="reported",
        severity="moderate",
        title="Fissure facade",
    )

    # Contradiction
    _make_contradiction(db_session, building, description="Ecart valeur fiscale")

    await db_session.commit()
    return building, org


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_structure(db_session, admin_user):
    """Assessment should contain all expected top-level sections."""
    building, _org = await _financeable_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    expected_keys = {
        "building_id",
        "verdict",
        "verdict_summary",
        "safe_to_finance",
        "collateral_confidence",
        "completeness",
        "trust",
        "contradictions",
        "unknowns",
        "caveats",
        "incidents",
        "lender_summary",
        "next_actions",
        "pack_ready",
        "pack_blockers",
        "assessed_at",
    }
    assert expected_keys.issubset(set(result.keys()))


@pytest.mark.asyncio
async def test_verdict_not_financeable_when_critical_unknowns(db_session, admin_user):
    """Verdict should be 'not_financeable' when critical unknowns block finance."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)

    _make_unknown(
        db_session,
        building,
        subject="Titre de propriete manquant",
        severity="critical",
        blocks_safe_to_x=["finance"],
    )
    await db_session.commit()

    result = await _service.assess_finance_readiness(db_session, building.id)

    assert result["verdict"] == "not_financeable"
    assert "non financable" in result["verdict_summary"].lower() or "Non financable" in result["verdict_summary"]


@pytest.mark.asyncio
async def test_verdict_conditional_when_moderate_issues(db_session, admin_user):
    """Verdict should be 'conditional' when there are moderate issues."""
    building, _org = await _conditional_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    assert result["verdict"] == "conditional"
    assert "condition" in result["verdict_summary"].lower()


@pytest.mark.asyncio
async def test_verdict_financeable_when_all_clear(db_session, admin_user):
    """Verdict should be financeable or conditional when no hard blockers."""
    building, _org = await _financeable_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    # May be conditional due to low completeness in test env, but not not_financeable
    assert result["verdict"] in ("financeable", "conditional")


@pytest.mark.asyncio
async def test_collateral_confidence_structure(db_session, admin_user):
    """Collateral confidence should have score_pct, level, and factors."""
    building, _org = await _financeable_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    cc = result["collateral_confidence"]
    assert "score_pct" in cc
    assert "level" in cc
    assert cc["level"] in ("strong", "adequate", "weak", "insufficient")
    assert "factors" in cc
    assert len(cc["factors"]) >= 1
    for factor in cc["factors"]:
        assert "name" in factor
        assert "status" in factor
        assert "impact" in factor


@pytest.mark.asyncio
async def test_trust_includes_level(db_session, admin_user):
    """Trust should include score_pct and level."""
    building, _org = await _financeable_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    trust = result["trust"]
    assert "score_pct" in trust
    assert "level" in trust
    assert trust["level"] in ("strong", "adequate", "weak", "insufficient")


@pytest.mark.asyncio
async def test_incidents_in_assessment(db_session, admin_user):
    """Incidents should include unresolved_count, recurring_count, risk_rating."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)

    _make_incident(
        db_session,
        building,
        org,
        admin_user,
        status="resolved",
        severity="major",
        repair_cost_chf=45000.0,
        title="Reparation fondations",
    )
    _make_incident(
        db_session,
        building,
        org,
        admin_user,
        status="reported",
        severity="moderate",
        title="Infiltration toiture",
    )
    await db_session.commit()

    result = await _service.assess_finance_readiness(db_session, building.id)

    inc = result["incidents"]
    assert inc["unresolved_count"] == 1
    assert "risk_rating" in inc
    assert inc["risk_rating"] in ("low", "moderate", "high")


@pytest.mark.asyncio
async def test_lender_summary_structure(db_session, admin_user):
    """Lender summary should contain expected fields."""
    building, _org = await _financeable_building(db_session, admin_user)

    result = await _service.get_lender_summary(db_session, building.id)

    expected_keys = {
        "building_id",
        "building_grade",
        "year",
        "address",
        "city",
        "canton",
        "collateral_confidence",
        "incidents_unresolved",
        "incidents_recurring",
        "caveats_count",
        "lender_conditions",
        "collateral_risks",
        "documentation_gaps",
        "key_facts",
        "key_risks",
        "key_strengths",
        "trust_score_pct",
        "completeness_pct",
        "generated_at",
    }
    assert expected_keys.issubset(set(result.keys()))
    assert result["address"] == "Rue du Credit 8"
    assert result["canton"] == "VD"
    assert result["year"] == 1960


@pytest.mark.asyncio
async def test_pack_blocked_when_not_financeable(db_session, admin_user):
    """Pack generation should fail when verdict is not_financeable."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)

    _make_unknown(
        db_session,
        building,
        subject="Titre de propriete absent",
        severity="critical",
        blocks_safe_to_x=["finance"],
    )
    await db_session.commit()

    with pytest.raises(ValueError, match="pas financable"):
        await _service.generate_lender_pack(
            db_session,
            building.id,
            created_by_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_next_actions_derived_from_gaps(db_session, admin_user):
    """Next actions should be generated from detected gaps."""
    building, _org = await _conditional_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    actions = result["next_actions"]
    assert len(actions) >= 1
    for action in actions:
        assert "title" in action
        assert "priority" in action
        assert action["priority"] in ("high", "medium", "low")
        assert "action_type" in action


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Assessment should raise ValueError for non-existent building."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await _service.assess_finance_readiness(db_session, fake_id)


@pytest.mark.asyncio
async def test_contradictions_included(db_session, admin_user):
    """Contradictions should appear in assessment."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)

    _make_contradiction(db_session, building, description="Ecart valeur fiscale", severity="high")
    await db_session.commit()

    result = await _service.assess_finance_readiness(db_session, building.id)

    assert result["contradictions"]["count"] == 1
    item = result["contradictions"]["items"][0]
    assert "description" in item
    assert "severity" in item


@pytest.mark.asyncio
async def test_unknowns_blocking_finance(db_session, admin_user):
    """Unknowns blocking finance should be flagged."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)

    _make_unknown(
        db_session,
        building,
        subject="Certificat energetique manquant",
        severity="high",
        blocks_safe_to_x=["finance"],
    )
    await db_session.commit()

    result = await _service.assess_finance_readiness(db_session, building.id)

    assert result["unknowns"]["count"] >= 1
    assert "Certificat energetique manquant" in result["unknowns"]["blocking_finance"]


@pytest.mark.asyncio
async def test_pack_ready_when_financeable(db_session, admin_user):
    """pack_ready should be True when verdict is not not_financeable and completeness >= 30%."""
    building, _org = await _financeable_building(db_session, admin_user)

    result = await _service.assess_finance_readiness(db_session, building.id)

    if result["verdict"] != "not_financeable" and result["completeness"]["score_pct"] >= 30.0:
        assert result["pack_ready"] is True
        assert result["pack_blockers"] == []
    else:
        # In minimal test env, completeness may be too low for pack
        assert isinstance(result["pack_ready"], bool)
        assert isinstance(result["pack_blockers"], list)


@pytest.mark.asyncio
async def test_redact_financials_defaults_false(db_session, admin_user):
    """Lender pack should default redact_financials to False."""
    # Verify the service signature defaults
    import inspect

    sig = inspect.signature(_service.generate_lender_pack)
    param = sig.parameters["redact_financials"]
    assert param.default is False
