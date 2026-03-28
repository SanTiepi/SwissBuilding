"""Pack generation orchestrator.

Contains the main ``generate_pack`` and ``list_available_packs`` entry points
plus the transfer-pack delegation and auto-conformance helpers.
"""

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.evidence_pack import EvidencePack
from app.schemas.pack_builder import (
    AvailablePacksResponse,
    PackConformanceResult,
    PackResult,
    PackSection,
    PackTypeInfo,
)
from app.services.pack_builder.caveats import _build_pack_caveats
from app.services.pack_builder.pack_types import (
    PACK_BUILDER_VERSION,
    PACK_TO_PROFILE,
    PACK_TYPES,
)
from app.services.pack_builder.redaction import _redact_section
from app.services.pack_builder.section_builders import _build_section

logger = logging.getLogger(__name__)


async def _run_auto_conformance(
    db: AsyncSession,
    building_id: uuid.UUID,
    pack_type: str,
    pack_id: uuid.UUID,
    checked_by_id: uuid.UUID | None = None,
) -> PackConformanceResult | None:
    """Run conformance check for a pack type. Advisory only -- never blocks pack generation."""
    profile_name = PACK_TO_PROFILE.get(pack_type)
    if not profile_name:
        return None
    try:
        from app.services.conformance_service import run_conformance_check

        check = await run_conformance_check(
            db,
            building_id,
            profile_name,
            target_type="pack",
            target_id=pack_id,
            checked_by_id=checked_by_id,
        )
        return PackConformanceResult(
            profile=profile_name,
            result=check.result,
            score=check.score,
            failed_checks=check.checks_failed or [],
        )
    except Exception:
        logger.warning("Auto-conformance check failed for pack %s (profile=%s)", pack_id, profile_name)
        return None


async def generate_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    pack_type: str,
    org_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    redact_financials: bool = False,
) -> PackResult:
    """Generate an audience-specific pack from the canonical building data.

    Reuses passport_service, completeness_engine, readiness_reasoner.
    Each pack type includes different sections relevant to that audience.
    All packs share the same underlying truth -- only the view changes.
    """
    if pack_type not in PACK_TYPES:
        raise ValueError(f"Unknown pack type: {pack_type}")

    pack_config = PACK_TYPES[pack_type]

    # Handle transfer pack delegation
    if pack_type == "transfer":
        return await _generate_transfer_pack(db, building_id, created_by_id)

    # Fetch building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")

    section_types = pack_config["sections"]

    # Build sections
    sections: list[PackSection] = []
    warnings: list[str] = []

    for section_type in section_types:
        if section_type == "caveats":
            continue  # Built after all other sections

        section = await _build_section(db, building, section_type)
        if section:
            sections.append(section)
        else:
            warnings.append(f"Section non disponible: {section_type}")

    # Build caveats if applicable (includes first-class caveats from DB)
    if "caveats" in section_types:
        caveats_section = await _build_pack_caveats(sections, building, pack_type, db=db)
        sections.append(caveats_section)

    # Compute overall completeness (exclude caveats)
    scorable = [s for s in sections if s.section_type != "caveats"]
    overall_completeness = sum(s.completeness for s in scorable) / len(scorable) if scorable else 0.0

    # Count caveats
    caveats_section_data = next((s for s in sections if s.section_type == "caveats"), None)
    caveats_count = len(caveats_section_data.items) if caveats_section_data else 0

    # Apply financial redaction to the exported view if requested
    output_sections = sections
    if redact_financials:
        output_sections = [_redact_section(s) for s in sections]

    generated_at = datetime.now(UTC)
    pack_id = uuid.uuid4()

    # Build metadata and hash
    metadata = {
        "pack_type": pack_type,
        "pack_name": pack_config["name"],
        "overall_completeness": overall_completeness,
        "total_sections": len(sections),
        "warnings": warnings,
        "includes_trust": pack_config["includes_trust"],
        "includes_provenance": pack_config["includes_provenance"],
        "sections": [
            {
                "section_type": s.section_type,
                "section_name": s.section_name,
                "completeness": s.completeness,
                "item_count": len(s.items),
            }
            for s in sections
        ],
        "caveats_count": caveats_count,
        "pack_version": PACK_BUILDER_VERSION,
        "generated_by": str(created_by_id) if created_by_id else None,
        "generation_date": generated_at.isoformat(),
        "financials_redacted": redact_financials,
    }

    content_for_hash = json.dumps(metadata, sort_keys=True, default=str)
    content_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()
    metadata["sha256_hash"] = content_hash

    # Create EvidencePack record
    pack_record = EvidencePack(
        id=pack_id,
        building_id=building_id,
        pack_type=f"pack_builder_{pack_type}",
        title=f"{pack_config['name']} - {building.address}",
        status="complete",
        created_by=created_by_id,
        assembled_at=generated_at,
        required_sections_json=[
            {"section_type": s.section_type, "label": s.section_name, "required": True, "included": True}
            for s in sections
        ],
        notes=json.dumps(metadata),
    )
    db.add(pack_record)
    await db.commit()

    # Auto-conformance check (advisory -- does not block pack generation)
    conformance = await _run_auto_conformance(db, building_id, pack_type, pack_id, created_by_id)

    return PackResult(
        pack_id=pack_id,
        building_id=building_id,
        pack_type=pack_type,
        pack_name=pack_config["name"],
        sections=output_sections,
        total_sections=len(output_sections),
        overall_completeness=overall_completeness,
        includes_trust=pack_config["includes_trust"],
        includes_provenance=pack_config["includes_provenance"],
        generated_at=generated_at,
        warnings=warnings,
        caveats_count=caveats_count,
        pack_version=PACK_BUILDER_VERSION,
        sha256_hash=content_hash,
        financials_redacted=redact_financials,
        conformance=conformance,
    )


