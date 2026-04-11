"""BatiConnect — Commitment & Caveat service + route tests."""

from datetime import date, timedelta

import pytest

from app.services.commitment_service import (
    auto_generate_caveats,
    check_expiring_commitments,
    create_caveat,
    create_commitment,
    get_building_caveats,
    get_building_commitments,
    get_caveats_for_pack,
    get_commitment_caveat_summary,
)

# ---------------------------------------------------------------------------
# Commitment CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_commitment(db_session, sample_building):
    data = {
        "commitment_type": "guarantee",
        "committed_by_type": "contractor",
        "committed_by_name": "SanaCore AG",
        "subject": "Garantie assainissement amiante 10 ans",
        "description": "Garantie decennale sur les travaux d'assainissement amiante.",
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=3650),
        "duration_months": 120,
    }
    commitment = await create_commitment(db_session, sample_building.id, data)
    assert commitment.id is not None
    assert commitment.commitment_type == "guarantee"
    assert commitment.status == "active"
    assert commitment.committed_by_name == "SanaCore AG"


@pytest.mark.asyncio
async def test_list_commitments_active(db_session, sample_building):
    for i in range(3):
        await create_commitment(
            db_session,
            sample_building.id,
            {
                "commitment_type": "warranty",
                "committed_by_type": "contractor",
                "committed_by_name": f"Firm {i}",
                "subject": f"Warranty {i}",
                "status": "active" if i < 2 else "expired",
            },
        )
    await db_session.flush()

    active = await get_building_commitments(db_session, sample_building.id, status="active")
    assert len(active) == 2

    all_commitments = await get_building_commitments(db_session, sample_building.id, status=None)
    assert len(all_commitments) == 3


@pytest.mark.asyncio
async def test_expiring_commitments(db_session, sample_building):
    # Create one expiring in 30 days, one in 200 days
    await create_commitment(
        db_session,
        sample_building.id,
        {
            "commitment_type": "guarantee",
            "committed_by_type": "contractor",
            "committed_by_name": "Firm A",
            "subject": "Expires soon",
            "end_date": date.today() + timedelta(days=30),
        },
    )
    await create_commitment(
        db_session,
        sample_building.id,
        {
            "commitment_type": "guarantee",
            "committed_by_type": "contractor",
            "committed_by_name": "Firm B",
            "subject": "Expires later",
            "end_date": date.today() + timedelta(days=200),
        },
    )
    await db_session.flush()

    expiring = await check_expiring_commitments(db_session, sample_building.id, horizon_days=90)
    assert len(expiring) == 1
    assert expiring[0]["days_until_expiry"] == 30


# ---------------------------------------------------------------------------
# Caveat CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_caveat(db_session, sample_building):
    data = {
        "caveat_type": "scope_limitation",
        "subject": "Toiture non inspectee",
        "description": "La toiture n'a pas ete inspectee lors du diagnostic.",
        "severity": "warning",
        "applies_to_pack_types": ["authority", "insurer"],
    }
    caveat = await create_caveat(db_session, sample_building.id, data)
    assert caveat.id is not None
    assert caveat.active is True
    assert caveat.severity == "warning"


@pytest.mark.asyncio
async def test_list_caveats_active_only(db_session, sample_building):
    await create_caveat(
        db_session,
        sample_building.id,
        {"caveat_type": "coverage_gap", "subject": "Active caveat", "active": True},
    )
    await create_caveat(
        db_session,
        sample_building.id,
        {"caveat_type": "coverage_gap", "subject": "Inactive caveat", "active": False},
    )
    await db_session.flush()

    active = await get_building_caveats(db_session, sample_building.id, active_only=True)
    assert len(active) == 1
    assert active[0].subject == "Active caveat"


@pytest.mark.asyncio
async def test_caveats_for_pack_filtering(db_session, sample_building):
    # Caveat for authority only
    await create_caveat(
        db_session,
        sample_building.id,
        {
            "caveat_type": "authority_condition",
            "subject": "Condition autorite",
            "applies_to_pack_types": ["authority"],
        },
    )
    # Caveat for insurer only
    await create_caveat(
        db_session,
        sample_building.id,
        {
            "caveat_type": "insurer_exclusion",
            "subject": "Exclusion assureur",
            "applies_to_pack_types": ["insurer"],
        },
    )
    # Caveat for all packs (null = all)
    await create_caveat(
        db_session,
        sample_building.id,
        {
            "caveat_type": "data_quality_warning",
            "subject": "Qualite donnees",
            "applies_to_pack_types": None,
        },
    )
    await db_session.flush()

    authority_caveats = await get_caveats_for_pack(db_session, sample_building.id, "authority")
    assert len(authority_caveats) == 2  # authority-specific + global

    insurer_caveats = await get_caveats_for_pack(db_session, sample_building.id, "insurer")
    assert len(insurer_caveats) == 2  # insurer-specific + global

    transfer_caveats = await get_caveats_for_pack(db_session, sample_building.id, "transfer")
    assert len(transfer_caveats) == 1  # global only


