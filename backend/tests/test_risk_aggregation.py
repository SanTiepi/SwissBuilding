"""Tests for the Risk Aggregation service, schemas, and API endpoints."""

import uuid

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.user import User
from app.models.zone import Zone
from app.services.risk_aggregation_service import (
    _score_to_grade,
    get_portfolio_risk_matrix,
    get_risk_correlation_map,
    get_risk_decomposition,
    get_unified_risk_score,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def building_with_data(db_session, admin_user):
    """Building with risk score, actions, zone+elements, interventions, docs, diagnostics."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Risque 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    # Risk score
    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building.id,
        asbestos_probability=0.85,
        pcb_probability=0.60,
        lead_probability=0.40,
        hap_probability=0.30,
        radon_probability=0.10,
        overall_risk_level="high",
        confidence=0.7,
        data_source="model",
    )
    db_session.add(risk)

    # Actions
    for status in ["open", "overdue", "completed"]:
        db_session.add(
            ActionItem(
                id=uuid.uuid4(),
                building_id=building.id,
                source_type="diagnostic",
                action_type="remediation",
                title=f"Action {status}",
                status=status,
                priority="high",
            )
        )

    # Zone + Elements
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name="Ground floor",
        created_by=admin_user.id,
    )
    db_session.add(zone)
    await db_session.flush()

    for condition in ["good", "degraded", "critical"]:
        db_session.add(
            BuildingElement(
                id=uuid.uuid4(),
                zone_id=zone.id,
                element_type="wall",
                name=f"Wall {condition}",
                condition=condition,
                created_by=admin_user.id,
            )
        )

    # Interventions
    db_session.add(
        Intervention(
            id=uuid.uuid4(),
            building_id=building.id,
            intervention_type="remediation",
            title="Asbestos removal",
            status="planned",
            created_by=admin_user.id,
        )
    )

    # Documents
    db_session.add(
        Document(
            id=uuid.uuid4(),
            building_id=building.id,
            file_name="report.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            file_path="/docs/report.pdf",
            uploaded_by=admin_user.id,
        )
    )

    # Diagnostic
    db_session.add(
        Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="avant_travaux",
            status="completed",
            diagnostician_id=admin_user.id,
        )
    )

    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def bare_building(db_session, admin_user):
    """Building with no associated data."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2000,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Unit tests: _score_to_grade
# ---------------------------------------------------------------------------


class TestScoreToGrade:
    def test_grade_a(self):
        assert _score_to_grade(95) == "A"

    def test_grade_b(self):
        assert _score_to_grade(80) == "B"

    def test_grade_c(self):
        assert _score_to_grade(65) == "C"

    def test_grade_d(self):
        assert _score_to_grade(45) == "D"

    def test_grade_e(self):
        assert _score_to_grade(25) == "E"

    def test_grade_f(self):
        assert _score_to_grade(10) == "F"


# ---------------------------------------------------------------------------
# FN1: get_unified_risk_score
# ---------------------------------------------------------------------------


class TestGetUnifiedRiskScore:
    async def test_returns_score_for_building_with_data(self, db_session, building_with_data):
        result = await get_unified_risk_score(db_session, building_with_data.id)
        assert 0 <= result.overall_score <= 100
        assert result.grade in ("A", "B", "C", "D", "E", "F")
        assert result.building_id == building_with_data.id
        assert "pollutant" in result.dimensions
        assert "compliance" in result.dimensions
        assert "structural" in result.dimensions
        assert "financial" in result.dimensions
        assert "operational" in result.dimensions

    async def test_returns_score_for_bare_building(self, db_session, bare_building):
        result = await get_unified_risk_score(db_session, bare_building.id)
        assert 0 <= result.overall_score <= 100
        assert result.grade in ("A", "B", "C", "D", "E", "F")

    async def test_raises_for_missing_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_unified_risk_score(db_session, uuid.uuid4())

    async def test_peer_comparison_defaults(self, db_session, bare_building):
        result = await get_unified_risk_score(db_session, bare_building.id)
        # With no peers, percentile defaults to 50
        assert result.percentile == 50.0


# ---------------------------------------------------------------------------
# FN2: get_risk_decomposition
# ---------------------------------------------------------------------------


class TestGetRiskDecomposition:
    async def test_decomposition_has_all_dimensions(self, db_session, building_with_data):
        result = await get_risk_decomposition(db_session, building_with_data.id)
        dim_names = {d.dimension for d in result.dimensions}
        assert dim_names == {"pollutant", "compliance", "structural", "financial", "operational"}

    async def test_waterfall_cumulative_matches_total(self, db_session, building_with_data):
        result = await get_risk_decomposition(db_session, building_with_data.id)
        assert len(result.waterfall) == 5
        last_cumulative = result.waterfall[-1].cumulative
        assert abs(last_cumulative - result.overall_score) < 0.5

    async def test_dimensions_have_contributors(self, db_session, building_with_data):
        result = await get_risk_decomposition(db_session, building_with_data.id)
        for dim in result.dimensions:
            assert len(dim.top_contributors) > 0
            assert dim.trend in ("improving", "stable", "worsening")
            assert len(dim.mitigation_options) > 0

    async def test_raises_for_missing_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_risk_decomposition(db_session, uuid.uuid4())

    async def test_waterfall_contributions_positive(self, db_session, building_with_data):
        result = await get_risk_decomposition(db_session, building_with_data.id)
        for segment in result.waterfall:
            assert segment.contribution >= 0


# ---------------------------------------------------------------------------
# FN3: get_risk_correlation_map
# ---------------------------------------------------------------------------


class TestGetRiskCorrelationMap:
    async def test_returns_correlations(self, db_session, building_with_data):
        result = await get_risk_correlation_map(db_session, building_with_data.id)
        assert len(result.correlations) > 0
        for corr in result.correlations:
            assert 0 <= corr.strength <= 1.0
            assert corr.direction in ("positive", "negative")
            assert corr.source != corr.target

    async def test_cascade_chains_present(self, db_session, building_with_data):
        result = await get_risk_correlation_map(db_session, building_with_data.id)
        assert len(result.cascade_chains) > 0
        for chain in result.cascade_chains:
            assert len(chain) >= 2

    async def test_pollutant_compliance_correlation_exists(self, db_session, building_with_data):
        result = await get_risk_correlation_map(db_session, building_with_data.id)
        pc = [c for c in result.correlations if c.source == "pollutant" and c.target == "compliance"]
        assert len(pc) == 1
        assert pc[0].strength > 0.3  # should be significant

    async def test_raises_for_missing_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_risk_correlation_map(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4: get_portfolio_risk_matrix
# ---------------------------------------------------------------------------


class TestGetPortfolioRiskMatrix:
    async def test_matrix_for_org_with_buildings(self, db_session, org, org_user):
        # Create a building owned by org member
        bld = Building(
            id=uuid.uuid4(),
            address="Rue Matrice 5",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1975,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(bld)
        await db_session.commit()

        result = await get_portfolio_risk_matrix(db_session, org.id)
        assert result.building_count == 1
        assert len(result.dimensions) == 5
        assert len(result.cells) == 5  # 1 building x 5 dimensions

    async def test_matrix_for_empty_org(self, db_session, org):
        result = await get_portfolio_risk_matrix(db_session, org.id)
        assert result.building_count == 0
        assert result.cells == []

    async def test_hotspot_identification(self, db_session, org, org_user):
        # Create multiple buildings with high risk scores to trigger hotspot
        for i in range(3):
            bld = Building(
                id=uuid.uuid4(),
                address=f"Rue Hot {i}",
                postal_code="1000",
                city="Lausanne",
                canton="VD",
                construction_year=1965,
                building_type="industrial",
                created_by=org_user.id,
                status="active",
            )
            db_session.add(bld)
            await db_session.flush()
            # High pollutant risk
            db_session.add(
                BuildingRiskScore(
                    id=uuid.uuid4(),
                    building_id=bld.id,
                    asbestos_probability=0.95,
                    pcb_probability=0.80,
                    lead_probability=0.70,
                    hap_probability=0.60,
                    radon_probability=0.50,
                    overall_risk_level="critical",
                    confidence=0.9,
                    data_source="diagnostic",
                )
            )

        await db_session.commit()

        result = await get_portfolio_risk_matrix(db_session, org.id)
        assert result.building_count == 3
        # Pollutant hotspot should be detected
        pollutant_hotspots = [h for h in result.hotspots if h.dimension == "pollutant"]
        assert len(pollutant_hotspots) == 1
        assert pollutant_hotspots[0].affected_building_count == 3


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestRiskAggregationAPI:
    async def test_get_risk_score_endpoint(self, client, auth_headers, building_with_data):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_data.id}/risk-score",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert "grade" in data
        assert "dimensions" in data

    async def test_get_risk_score_404(self, client, auth_headers):
        resp = await client.get(
            f"/api/v1/buildings/{uuid.uuid4()}/risk-score",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_risk_decomposition_endpoint(self, client, auth_headers, building_with_data):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_data.id}/risk-decomposition",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "waterfall" in data
        assert "dimensions" in data

    async def test_get_risk_correlations_endpoint(self, client, auth_headers, building_with_data):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_data.id}/risk-correlations",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "correlations" in data
        assert "cascade_chains" in data

    async def test_get_risk_matrix_endpoint(self, client, auth_headers, org):
        resp = await client.get(
            f"/api/v1/organizations/{org.id}/risk-matrix",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cells" in data
        assert "hotspots" in data
        assert "dimensions" in data

    async def test_unauthenticated_returns_401(self, client, building_with_data):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_data.id}/risk-score",
        )
        assert resp.status_code in (401, 403)