async def _generate_transfer_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    created_by_id: uuid.UUID | None,
) -> PackResult:
    """Delegate transfer pack to transfer_package_service and wrap result."""
    from app.services.transfer_package_service import generate_transfer_package

    transfer = await generate_transfer_package(db, building_id)
    if not transfer:
        raise ValueError("Building not found")

    generated_at = datetime.now(UTC)
    pack_id = uuid.uuid4()

    # Wrap transfer package sections into PackSection format
    sections: list[PackSection] = []
    transfer_dict = transfer.model_dump()
    for key, value in transfer_dict.items():
        if key in ("package_id", "building_id", "generated_at", "package_version", "sha256_hash"):
            continue
        if value and isinstance(value, (dict, list)):
            section_items = value if isinstance(value, list) else [value]
            sections.append(
                PackSection(
                    section_name=key.replace("_", " ").title(),
                    section_type=key,
                    items=[item if isinstance(item, dict) else {"value": item} for item in section_items],
                    completeness=1.0,
                )
            )

    overall_completeness = sum(s.completeness for s in sections) / len(sections) if sections else 0.0
    content_hash = transfer_dict.get("sha256_hash", "")

    # Auto-conformance check (advisory)
    conformance = await _run_auto_conformance(db, building_id, "transfer", pack_id, created_by_id)

    return PackResult(
        pack_id=pack_id,
        building_id=building_id,
        pack_type="transfer",
        pack_name="Pack Transmission",
        sections=sections,
        total_sections=len(sections),
        overall_completeness=overall_completeness,
        includes_trust=True,
        includes_provenance=True,
        generated_at=generated_at,
        warnings=[],
        caveats_count=0,
        pack_version=PACK_BUILDER_VERSION,
        sha256_hash=content_hash,
        conformance=conformance,
    )


async def list_available_packs(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> AvailablePacksResponse:
    """Return which pack types are available/ready for a building.

    Readiness is based on passport grade and completeness score.
    """
    # Check building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")

    # Get completeness score for readiness estimate
    completeness_score = 0.0
    try:
        from app.services.completeness_engine import evaluate_completeness

        comp_result = await evaluate_completeness(db, building_id)
        completeness_score = comp_result.overall_score
    except Exception:
        pass

    # Get passport grade
    passport_grade = "F"
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
    except Exception:
        pass

    grade_score = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2}.get(passport_grade, 0.1)
    base_readiness = (completeness_score + grade_score) / 2

    packs: list[PackTypeInfo] = []
    for pack_type, config in PACK_TYPES.items():
        # Adjust readiness per pack type
        readiness_score = base_readiness
        if pack_type == "authority":
            # Authority packs need higher completeness
            readiness_score = min(base_readiness, completeness_score)
        elif pack_type == "contractor":
            # Contractor packs are less demanding
            readiness_score = min(1.0, base_readiness + 0.2)
        elif pack_type == "transfer":
            # Transfer packs need good overall data
            readiness_score = base_readiness

        if readiness_score >= 0.7:
            readiness = "ready"
        elif readiness_score >= 0.4:
            readiness = "partial"
        else:
            readiness = "not_ready"

        section_count = len(config["sections"])
        if pack_type == "transfer":
            section_count = 11  # transfer package has 11 sections

        packs.append(
            PackTypeInfo(
                pack_type=pack_type,
                name=config["name"],
                section_count=section_count,
                includes_trust=config["includes_trust"],
                includes_provenance=config["includes_provenance"],
                readiness=readiness,
                readiness_score=round(readiness_score, 2),
            )
        )

    return AvailablePacksResponse(building_id=building_id, packs=packs)