# ---------------------------------------------------------------------------
# Auto-generate caveats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_generate_caveats_from_unknowns(db_session, sample_building):
    """Auto-generate caveats from open unknown entries."""
    from app.models.unknowns_ledger import UnknownEntry

    unknown = UnknownEntry(
        building_id=sample_building.id,
        unknown_type="missing_diagnostic",
        subject="Diagnostic amiante manquant",
        description="Aucun diagnostic amiante pour le batiment.",
        severity="high",
        status="open",
        blocks_pack_types=["authority"],
    )
    db_session.add(unknown)
    await db_session.flush()

    generated = await auto_generate_caveats(db_session, sample_building.id)
    assert len(generated) >= 1
    subjects = [c.subject for c in generated]
    assert "Diagnostic amiante manquant" in subjects


@pytest.mark.asyncio
async def test_auto_generate_caveats_idempotent(db_session, sample_building):
    """Running auto-generate twice should not duplicate caveats."""
    from app.models.unknowns_ledger import UnknownEntry

    unknown = UnknownEntry(
        building_id=sample_building.id,
        unknown_type="missing_document",
        subject="Document manquant",
        severity="medium",
        status="open",
    )
    db_session.add(unknown)
    await db_session.flush()

    first = await auto_generate_caveats(db_session, sample_building.id)
    second = await auto_generate_caveats(db_session, sample_building.id)
    assert len(first) >= 1
    assert len(second) == 0  # idempotent: no new caveats


@pytest.mark.asyncio
async def test_auto_generate_caveats_from_contradictions(db_session, sample_building):
    """Auto-generate caveats from unresolved contradictions."""
    from app.models.data_quality_issue import DataQualityIssue

    issue = DataQualityIssue(
        building_id=sample_building.id,
        issue_type="contradiction",
        field_name="construction_year",
        description="Annee de construction contradictoire entre deux sources.",
        severity="high",
        status="open",
    )
    db_session.add(issue)
    await db_session.flush()

    generated = await auto_generate_caveats(db_session, sample_building.id)
    assert len(generated) >= 1
    types = [c.caveat_type for c in generated]
    assert "data_quality_warning" in types


@pytest.mark.asyncio
async def test_auto_generate_caveats_from_low_confidence_claims(db_session, sample_building, admin_user):
    """Auto-generate caveats from low-confidence claims."""
    import uuid

    from app.models.building_claim import BuildingClaim
    from app.models.organization import Organization

    org = Organization(id=uuid.uuid4(), name="TestOrg", type="property_management")
    db_session.add(org)
    await db_session.flush()

    claim = BuildingClaim(
        building_id=sample_building.id,
        organization_id=org.id,
        claimed_by_id=admin_user.id,
        claim_type="pollutant_presence",
        subject="Presence amiante sous-sol",
        assertion="Amiante probablement present dans le sous-sol.",
        basis_type="inference",
        confidence=0.3,
        status="asserted",
    )
    db_session.add(claim)
    await db_session.flush()

    generated = await auto_generate_caveats(db_session, sample_building.id)
    assert len(generated) >= 1
    types = [c.caveat_type for c in generated]
    assert "unverified_claim" in types


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_commitment_caveat_summary(db_session, sample_building):
    # Create commitments in various states
    await create_commitment(
        db_session,
        sample_building.id,
        {
            "commitment_type": "guarantee",
            "committed_by_type": "contractor",
            "committed_by_name": "A",
            "subject": "Active",
            "status": "active",
            "end_date": date.today() + timedelta(days=30),
        },
    )
    await create_commitment(
        db_session,
        sample_building.id,
        {
            "commitment_type": "warranty",
            "committed_by_type": "contractor",
            "committed_by_name": "B",
            "subject": "Expired",
            "status": "expired",
        },
    )
    # Create caveats
    await create_caveat(
        db_session,
        sample_building.id,
        {"caveat_type": "scope_limitation", "subject": "Caveat 1", "severity": "warning"},
    )
    await create_caveat(
        db_session,
        sample_building.id,
        {"caveat_type": "coverage_gap", "subject": "Caveat 2", "severity": "critical"},
    )
    await db_session.flush()

    summary = await get_commitment_caveat_summary(db_session, sample_building.id)
    assert summary["active_commitments"] == 1
    assert summary["expiring_soon"] == 1
    assert summary["expired_commitments"] == 1
    assert summary["active_caveats"] == 2
    assert summary["caveats_by_severity"]["warning"] == 1
    assert summary["caveats_by_severity"]["critical"] == 1
    assert summary["caveats_by_type"]["scope_limitation"] == 1
    assert summary["caveats_by_type"]["coverage_gap"] == 1
