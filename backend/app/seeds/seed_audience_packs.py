"""Finance Surfaces — Audience Pack seed data.

Run: python -m app.seeds.seed_audience_packs

Idempotent: uses upsert pattern on unique profile_code.
Creates 4 redaction profiles, 6 caveat profiles, and 2 demo audience packs.
"""

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.audience_pack import AudiencePack
from app.models.building import Building
from app.models.redaction_profile import DecisionCaveatProfile, ExternalAudienceRedactionProfile


async def seed():
    async with AsyncSessionLocal() as db:
        # ---- 1. Redaction Profiles (idempotent on profile_code) ----
        redaction_profiles = [
            {
                "profile_code": "redact-insurer",
                "audience_type": "insurer",
                "allowed_sections": [
                    "building_identity",
                    "diagnostics_summary",
                    "obligations",
                    "documents",
                ],
                "blocked_sections": ["financial", "internal_notes", "draft_procedures"],
                "redacted_fields": [
                    {"section": "building_identity", "field": "cadastral_ref", "reason": "not relevant for insurer"},
                ],
            },
            {
                "profile_code": "redact-fiduciary",
                "audience_type": "fiduciary",
                "allowed_sections": [
                    "building_identity",
                    "diagnostics_summary",
                    "obligations",
                    "documents",
                    "financial",
                ],
                "blocked_sections": ["internal_notes", "draft_procedures"],
                "redacted_fields": [],
            },
            {
                "profile_code": "redact-transaction",
                "audience_type": "transaction",
                "allowed_sections": [
                    "building_identity",
                    "diagnostics_summary",
                    "obligations",
                    "documents",
                ],
                "blocked_sections": ["financial", "internal_notes", "draft_procedures"],
                "redacted_fields": [
                    {"section": "building_identity", "field": "owner_details", "reason": "privacy"},
                ],
            },
            {
                "profile_code": "redact-lender",
                "audience_type": "lender",
                "allowed_sections": [
                    "building_identity",
                    "diagnostics_summary",
                    "obligations",
                    "documents",
                ],
                "blocked_sections": ["internal_notes", "draft_procedures"],
                "redacted_fields": [],
            },
        ]

        for rp_data in redaction_profiles:
            existing = (
                await db.execute(
                    select(ExternalAudienceRedactionProfile).where(
                        ExternalAudienceRedactionProfile.profile_code == rp_data["profile_code"]
                    )
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(ExternalAudienceRedactionProfile(id=uuid.uuid4(), **rp_data))

        await db.flush()

        # ---- 2. Decision Caveat Profiles (idempotent on audience_type + caveat_type) ----
        caveat_profiles = [
            {
                "audience_type": "insurer",
                "caveat_type": "freshness_warning",
                "template_text": "Diagnostic data may be older than 24 months -- independent review recommended before coverage decision.",
                "severity": "warning",
                "applies_when": {"freshness_state": "stale"},
            },
            {
                "audience_type": "insurer",
                "caveat_type": "confidence_caveat",
                "template_text": "Some data points are self-declared and have not been independently verified.",
                "severity": "info",
                "applies_when": {"confidence_level": "declared"},
            },
            {
                "audience_type": "transaction",
                "caveat_type": "unknown_disclosure",
                "template_text": "This building has unresolved unknown issues that may affect transaction readiness.",
                "severity": "warning",
                "applies_when": {"has_unknowns": True},
            },
            {
                "audience_type": "lender",
                "caveat_type": "contradiction_notice",
                "template_text": "Contradictory data detected in building records -- manual verification advised.",
                "severity": "critical",
                "applies_when": {"has_contradictions": True},
            },
            {
                "audience_type": "fiduciary",
                "caveat_type": "residual_risk_notice",
                "template_text": "Residual pollutant risks remain after remediation -- ongoing monitoring required.",
                "severity": "warning",
                "applies_when": {"has_unknowns": True},
            },
            {
                "audience_type": "transaction",
                "caveat_type": "regulatory_caveat",
                "template_text": "Building is subject to cantonal environmental regulations requiring disclosure at transfer.",
                "severity": "info",
                "applies_when": {},
            },
        ]

        for cp_data in caveat_profiles:
            existing = (
                await db.execute(
                    select(DecisionCaveatProfile).where(
                        DecisionCaveatProfile.audience_type == cp_data["audience_type"],
                        DecisionCaveatProfile.caveat_type == cp_data["caveat_type"],
                    )
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(DecisionCaveatProfile(id=uuid.uuid4(), **cp_data))

        await db.flush()

        # ---- 3. Demo Audience Packs (find first building, idempotent) ----
        first_building = (await db.execute(select(Building).limit(1))).scalar_one_or_none()
        if first_building:
            for pack_type, status in [("insurer", "ready"), ("transaction", "draft")]:
                existing = (
                    await db.execute(
                        select(AudiencePack).where(
                            AudiencePack.building_id == first_building.id,
                            AudiencePack.pack_type == pack_type,
                        )
                    )
                ).scalar_one_or_none()
                if not existing:
                    sections = {
                        "building_identity": {
                            "address": first_building.address,
                            "city": first_building.city,
                            "canton": first_building.canton,
                        }
                    }
                    content_hash = hashlib.sha256(json.dumps(sections, sort_keys=True).encode()).hexdigest()
                    db.add(
                        AudiencePack(
                            id=uuid.uuid4(),
                            building_id=first_building.id,
                            pack_type=pack_type,
                            pack_version=1,
                            status=status,
                            sections=sections,
                            unknowns_summary=[],
                            contradictions_summary=[],
                            residual_risk_summary=[],
                            trust_refs=[],
                            proof_refs=[],
                            content_hash=content_hash,
                            generated_at=datetime.now(UTC),
                        )
                    )

        await db.commit()
        print("Audience Packs seed complete:")
        print(f"  Redaction profiles: {len(redaction_profiles)}")
        print(f"  Caveat profiles: {len(caveat_profiles)}")
        print("  Demo packs: 2 (if building exists)")


if __name__ == "__main__":
    asyncio.run(seed())
