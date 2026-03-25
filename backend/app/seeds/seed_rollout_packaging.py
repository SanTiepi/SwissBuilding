"""Seed data for Adoption Loops — rollout + packaging layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bounded_embed import BoundedEmbedToken, ExternalViewerProfile
from app.models.building import Building
from app.models.delegated_access import DelegatedAccessGrant, PrivilegedAccessEvent
from app.models.package_preset import PackagePreset
from app.models.user import User


async def seed_rollout_packaging(db: AsyncSession) -> dict:
    """Seed rollout + packaging data. Idempotent."""
    stats: dict[str, int] = {}

    # --- Package Presets ---
    presets = [
        {
            "preset_code": "wedge",
            "title": "Pollutant Diagnostic Starter",
            "description": "Minimal amiante-first view for diagnostic labs and property owners.",
            "audience_type": "owner",
            "included_sections": ["building_identity", "diagnostics", "obligations", "proof_history"],
            "excluded_sections": ["financial", "internal_notes", "draft_documents"],
            "unknown_sections": ["commune_overrides", "pending_reviews"],
        },
        {
            "preset_code": "operational",
            "title": "Property Management Operations",
            "description": "Full operational view for gérances: leases, contracts, obligations, procedures.",
            "audience_type": "manager",
            "included_sections": [
                "building_identity",
                "diagnostics",
                "obligations",
                "procedures",
                "proof_history",
                "leases",
                "contracts",
                "ownership",
            ],
            "excluded_sections": ["internal_notes", "draft_documents"],
            "unknown_sections": ["pending_reviews"],
        },
        {
            "preset_code": "portfolio",
            "title": "Portfolio Intelligence Pack",
            "description": "Cross-building view for fiduciaries and institutional owners.",
            "audience_type": "fiduciary",
            "included_sections": [
                "building_identity",
                "diagnostics",
                "obligations",
                "procedures",
                "proof_history",
                "leases",
                "contracts",
                "ownership",
                "financial",
            ],
            "excluded_sections": ["internal_notes"],
            "unknown_sections": ["commune_overrides", "pending_reviews"],
        },
    ]
    created_presets = 0
    for p in presets:
        exists = await db.execute(select(PackagePreset).where(PackagePreset.preset_code == p["preset_code"]))
        if not exists.scalar_one_or_none():
            db.add(PackagePreset(**p))
            created_presets += 1
    stats["package_presets"] = created_presets

    # --- External Viewer Profiles ---
    profiles = [
        {
            "name": "Authority Inspector",
            "viewer_type": "authority",
            "allowed_sections": ["building_identity", "diagnostics", "obligations", "proof_history"],
            "requires_acknowledgement": True,
            "notes": "For DIREN/SAN inspectors reviewing building compliance.",
        },
        {
            "name": "Insurance Assessor",
            "viewer_type": "insurer",
            "allowed_sections": ["building_identity", "diagnostics", "obligations"],
            "requires_acknowledgement": False,
            "notes": "For insurance company risk assessors.",
        },
    ]
    created_profiles = 0
    for prof in profiles:
        exists = await db.execute(select(ExternalViewerProfile).where(ExternalViewerProfile.name == prof["name"]))
        if not exists.scalar_one_or_none():
            db.add(ExternalViewerProfile(**prof))
            created_profiles += 1
    stats["viewer_profiles"] = created_profiles

    await db.flush()

    # --- Delegated Access Grant + Embed Token (need existing building + user) ---
    building_result = await db.execute(select(Building).limit(1))
    building = building_result.scalar_one_or_none()
    user_result = await db.execute(select(User).where(User.role == "admin").limit(1))
    admin_user = user_result.scalar_one_or_none()

    if building and admin_user:
        # Grant
        grant_exists = await db.execute(
            select(DelegatedAccessGrant).where(DelegatedAccessGrant.building_id == building.id).limit(1)
        )
        if not grant_exists.scalar_one_or_none():
            grant = DelegatedAccessGrant(
                building_id=building.id,
                granted_to_email="partner@example.ch",
                grant_type="viewer",
                scope={
                    "documents": True,
                    "diagnostics": True,
                    "procedures": False,
                    "financial": False,
                    "obligations": True,
                },
                granted_by_user_id=admin_user.id,
                notes="Demo delegated viewer access.",
            )
            db.add(grant)
            stats["grants"] = 1

            # Privileged access event
            db.add(
                PrivilegedAccessEvent(
                    user_id=admin_user.id,
                    building_id=building.id,
                    action_type="grant_created",
                    target_entity_type="delegated_access_grant",
                    details={"grant_type": "viewer", "granted_to": "partner@example.ch"},
                )
            )
            stats["privileged_events"] = 1
        else:
            stats["grants"] = 0
            stats["privileged_events"] = 0

        # Embed token
        token_exists = await db.execute(
            select(BoundedEmbedToken).where(BoundedEmbedToken.building_id == building.id).limit(1)
        )
        if not token_exists.scalar_one_or_none():
            profile_result = await db.execute(select(ExternalViewerProfile).limit(1))
            profile = profile_result.scalar_one_or_none()
            db.add(
                BoundedEmbedToken(
                    building_id=building.id,
                    token="demo-embed-token-abc123",
                    viewer_profile_id=profile.id if profile else None,
                    scope={"sections": ["building_identity", "diagnostics"], "max_views": 100},
                    created_by_user_id=admin_user.id,
                )
            )
            stats["embed_tokens"] = 1
        else:
            stats["embed_tokens"] = 0
    else:
        stats["grants"] = 0
        stats["privileged_events"] = 0
        stats["embed_tokens"] = 0

    await db.commit()
    return stats
