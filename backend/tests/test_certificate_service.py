"""Tests for the BatiConnect Certificate Service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.building_certificate import BuildingCertificate
from app.services.certificate_service import (
    _compute_integrity_hash,
    _generate_sequential_number,
    generate_certificate,
    list_certificates,
    verify_certificate,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_certificate_returns_correct_fields(db_session, admin_user):
    """Certificate should contain all required fields."""
    building = await _create_building(db_session, admin_user)
    result = await generate_certificate(db_session, building.id, admin_user.id)

    assert result is not None
    assert "certificate_id" in result
    assert "certificate_number" in result
    assert result["certificate_number"].startswith("BC-")
    assert "issued_at" in result
    assert "valid_until" in result
    assert "building" in result
    assert result["building"]["address"] == "Rue Test 1"
    assert "evidence_score" in result
    assert "passport_grade" in result
    assert "completeness" in result
    assert "trust_score" in result
    assert "key_findings" in result
    assert "document_coverage" in result
    assert "certification_chain" in result
    assert "verification_url" in result
    assert "verification_qr_data" in result
    assert result["issuer"] == "BatiConnect by Batiscan Sarl"
    assert "disclaimer" in result
    assert "integrity_hash" in result


@pytest.mark.asyncio
async def test_generate_certificate_none_for_missing_building(db_session, admin_user):
    """Certificate generation should return None for non-existent building."""
    fake_id = uuid.uuid4()
    result = await generate_certificate(db_session, fake_id, admin_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_certificate_number_is_sequential(db_session, admin_user):
    """Sequential certificates should have incrementing numbers."""
    building = await _create_building(db_session, admin_user)

    result1 = await generate_certificate(db_session, building.id, admin_user.id)
    result2 = await generate_certificate(db_session, building.id, admin_user.id)

    assert result1 is not None
    assert result2 is not None
    num1 = int(result1["certificate_number"].split("-")[-1])
    num2 = int(result2["certificate_number"].split("-")[-1])
    assert num2 == num1 + 1


@pytest.mark.asyncio
async def test_integrity_hash_is_correct(db_session, admin_user):
    """The integrity hash should match recomputation of the content."""
    building = await _create_building(db_session, admin_user)
    result = await generate_certificate(db_session, building.id, admin_user.id)

    assert result is not None
    stored_hash = result["integrity_hash"]

    # Recompute: remove integrity_hash and hash the rest
    content_copy = dict(result)
    del content_copy["integrity_hash"]
    expected_hash = _compute_integrity_hash(content_copy)
    assert stored_hash == expected_hash


@pytest.mark.asyncio
async def test_verify_returns_valid_for_fresh_certificate(db_session, admin_user):
    """Verification should return valid for a freshly generated certificate."""
    building = await _create_building(db_session, admin_user)
    result = await generate_certificate(db_session, building.id, admin_user.id)

    assert result is not None
    cert_id = uuid.UUID(result["certificate_id"])
    verification = await verify_certificate(db_session, cert_id)

    assert verification["valid"] is True
    assert "valid" in verification["reason"].lower()


@pytest.mark.asyncio
async def test_verify_returns_invalid_for_expired_certificate(db_session, admin_user):
    """Verification should detect an expired certificate."""
    building = await _create_building(db_session, admin_user)
    result = await generate_certificate(db_session, building.id, admin_user.id)

    assert result is not None
    cert_id = uuid.UUID(result["certificate_id"])

    # Manually expire the certificate in DB
    from sqlalchemy import select

    db_result = await db_session.execute(select(BuildingCertificate).where(BuildingCertificate.id == cert_id))
    cert = db_result.scalar_one()
    cert.valid_until = datetime.now(UTC) - timedelta(days=1)
    await db_session.flush()

    verification = await verify_certificate(db_session, cert_id)
    assert verification["valid"] is False
    assert "expired" in verification["reason"].lower()


@pytest.mark.asyncio
async def test_verify_returns_not_found_for_unknown_id(db_session):
    """Verification should return not found for unknown certificate ID."""
    fake_id = uuid.uuid4()
    verification = await verify_certificate(db_session, fake_id)
    assert verification["valid"] is False
    assert "not found" in verification["reason"].lower()


@pytest.mark.asyncio
async def test_certificate_chain_references_previous(db_session, admin_user):
    """Second certificate should reference first certificate's hash."""
    building = await _create_building(db_session, admin_user)

    result1 = await generate_certificate(db_session, building.id, admin_user.id)
    result2 = await generate_certificate(db_session, building.id, admin_user.id)

    assert result1 is not None
    assert result2 is not None

    chain2 = result2["certification_chain"]
    assert chain2["previous_certificate_hash"] == result1["integrity_hash"]


@pytest.mark.asyncio
async def test_list_by_building(db_session, admin_user):
    """List should return only certificates for the specified building."""
    b1 = await _create_building(db_session, admin_user)
    b2 = await _create_building(db_session, admin_user)

    await generate_certificate(db_session, b1.id, admin_user.id)
    await generate_certificate(db_session, b1.id, admin_user.id)
    await generate_certificate(db_session, b2.id, admin_user.id)

    items, total = await list_certificates(db_session, building_id=b1.id)
    assert total == 2
    assert len(items) == 2
    assert all(item["building_id"] == str(b1.id) for item in items)


@pytest.mark.asyncio
async def test_different_certificate_types(db_session, admin_user):
    """Different certificate types should be stored correctly."""
    building = await _create_building(db_session, admin_user)

    for cert_type in ("standard", "authority", "transaction"):
        result = await generate_certificate(db_session, building.id, admin_user.id, cert_type)
        assert result is not None
        assert result["certificate_type"] == cert_type


@pytest.mark.asyncio
async def test_sequential_number_format(db_session, admin_user):
    """Certificate number should match BC-YYYY-NNNNN format."""
    number = await _generate_sequential_number(db_session)
    year = datetime.now(UTC).year
    assert number == f"BC-{year}-00001"


@pytest.mark.asyncio
async def test_compute_integrity_hash_deterministic():
    """Same content should always produce the same hash."""
    content = {"a": 1, "b": "test", "c": [1, 2, 3]}
    hash1 = _compute_integrity_hash(content)
    hash2 = _compute_integrity_hash(content)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex
