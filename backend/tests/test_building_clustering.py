"""Tests for building clustering service and API endpoints."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.building_clustering_service import (
    _era_for_year,
    _risk_signature,
    cluster_by_construction_era,
    cluster_by_risk_profile,
    find_outlier_buildings,
    get_cluster_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    organization = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email="cluster-test@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Cluster",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def buildings_1960s(db_session, org_user):
    """Two 1960s buildings with asbestos."""
    buildings = []
    for i in range(2):
        b = Building(
            id=uuid.uuid4(),
            address=f"Rue 1960s-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1960 + i,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()
    for b in buildings:
        await db_session.refresh(b)
    return buildings


@pytest.fixture
async def buildings_mixed_eras(db_session, org_user):
    """Buildings across all 4 eras."""
    specs = [
        ("Rue Old 1", 1940, "residential"),
        ("Rue Mid 1", 1960, "commercial"),
        ("Rue Late 1", 1980, "residential"),
        ("Rue New 1", 2000, "residential"),
    ]
    buildings = []
    for addr, year, btype in specs:
        b = Building(
            id=uuid.uuid4(),
            address=addr,
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=year,
            building_type=btype,
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()
    for b in buildings:
        await db_session.refresh(b)
    return buildings


@pytest.fixture
async def diagnostics_with_samples(db_session, buildings_1960s):
    """Create diagnostics and samples with threshold_exceeded for asbestos."""
    diags = []
    for b in buildings_1960s:
        d = Diagnostic(
            id=uuid.uuid4(),
            building_id=b.id,
            diagnostic_type="asbestos",
            status="completed",
        )
        db_session.add(d)
        diags.append(d)

        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number=f"S-{b.address}",
            location_detail="Kitchen ceiling",
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="high",
        )
        db_session.add(s)

    await db_session.commit()
    return diags


@pytest.fixture
async def risk_scores(db_session, buildings_1960s):
    """Risk scores for the 1960s buildings."""
    scores = []
    for b in buildings_1960s:
        rs = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=b.id,
            overall_risk_level="high",
            asbestos_probability=0.9,
        )
        db_session.add(rs)
        scores.append(rs)
    await db_session.commit()
    return scores


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestEraForYear:
    """Tests for _era_for_year helper."""

    def test_pre_1950(self):
        assert _era_for_year(1920) == "pre_1950"
        assert _era_for_year(1949) == "pre_1950"

    def test_1950_1975(self):
        assert _era_for_year(1950) == "1950_1975"
        assert _era_for_year(1965) == "1950_1975"
        assert _era_for_year(1974) == "1950_1975"

    def test_1975_1991(self):
        assert _era_for_year(1975) == "1975_1991"
        assert _era_for_year(1985) == "1975_1991"
        assert _era_for_year(1990) == "1975_1991"

    def test_post_1991(self):
        assert _era_for_year(1991) == "post_1991"
        assert _era_for_year(2020) == "post_1991"

    def test_none_returns_none(self):
        assert _era_for_year(None) is None


class TestRiskSignature:
    """Tests for _risk_signature helper."""

    def test_with_pollutants(self):
        sig = _risk_signature({"asbestos", "pcb"}, "high")
        assert sig == {"asbestos": "high", "pcb": "high"}

    def test_no_pollutants(self):
        sig = _risk_signature(set(), "low")
        assert sig == {"none": "low"}

    def test_no_pollutants_no_risk(self):
        sig = _risk_signature(set(), None)
        assert sig == {"none": "unknown"}


# ---------------------------------------------------------------------------
# FN1: cluster_by_risk_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_profile_empty_org(db_session, org):
    """Empty org returns zero clusters."""
    result = await cluster_by_risk_profile(db_session, org.id)
    assert result.total_buildings_analyzed == 0
    assert result.clusters == []


@pytest.mark.asyncio
async def test_risk_profile_with_matching_pollutants(
    db_session, org, buildings_1960s, diagnostics_with_samples, risk_scores
):
    """Buildings with same pollutant + risk level cluster together."""
    result = await cluster_by_risk_profile(db_session, org.id)
    assert result.total_buildings_analyzed == 2
    assert len(result.clusters) >= 1
    # Both buildings should be in the same cluster
    biggest = max(result.clusters, key=lambda c: c.cluster_size)
    assert biggest.cluster_size == 2
    assert biggest.dominant_risk == "asbestos"
    assert "asbestos" in biggest.risk_signature


@pytest.mark.asyncio
async def test_risk_profile_different_pollutants(db_session, org, org_user):
    """Buildings with different pollutants form different clusters."""
    b1 = Building(
        id=uuid.uuid4(),
        address="A",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    b2 = Building(
        id=uuid.uuid4(),
        address="B",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    # Different pollutants
    d1 = Diagnostic(id=uuid.uuid4(), building_id=b1.id, diagnostic_type="asbestos", status="completed")
    d2 = Diagnostic(id=uuid.uuid4(), building_id=b2.id, diagnostic_type="pcb", status="completed")
    db_session.add_all([d1, d2])
    await db_session.commit()

    s1 = Sample(
        id=uuid.uuid4(), diagnostic_id=d1.id, sample_number="S1", pollutant_type="asbestos", threshold_exceeded=True
    )
    s2 = Sample(id=uuid.uuid4(), diagnostic_id=d2.id, sample_number="S2", pollutant_type="pcb", threshold_exceeded=True)
    db_session.add_all([s1, s2])
    await db_session.commit()

    result = await cluster_by_risk_profile(db_session, org.id)
    assert result.total_buildings_analyzed == 2
    # Should have at least 2 clusters since pollutants differ
    assert len(result.clusters) >= 2


@pytest.mark.asyncio
async def test_risk_profile_no_pollutants(db_session, org, buildings_1960s):
    """Buildings without pollutants still cluster (by risk level 'unknown')."""
    result = await cluster_by_risk_profile(db_session, org.id)
    assert result.total_buildings_analyzed == 2
    assert len(result.clusters) >= 1


@pytest.mark.asyncio
async def test_risk_profile_cluster_sorted_by_size(db_session, org, org_user):
    """Clusters are sorted by size descending."""
    buildings = []
    for i in range(5):
        b = Building(
            id=uuid.uuid4(),
            address=f"Sort-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1960,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()

    result = await cluster_by_risk_profile(db_session, org.id)
    sizes = [c.cluster_size for c in result.clusters]
    assert sizes == sorted(sizes, reverse=True)


# ---------------------------------------------------------------------------
# FN2: cluster_by_construction_era
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_era_empty_org(db_session, org):
    """Empty org returns 4 era buckets with 0 buildings each."""
    result = await cluster_by_construction_era(db_session, org.id)
    assert result.total_buildings_analyzed == 0
    assert len(result.era_clusters) == 4


@pytest.mark.asyncio
async def test_era_buildings_sorted(db_session, org, buildings_mixed_eras):
    """Buildings are assigned to correct era buckets."""
    result = await cluster_by_construction_era(db_session, org.id)
    assert result.total_buildings_analyzed == 4
    era_map = {c.era_label: c for c in result.era_clusters}
    assert era_map["pre_1950"].building_count == 1
    assert era_map["1950_1975"].building_count == 1
    assert era_map["1975_1991"].building_count == 1
    assert era_map["post_1991"].building_count == 1


@pytest.mark.asyncio
async def test_era_recommended_actions_present(db_session, org, buildings_mixed_eras):
    """Each era bucket has recommended actions."""
    result = await cluster_by_construction_era(db_session, org.id)
    for cluster in result.era_clusters:
        assert len(cluster.recommended_actions) > 0


@pytest.mark.asyncio
async def test_era_pollutant_risks(db_session, org, buildings_1960s, diagnostics_with_samples):
    """Era cluster lists common pollutant risks."""
    result = await cluster_by_construction_era(db_session, org.id)
    era_map = {c.era_label: c for c in result.era_clusters}
    cluster_1950 = era_map["1950_1975"]
    assert cluster_1950.building_count == 2
    assert "asbestos" in cluster_1950.common_pollutant_risks


@pytest.mark.asyncio
async def test_era_no_construction_year(db_session, org, org_user):
    """Buildings with no construction year are excluded from era clusters."""
    b = Building(
        id=uuid.uuid4(),
        address="No Year",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=None,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    result = await cluster_by_construction_era(db_session, org.id)
    assert result.total_buildings_analyzed == 1
    total_in_eras = sum(c.building_count for c in result.era_clusters)
    assert total_in_eras == 0


# ---------------------------------------------------------------------------
# FN3: find_outlier_buildings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outliers_empty_org(db_session, org):
    """Empty org returns no outliers."""
    result = await find_outlier_buildings(db_session, org.id)
    assert result.total_buildings_analyzed == 0
    assert result.outliers == []


@pytest.mark.asyncio
async def test_outlier_risk_higher_than_peers(db_session, org, org_user):
    """Building with higher risk than peers is flagged."""
    buildings = []
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Peer-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1965,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()

    # Give 2 buildings low risk, 1 critical
    for i, level in enumerate(["low", "low", "critical"]):
        rs = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=buildings[i].id,
            overall_risk_level=level,
        )
        db_session.add(rs)
    await db_session.commit()

    result = await find_outlier_buildings(db_session, org.id)
    risk_outliers = [o for o in result.outliers if o.deviation_type == "risk_higher_than_peers"]
    assert len(risk_outliers) >= 1
    assert risk_outliers[0].outlier_id == buildings[2].id


@pytest.mark.asyncio
async def test_outlier_unusual_pollutant_mix(db_session, org, org_user):
    """Building with unusual pollutants vs era peers is flagged."""
    buildings = []
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Poll-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1965,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()

    # 2 buildings have asbestos (common), 1 has radon (unusual for era)
    for i, pollutant in enumerate(["asbestos", "asbestos", "radon"]):
        d = Diagnostic(
            id=uuid.uuid4(),
            building_id=buildings[i].id,
            diagnostic_type=pollutant,
            status="completed",
        )
        db_session.add(d)
        await db_session.commit()
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number=f"S-{i}",
            pollutant_type=pollutant,
            threshold_exceeded=True,
        )
        db_session.add(s)
    await db_session.commit()

    result = await find_outlier_buildings(db_session, org.id)
    unusual = [o for o in result.outliers if o.deviation_type == "unusual_pollutant_mix"]
    assert len(unusual) >= 1


@pytest.mark.asyncio
async def test_outlier_missing_diagnostics(db_session, org, org_user):
    """Building with fewer diagnostics than peers is flagged."""
    buildings = []
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Diag-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1965,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()

    # Give 2 buildings multiple diagnostics, 1 gets none
    for b in buildings[:2]:
        for _j in range(3):
            d = Diagnostic(
                id=uuid.uuid4(),
                building_id=b.id,
                diagnostic_type="asbestos",
                status="completed",
            )
            db_session.add(d)
    await db_session.commit()

    result = await find_outlier_buildings(db_session, org.id)
    missing = [o for o in result.outliers if o.deviation_type == "missing_diagnostics_vs_peers"]
    assert len(missing) >= 1
    assert missing[0].outlier_id == buildings[2].id


@pytest.mark.asyncio
async def test_outlier_severity_sorted(db_session, org, org_user):
    """Outliers are sorted by severity descending."""
    buildings = []
    for i in range(4):
        b = Building(
            id=uuid.uuid4(),
            address=f"Sev-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1965,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()

    for i, level in enumerate(["low", "low", "high", "critical"]):
        rs = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=buildings[i].id,
            overall_risk_level=level,
        )
        db_session.add(rs)
    await db_session.commit()

    result = await find_outlier_buildings(db_session, org.id)
    if len(result.outliers) >= 2:
        severities = [o.severity for o in result.outliers]
        assert severities == sorted(severities, reverse=True)


# ---------------------------------------------------------------------------
# FN4: get_cluster_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_empty_org(db_session, org):
    """Empty org returns zero summary."""
    result = await get_cluster_summary(db_session, org.id)
    assert result.total_buildings == 0
    assert result.total_clusters == 0
    assert result.diversity_score == 0.0


@pytest.mark.asyncio
async def test_summary_single_building(db_session, org, org_user):
    """Single building = 1 cluster, diversity 0."""
    b = Building(
        id=uuid.uuid4(),
        address="Solo",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    result = await get_cluster_summary(db_session, org.id)
    assert result.total_buildings == 1
    assert result.total_clusters == 1
    assert result.largest_cluster_size == 1
    assert result.buildings_without_cluster == 1
    assert result.diversity_score == 0.0


@pytest.mark.asyncio
async def test_summary_multiple_buildings_same_profile(
    db_session, org, buildings_1960s, diagnostics_with_samples, risk_scores
):
    """Buildings with same profile = 1 cluster, diversity 0."""
    result = await get_cluster_summary(db_session, org.id)
    assert result.total_buildings == 2
    assert result.total_clusters == 1
    assert result.largest_cluster_size == 2
    assert result.buildings_without_cluster == 0


@pytest.mark.asyncio
async def test_summary_diverse_portfolio(db_session, org, org_user):
    """Different risk profiles increase diversity score."""
    buildings = []
    for i in range(4):
        b = Building(
            id=uuid.uuid4(),
            address=f"Div-{i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1960,
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()

    # Give each building a different pollutant
    pollutants = ["asbestos", "pcb", "lead", "hap"]
    for i, pollutant in enumerate(pollutants):
        d = Diagnostic(
            id=uuid.uuid4(),
            building_id=buildings[i].id,
            diagnostic_type=pollutant,
            status="completed",
        )
        db_session.add(d)
        await db_session.commit()
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=d.id,
            sample_number=f"D-{i}",
            pollutant_type=pollutant,
            threshold_exceeded=True,
        )
        db_session.add(s)
    await db_session.commit()

    result = await get_cluster_summary(db_session, org.id)
    assert result.total_buildings == 4
    assert result.total_clusters == 4
    assert result.diversity_score == 1.0  # Max entropy = all different


@pytest.mark.asyncio
async def test_summary_most_common_pattern(db_session, org, buildings_1960s, diagnostics_with_samples, risk_scores):
    """Most common risk pattern reflects the largest cluster."""
    result = await get_cluster_summary(db_session, org.id)
    assert "asbestos" in result.most_common_risk_pattern


@pytest.mark.asyncio
async def test_summary_org_id_matches(db_session, org, buildings_1960s):
    """Organization ID is correctly set in result."""
    result = await get_cluster_summary(db_session, org.id)
    assert result.organization_id == org.id


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_risk_profile(client, auth_headers, db_session, org):
    """GET risk-profile returns 200."""
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/building-clusters/risk-profile",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "clusters" in data
    assert data["total_buildings_analyzed"] == 0


@pytest.mark.asyncio
async def test_api_construction_era(client, auth_headers, db_session, org):
    """GET construction-era returns 200 with 4 era buckets."""
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/building-clusters/construction-era",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["era_clusters"]) == 4


@pytest.mark.asyncio
async def test_api_outliers(client, auth_headers, db_session, org):
    """GET outliers returns 200."""
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/building-clusters/outliers",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "outliers" in data


@pytest.mark.asyncio
async def test_api_summary(client, auth_headers, db_session, org):
    """GET summary returns 200."""
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/building-clusters/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] == 0
    assert data["diversity_score"] == 0.0
