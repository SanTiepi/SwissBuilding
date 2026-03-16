"""Tests for the campaign_recommender service."""

import uuid

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.campaign_recommender import recommend_campaigns

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, construction_year=1970, canton="VD"):
    b = Building(
        id=uuid.uuid4(),
        address=f"Rue Test {construction_year}",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="avant_travaux",
        status=status,
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, pollutant="asbestos", exceeded=True):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant,
        location_room="Salle 1",
        material_category="Flocage",
        threshold_exceeded=exceeded,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_risk_score(db, building_id, level="critical"):
    rs = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building_id,
        asbestos_probability=0.9,
        pcb_probability=0.1,
        lead_probability=0.1,
        hap_probability=0.1,
        radon_probability=0.1,
        overall_risk_level=level,
        confidence=0.8,
    )
    db.add(rs)
    await db.flush()
    return rs


async def _create_action(db, building_id, priority="critical", status="open"):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        title=f"Action {priority}",
        description="Test action",
        source_type="diagnostic",
        action_type="remediation",
        priority=priority,
        status=status,
    )
    db.add(a)
    await db.flush()
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecommendCampaigns:
    async def test_empty_portfolio(self, db_session):
        result = await recommend_campaigns(db_session, owner_id=uuid.uuid4())
        assert result == []

    async def test_diagnostic_gap_recommendation(self, db_session, admin_user):
        """Pre-1991 buildings without diagnostic should trigger a diagnostic campaign."""
        b1 = await _create_building(db_session, admin_user, construction_year=1975)
        b2 = await _create_building(db_session, admin_user, construction_year=1965)
        # b3 is post-1991, should not be included in gap
        await _create_building(db_session, admin_user, construction_year=2005)

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        diag_recs = [r for r in result if r["rationale"] == "regulatory_gap"]
        assert len(diag_recs) == 1
        rec = diag_recs[0]
        assert rec["campaign_type"] == "diagnostic"
        assert str(b1.id) in rec["building_ids"]
        assert str(b2.id) in rec["building_ids"]

    async def test_no_diagnostic_gap_when_diagnosed(self, db_session, admin_user):
        """Pre-1991 buildings with completed diagnostics should not be flagged."""
        b = await _create_building(db_session, admin_user, construction_year=1975)
        await _create_diagnostic(db_session, b.id, status="completed")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        diag_recs = [r for r in result if r["rationale"] == "regulatory_gap"]
        assert len(diag_recs) == 0

    async def test_risk_cluster_recommendation(self, db_session, admin_user):
        """Buildings with critical risk should trigger a remediation campaign."""
        b = await _create_building(db_session, admin_user, construction_year=1970)
        await _create_risk_score(db_session, b.id, level="critical")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        risk_recs = [r for r in result if r["rationale"] == "risk_cluster"]
        assert len(risk_recs) == 1
        assert risk_recs[0]["priority"] == "critical"

    async def test_no_risk_cluster_for_low_risk(self, db_session, admin_user):
        """Low-risk buildings should not trigger risk cluster campaigns."""
        b = await _create_building(db_session, admin_user, construction_year=2010)
        await _create_risk_score(db_session, b.id, level="low")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        risk_recs = [r for r in result if r["rationale"] == "risk_cluster"]
        assert len(risk_recs) == 0

    async def test_action_backlog_recommendation(self, db_session, admin_user):
        """Multiple open critical actions should trigger a remediation campaign."""
        b = await _create_building(db_session, admin_user, construction_year=1970)
        await _create_action(db_session, b.id, priority="critical", status="open")
        await _create_action(db_session, b.id, priority="high", status="open")
        await _create_action(db_session, b.id, priority="critical", status="open")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        action_recs = [r for r in result if r["rationale"] == "action_backlog"]
        assert len(action_recs) == 1

    async def test_no_action_backlog_for_closed(self, db_session, admin_user):
        """Closed actions should not trigger backlog campaigns."""
        b = await _create_building(db_session, admin_user, construction_year=1970)
        await _create_action(db_session, b.id, priority="critical", status="completed")
        await _create_action(db_session, b.id, priority="high", status="completed")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        action_recs = [r for r in result if r["rationale"] == "action_backlog"]
        assert len(action_recs) == 0

    async def test_pollutant_prevalence_recommendation(self, db_session, admin_user):
        """High positive rate for a pollutant should trigger a targeted campaign."""
        b = await _create_building(db_session, admin_user, construction_year=1970)
        d = await _create_diagnostic(db_session, b.id)
        # 3 positive, 1 negative -> 75% rate
        await _create_sample(db_session, d.id, pollutant="asbestos", exceeded=True)
        await _create_sample(db_session, d.id, pollutant="asbestos", exceeded=True)
        await _create_sample(db_session, d.id, pollutant="asbestos", exceeded=True)
        await _create_sample(db_session, d.id, pollutant="asbestos", exceeded=False)

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        poll_recs = [r for r in result if r["rationale"] == "pollutant_prevalence"]
        assert len(poll_recs) >= 1
        asbestos_rec = [r for r in poll_recs if r.get("pollutant_type") == "asbestos"]
        assert len(asbestos_rec) == 1

    async def test_recommendations_sorted_by_impact(self, db_session, admin_user):
        """Recommendations should be sorted by impact_score descending."""
        b = await _create_building(db_session, admin_user, construction_year=1970)
        await _create_risk_score(db_session, b.id, level="critical")
        await _create_action(db_session, b.id, priority="critical", status="open")
        await _create_action(db_session, b.id, priority="critical", status="open")
        await _create_action(db_session, b.id, priority="critical", status="open")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id)
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]["impact_score"] >= result[i + 1]["impact_score"]

    async def test_limit_respected(self, db_session, admin_user):
        """Limit parameter should cap the number of recommendations."""
        b = await _create_building(db_session, admin_user, construction_year=1970)
        await _create_risk_score(db_session, b.id, level="critical")

        result = await recommend_campaigns(db_session, owner_id=admin_user.id, limit=1)
        assert len(result) <= 1
