"""Tests for the Building Genealogy service and API."""

import uuid
from datetime import date

import pytest

from app.models.building_change import BuildingEvent
from app.models.building_genealogy import (
    HistoricalClaim,
)
from app.schemas.building_genealogy import (
    HistoricalClaimCreate,
    OwnershipEpisodeCreate,
    TransformationEpisodeCreate,
)
from app.services.genealogy_service import (
    add_historical_claim,
    add_ownership_episode,
    add_transformation,
    compare_declared_vs_observed,
    get_building_genealogy,
    get_genealogy_timeline,
)

# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_transformation_creates_episode(db_session, sample_building):
    """add_transformation persists a TransformationEpisode."""
    data = TransformationEpisodeCreate(
        episode_type="renovation",
        title="Rénovation toiture",
        description="Remplacement complet de la toiture",
        period_start=date(2020, 3, 1),
        period_end=date(2020, 6, 15),
        evidence_basis="documented",
    )
    episode = await add_transformation(db_session, sample_building.id, data)
    await db_session.commit()

    assert episode.id is not None
    assert episode.building_id == sample_building.id
    assert episode.episode_type == "renovation"
    assert episode.title == "Rénovation toiture"
    assert episode.period_start == date(2020, 3, 1)
    assert episode.evidence_basis == "documented"


@pytest.mark.asyncio
async def test_add_ownership_episode_creates_record(db_session, sample_building):
    """add_ownership_episode persists an OwnershipEpisode."""
    data = OwnershipEpisodeCreate(
        owner_name="Famille Dupont",
        owner_type="individual",
        period_start=date(1985, 1, 1),
        period_end=date(2010, 6, 30),
        acquisition_type="purchase",
        evidence_basis="registry",
    )
    episode = await add_ownership_episode(db_session, sample_building.id, data)
    await db_session.commit()

    assert episode.id is not None
    assert episode.owner_name == "Famille Dupont"
    assert episode.owner_type == "individual"
    assert episode.acquisition_type == "purchase"


@pytest.mark.asyncio
async def test_add_historical_claim_creates_record(db_session, sample_building):
    """add_historical_claim persists a HistoricalClaim."""
    data = HistoricalClaimCreate(
        claim_type="material_presence",
        subject="Amiante dans la toiture",
        assertion="Plaques fibro-ciment contenant de l'amiante posées en 1972",
        reference_date=date(1972, 1, 1),
        evidence_basis="document",
        confidence=0.8,
        source_description="Rapport diagnostic 2019",
    )
    claim = await add_historical_claim(db_session, sample_building.id, data)
    await db_session.commit()

    assert claim.id is not None
    assert claim.claim_type == "material_presence"
    assert claim.confidence == 0.8
    assert claim.status == "recorded"


@pytest.mark.asyncio
async def test_get_building_genealogy_returns_all_types(db_session, sample_building):
    """get_building_genealogy returns transformations, ownership, and claims."""
    # Add one of each
    t_data = TransformationEpisodeCreate(
        episode_type="construction",
        title="Construction initiale",
        period_start=date(1965, 1, 1),
        evidence_basis="documented",
    )
    await add_transformation(db_session, sample_building.id, t_data)

    o_data = OwnershipEpisodeCreate(
        owner_name="Régie Romande SA",
        owner_type="company",
        period_start=date(1965, 1, 1),
    )
    await add_ownership_episode(db_session, sample_building.id, o_data)

    c_data = HistoricalClaimCreate(
        claim_type="construction_date",
        subject="Date de construction",
        assertion="Construit en 1965",
        reference_date=date(1965, 1, 1),
        evidence_basis="registry",
        confidence=0.95,
    )
    await add_historical_claim(db_session, sample_building.id, c_data)
    await db_session.commit()

    result = await get_building_genealogy(db_session, sample_building.id)

    assert result.building_id == sample_building.id
    assert len(result.transformations) == 1
    assert len(result.ownership_episodes) == 1
    assert len(result.historical_claims) == 1
    assert result.transformations[0].episode_type == "construction"
    assert result.ownership_episodes[0].owner_name == "Régie Romande SA"
    assert result.historical_claims[0].claim_type == "construction_date"


