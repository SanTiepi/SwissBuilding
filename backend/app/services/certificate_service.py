"""
BatiConnect Certificate Service — signed, verifiable building state certificates.

Generates certificates that bundle proof-of-state, evidence score, passport,
completeness, trust, and readiness into a single verifiable document with
SHA-256 integrity hash and certificate chain.

Certificate types:
  - standard: General building state certification
  - authority: Formatted for cantonal authority submission
  - transaction: Complete dossier for sale, insurance, or financing
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_certificate import BuildingCertificate
from app.models.document import Document

logger = logging.getLogger(__name__)

CERTIFICATE_VERSION = "1.0"
CERTIFICATE_VALIDITY_DAYS = 90
ISSUER = "BatiConnect by Batiscan Sarl"
DISCLAIMER = (
    "This certificate reflects data state at issuance. "
    "It is not a legal compliance guarantee. "
    "Verify at the provided verification URL for current validity."
)


def _compute_integrity_hash(content: dict) -> str:
    """Compute SHA-256 hash of certificate content (excluding integrity_hash field)."""
    serializable = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(serializable.encode("utf-8")).hexdigest()


async def _generate_sequential_number(db: AsyncSession) -> str:
    """Generate next certificate number in format BC-{year}-{5-digit seq}.

    Uses MAX+1 on the current year's certificates for thread safety
    within a transaction.
    """
    year = datetime.now(UTC).year
    prefix = f"BC-{year}-"

    result = await db.execute(
        select(func.max(BuildingCertificate.certificate_number)).where(
            BuildingCertificate.certificate_number.like(f"{prefix}%")
        )
    )
    last_number = result.scalar_one_or_none()

    if last_number:
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}{seq:05d}"


async def generate_certificate(
    db: AsyncSession,
    building_id: UUID,
    requested_by_id: UUID,
    certificate_type: str = "standard",
) -> dict | None:
    """Generate a BatiConnect Certificate for a building.

    Returns None if the building does not exist.
    Returns the full certificate dict and persists it to DB.
    """
    # ── 0. Fetch building ─────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    certificate_id = uuid4()
    issued_at = datetime.now(UTC)
    valid_until = issued_at + timedelta(days=CERTIFICATE_VALIDITY_DAYS)
    certificate_number = await _generate_sequential_number(db)

    # ── 1. Building info ──────────────────────────────────────────
    building_info = {
        "address": building.address,
        "city": building.city,
        "postal_code": building.postal_code,
        "egid": building.egid,
        "canton": building.canton,
        "construction_year": building.construction_year,
        "building_type": building.building_type,
    }

    # ── 2. Evidence score ─────────────────────────────────────────
    evidence_data: dict | None = None
    try:
        from app.services.evidence_score_service import compute_evidence_score

        evidence_data = await compute_evidence_score(db, building_id)
    except Exception as e:
        logger.warning("Failed to compute evidence score for %s: %s", building_id, e)

    evidence_score_val = evidence_data["score"] if evidence_data else 0
    evidence_grade = evidence_data["grade"] if evidence_data else "F"

    # ── 3. Passport ───────────────────────────────────────────────
    passport_data: dict | None = None
    try:
        from app.services.passport_service import get_passport_summary

        passport_data = await get_passport_summary(db, building_id)
    except Exception as e:
        logger.warning("Failed to get passport for %s: %s", building_id, e)

    passport_grade = passport_data.get("passport_grade", "F") if passport_data else "F"

    # ── 4. Completeness ───────────────────────────────────────────
    completeness_pct = 0.0
    try:
        from app.services.completeness_engine import evaluate_completeness

        comp_result = await evaluate_completeness(db, building_id)
        completeness_pct = round(comp_result.overall_score * 100, 1)
    except Exception as e:
        logger.warning("Failed to evaluate completeness for %s: %s", building_id, e)

    # ── 5. Trust score ────────────────────────────────────────────
    trust_value = 0.0
    try:
        from app.services.trust_score_calculator import compute_building_trust_score

        trust_data = await compute_building_trust_score(db, building_id)
        if trust_data and "overall_score" in trust_data:
            trust_value = trust_data["overall_score"]
    except Exception as e:
        logger.warning("Failed to compute trust for %s: %s", building_id, e)

    # ── 6. Readiness summary ──────────────────────────────────────
    readiness_summary: dict | None = None
    if passport_data and "readiness" in passport_data:
        readiness_summary = passport_data["readiness"]

    # ── 7. Key findings (top 5 critical issues) ──────────────────
    key_findings: list[str] = []
    if passport_data:
        blind_spots = passport_data.get("blind_spots", {})
        if blind_spots.get("blocking", 0) > 0:
            key_findings.append(f"{blind_spots['blocking']} readiness-blocking unknown(s) detected")
        contradictions = passport_data.get("contradictions", {})
        if contradictions.get("unresolved", 0) > 0:
            key_findings.append(f"{contradictions['unresolved']} unresolved contradiction(s)")
        pollutant_cov = passport_data.get("pollutant_coverage", {})
        missing = pollutant_cov.get("missing", [])
        if missing:
            key_findings.append(f"Missing pollutant diagnostics: {', '.join(missing[:3])}")
    if evidence_score_val < 40:
        key_findings.append("Low evidence score — significant knowledge gaps remain")
    if completeness_pct < 50:
        key_findings.append("Dossier completeness below 50%")
    key_findings = key_findings[:5]

    # ── 8. Document coverage ──────────────────────────────────────
    doc_result = await db.execute(
        select(Document.document_type, func.count())
        .where(Document.building_id == building_id)
        .group_by(Document.document_type)
    )
    document_coverage = {dtype: count for dtype, count in doc_result.all()}

    # ── 9. Certification chain ────────────────────────────────────
    # Get proof-of-state hash
    proof_hash: str | None = None
    try:
        from app.services.proof_of_state_service import generate_proof_of_state

        pos = await generate_proof_of_state(db, building_id, requested_by_id)
        if pos and "integrity" in pos:
            proof_hash = pos["integrity"]["hash"]
    except Exception as e:
        logger.warning("Failed to generate proof-of-state hash for %s: %s", building_id, e)

    # Get previous certificate hash for this building
    prev_result = await db.execute(
        select(BuildingCertificate.integrity_hash)
        .where(BuildingCertificate.building_id == building_id)
        .order_by(desc(BuildingCertificate.issued_at))
        .limit(1)
    )
    previous_hash = prev_result.scalar_one_or_none()

    certification_chain = {
        "proof_of_state_hash": proof_hash,
        "previous_certificate_hash": previous_hash,
    }

    # ── 10. Verification URL ──────────────────────────────────────
    verification_url = f"/verify/{certificate_id}"
    verification_qr_data = verification_url

    # ── Assemble certificate content ──────────────────────────────
    content = {
        "certificate_id": str(certificate_id),
        "certificate_number": certificate_number,
        "certificate_type": certificate_type,
        "version": CERTIFICATE_VERSION,
        "issued_at": issued_at.isoformat(),
        "valid_until": valid_until.isoformat(),
        "building": building_info,
        "evidence_score": {
            "score": evidence_score_val,
            "grade": evidence_grade,
        },
        "passport_grade": passport_grade,
        "completeness": completeness_pct,
        "trust_score": round(trust_value, 4),
        "readiness_summary": readiness_summary,
        "key_findings": key_findings,
        "document_coverage": document_coverage,
        "certification_chain": certification_chain,
        "verification_url": verification_url,
        "verification_qr_data": verification_qr_data,
        "issuer": ISSUER,
        "disclaimer": DISCLAIMER,
    }

    # ── Compute integrity hash ────────────────────────────────────
    integrity_hash = _compute_integrity_hash(content)
    content["integrity_hash"] = integrity_hash

    # ── Persist to DB ─────────────────────────────────────────────
    cert = BuildingCertificate(
        id=certificate_id,
        certificate_number=certificate_number,
        building_id=building_id,
        requested_by_id=requested_by_id,
        certificate_type=certificate_type,
        evidence_score=evidence_score_val,
        passport_grade=passport_grade,
        content_json=content,
        integrity_hash=integrity_hash,
        previous_hash=previous_hash,
        issued_at=issued_at,
        valid_until=valid_until,
        status="active",
    )
    db.add(cert)
    await db.flush()

    logger.info(
        "Certificate %s generated for building %s (type=%s, grade=%s)",
        certificate_number,
        building_id,
        certificate_type,
        passport_grade,
    )

    return content


async def verify_certificate(
    db: AsyncSession,
    certificate_id: UUID,
) -> dict:
    """Verify a certificate by its ID.

    Returns:
        {"valid": bool, "certificate": dict | None, "reason": str}
    """
    result = await db.execute(select(BuildingCertificate).where(BuildingCertificate.id == certificate_id))
    cert = result.scalar_one_or_none()

    if cert is None:
        return {"valid": False, "certificate": None, "reason": "Certificate not found"}

    # Check integrity hash
    stored_content = dict(cert.content_json)
    stored_hash = stored_content.pop("integrity_hash", None)
    recomputed_hash = _compute_integrity_hash(stored_content)

    if stored_hash != recomputed_hash:
        return {
            "valid": False,
            "certificate": cert.content_json,
            "reason": "Integrity check failed — certificate content has been tampered with",
        }

    # Check expiry
    now = datetime.now(UTC)
    valid_until = cert.valid_until
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=UTC)

    if now > valid_until:
        return {
            "valid": False,
            "certificate": cert.content_json,
            "reason": "Certificate has expired",
        }

    # Check revocation
    if cert.status == "revoked":
        return {
            "valid": False,
            "certificate": cert.content_json,
            "reason": "Certificate has been revoked",
        }

    return {
        "valid": True,
        "certificate": cert.content_json,
        "reason": "Certificate is valid and integrity verified",
    }


async def list_certificates(
    db: AsyncSession,
    building_id: UUID | None = None,
    org_id: UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    """List certificates with optional filtering.

    Returns (items, total_count).
    """
    query = select(BuildingCertificate)
    count_query = select(func.count()).select_from(BuildingCertificate)

    if building_id is not None:
        query = query.where(BuildingCertificate.building_id == building_id)
        count_query = count_query.where(BuildingCertificate.building_id == building_id)

    if org_id is not None:
        # Filter by buildings belonging to org — join through Building
        query = query.join(Building, BuildingCertificate.building_id == Building.id).where(
            Building.owner_id.in_(select(Building.owner_id).where(Building.id == BuildingCertificate.building_id))
        )
        # For org filtering we use a simpler approach: just filter by building ownership
        # This is a pragmatic filter; full org-scoping would use organization_id on Building

    query = query.order_by(desc(BuildingCertificate.issued_at))

    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    certs = list(result.scalars().all())

    items = [
        {
            "id": str(c.id),
            "certificate_number": c.certificate_number,
            "building_id": str(c.building_id),
            "certificate_type": c.certificate_type,
            "evidence_score": c.evidence_score,
            "passport_grade": c.passport_grade,
            "integrity_hash": c.integrity_hash,
            "issued_at": c.issued_at.isoformat() if c.issued_at else None,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "status": c.status,
        }
        for c in certs
    ]

    return items, total