@pytest.mark.asyncio
async def test_get_genealogy_timeline_merges_with_events(db_session, sample_building, admin_user):
    """Timeline includes both genealogy entries and BuildingEvents."""
    # Add a transformation
    t_data = TransformationEpisodeCreate(
        episode_type="renovation",
        title="Assainissement amiante",
        period_start=date(2021, 1, 1),
        evidence_basis="documented",
    )
    await add_transformation(db_session, sample_building.id, t_data)

    # Add a BuildingEvent
    event = BuildingEvent(
        building_id=sample_building.id,
        event_type="intervention_completed",
        title="Intervention terminée: retrait amiante",
        actor_id=admin_user.id,
        severity="significant",
    )
    db_session.add(event)
    await db_session.commit()

    timeline = await get_genealogy_timeline(db_session, sample_building.id)

    assert timeline.building_id == sample_building.id
    assert timeline.total_entries == 2
    entry_types = {e.entry_type for e in timeline.entries}
    assert "transformation" in entry_types
    assert "event" in entry_types


@pytest.mark.asyncio
async def test_get_genealogy_timeline_chronological_order(db_session, sample_building):
    """Timeline entries are sorted chronologically."""
    # Add entries in reverse order
    t2 = TransformationEpisodeCreate(
        episode_type="modernization",
        title="Modernisation 2020",
        period_start=date(2020, 1, 1),
        evidence_basis="documented",
    )
    t1 = TransformationEpisodeCreate(
        episode_type="construction",
        title="Construction 1965",
        period_start=date(1965, 1, 1),
        evidence_basis="documented",
    )
    await add_transformation(db_session, sample_building.id, t2)
    await add_transformation(db_session, sample_building.id, t1)
    await db_session.commit()

    timeline = await get_genealogy_timeline(db_session, sample_building.id)

    assert len(timeline.entries) == 2
    assert timeline.entries[0].title == "Construction 1965"
    assert timeline.entries[1].title == "Modernisation 2020"


@pytest.mark.asyncio
async def test_compare_declared_vs_observed_flags_unverified(db_session, sample_building):
    """Claims that are not verified show up as discrepancies."""
    c_data = HistoricalClaimCreate(
        claim_type="material_presence",
        subject="Plomb dans la peinture",
        assertion="Peinture au plomb dans les cages d'escalier",
        evidence_basis="testimony",
        confidence=0.3,
    )
    await add_historical_claim(db_session, sample_building.id, c_data)
    await db_session.commit()

    result = await compare_declared_vs_observed(db_session, sample_building.id)

    assert result.building_id == sample_building.id
    assert result.total_claims == 1
    assert result.unverified_count == 1
    assert len(result.discrepancies) == 1
    assert result.discrepancies[0].discrepancy_type == "unverified"


@pytest.mark.asyncio
async def test_compare_declared_vs_observed_verified_not_flagged(db_session, sample_building):
    """Verified claims are not flagged as discrepancies."""
    claim = HistoricalClaim(
        building_id=sample_building.id,
        claim_type="construction_date",
        subject="Date de construction",
        assertion="Construit en 1965",
        evidence_basis="registry",
        confidence=1.0,
        status="verified",
    )
    db_session.add(claim)
    await db_session.commit()

    result = await compare_declared_vs_observed(db_session, sample_building.id)

    assert result.total_claims == 1
    assert result.verified_count == 1
    assert result.unverified_count == 0
    assert len(result.discrepancies) == 0


@pytest.mark.asyncio
async def test_compare_declared_vs_observed_contested(db_session, sample_building):
    """Contested claims are flagged as contradictions."""
    claim = HistoricalClaim(
        building_id=sample_building.id,
        claim_type="material_presence",
        subject="PCB dans les joints",
        assertion="Présence de PCB confirmée en 2005",
        evidence_basis="document",
        confidence=0.6,
        status="contested",
    )
    db_session.add(claim)
    await db_session.commit()

    result = await compare_declared_vs_observed(db_session, sample_building.id)

    assert result.contested_count == 1
    assert len(result.discrepancies) == 1
    assert result.discrepancies[0].discrepancy_type == "contradiction"


@pytest.mark.asyncio
async def test_transformation_with_approximate_dates(db_session, sample_building):
    """Approximate dates are stored correctly."""
    data = TransformationEpisodeCreate(
        episode_type="restoration",
        title="Restauration probable années 80",
        period_start=date(1980, 1, 1),
        period_end=date(1985, 12, 31),
        approximate=True,
        evidence_basis="inferred",
    )
    episode = await add_transformation(db_session, sample_building.id, data)
    await db_session.commit()

    assert episode.approximate is True
    assert episode.evidence_basis == "inferred"


@pytest.mark.asyncio
async def test_ownership_episode_with_evidence_fields(db_session, sample_building):
    """Ownership episode stores evidence basis and acquisition type."""
    data = OwnershipEpisodeCreate(
        owner_name="Commune de Lausanne",
        owner_type="public",
        period_start=date(2010, 7, 1),
        acquisition_type="donation",
        evidence_basis="registry",
    )
    episode = await add_ownership_episode(db_session, sample_building.id, data)
    await db_session.commit()

    assert episode.owner_type == "public"
    assert episode.acquisition_type == "donation"
    assert episode.evidence_basis == "registry"


@pytest.mark.asyncio
async def test_empty_genealogy(db_session, sample_building):
    """Empty building returns empty genealogy without error."""
    result = await get_building_genealogy(db_session, sample_building.id)

    assert result.building_id == sample_building.id
    assert len(result.transformations) == 0
    assert len(result.ownership_episodes) == 0
    assert len(result.historical_claims) == 0


@pytest.mark.asyncio
async def test_empty_declared_vs_observed(db_session, sample_building):
    """No claims returns zeroed comparison."""
    result = await compare_declared_vs_observed(db_session, sample_building.id)

    assert result.total_claims == 0
    assert result.verified_count == 0
    assert result.contested_count == 0
    assert result.unverified_count == 0
    assert len(result.discrepancies) == 0


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_genealogy(client, sample_building, auth_headers):
    """GET /buildings/{id}/genealogy returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/genealogy",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "transformations" in data
    assert "ownership_episodes" in data
    assert "historical_claims" in data


@pytest.mark.asyncio
async def test_api_add_transformation(client, sample_building, auth_headers):
    """POST /buildings/{id}/genealogy/transformations creates a record."""
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/genealogy/transformations",
        headers=auth_headers,
        json={
            "episode_type": "renovation",
            "title": "Rénovation façade",
            "period_start": "2022-03-01",
            "evidence_basis": "documented",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["episode_type"] == "renovation"
    assert data["title"] == "Rénovation façade"


@pytest.mark.asyncio
async def test_api_add_ownership(client, sample_building, auth_headers):
    """POST /buildings/{id}/genealogy/ownership creates a record."""
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/genealogy/ownership",
        headers=auth_headers,
        json={
            "owner_name": "Dupont SA",
            "owner_type": "company",
            "period_start": "2000-01-01",
            "acquisition_type": "purchase",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["owner_name"] == "Dupont SA"


@pytest.mark.asyncio
async def test_api_add_historical_claim(client, sample_building, auth_headers):
    """POST /buildings/{id}/genealogy/historical-claims creates a record."""
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/genealogy/historical-claims",
        headers=auth_headers,
        json={
            "claim_type": "construction_date",
            "subject": "Date de construction",
            "assertion": "Construit en 1965",
            "reference_date": "1965-01-01",
            "evidence_basis": "registry",
            "confidence": 0.95,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["claim_type"] == "construction_date"
    assert data["confidence"] == 0.95


@pytest.mark.asyncio
async def test_api_get_timeline(client, sample_building, auth_headers):
    """GET /buildings/{id}/genealogy/timeline returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/genealogy/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "entries" in data
    assert "total_entries" in data


@pytest.mark.asyncio
async def test_api_declared_vs_observed(client, sample_building, auth_headers):
    """GET /buildings/{id}/genealogy/declared-vs-observed returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/genealogy/declared-vs-observed",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "total_claims" in data
    assert "discrepancies" in data


@pytest.mark.asyncio
async def test_api_genealogy_404_for_missing_building(client, auth_headers):
    """Genealogy endpoints return 404 for non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/genealogy",
        headers=auth_headers,
    )
    assert resp.status_code == 404
