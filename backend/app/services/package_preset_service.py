"""Adoption Loops — Package preset service: presets, embed tokens, viewer profiles."""

import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bounded_embed import BoundedEmbedToken, ExternalViewerProfile
from app.models.package_preset import PackagePreset

# --- Package Presets ---


async def list_presets(db: AsyncSession, *, active_only: bool = True) -> list[PackagePreset]:
    """List all package presets."""
    query = select(PackagePreset)
    if active_only:
        query = query.where(PackagePreset.is_active.is_(True))
    query = query.order_by(PackagePreset.preset_code)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_preset(db: AsyncSession, preset_code: str) -> PackagePreset | None:
    """Fetch a preset by code."""
    result = await db.execute(select(PackagePreset).where(PackagePreset.preset_code == preset_code))
    return result.scalar_one_or_none()


async def preview_package(db: AsyncSession, building_id: UUID, preset_code: str) -> dict | None:
    """Assemble a package preview for a building using the given preset."""
    preset = await get_preset(db, preset_code)
    if not preset:
        return None

    return {
        "preset_code": preset.preset_code,
        "building_id": str(building_id),
        "title": preset.title,
        "audience_type": preset.audience_type,
        "included": preset.included_sections or [],
        "excluded": preset.excluded_sections or [],
        "unknown": preset.unknown_sections or [],
    }


# --- Embed Tokens ---


async def create_embed_token(
    db: AsyncSession,
    building_id: UUID,
    created_by_user_id: UUID,
    *,
    viewer_profile_id: UUID | None = None,
    scope: dict | None = None,
) -> BoundedEmbedToken:
    """Create a bounded embed token for a building."""
    token_str = secrets.token_urlsafe(48)
    embed = BoundedEmbedToken(
        building_id=building_id,
        token=token_str,
        viewer_profile_id=viewer_profile_id,
        scope=scope,
        created_by_user_id=created_by_user_id,
    )
    db.add(embed)
    await db.flush()
    await db.refresh(embed)
    return embed


async def validate_embed_token(db: AsyncSession, token: str) -> BoundedEmbedToken | None:
    """Look up an active embed token."""
    result = await db.execute(
        select(BoundedEmbedToken).where(BoundedEmbedToken.token == token).where(BoundedEmbedToken.is_active.is_(True))
    )
    embed = result.scalar_one_or_none()
    if not embed:
        return None

    # Check max_views from scope
    scope = embed.scope or {}
    max_views = scope.get("max_views")
    if max_views is not None and embed.view_count >= max_views:
        return None

    # Check expiry from scope
    expires_at_str = scope.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(UTC) > expires_at.replace(tzinfo=UTC):
                return None
        except (ValueError, TypeError):
            pass

    return embed


async def record_embed_view(db: AsyncSession, embed: BoundedEmbedToken) -> None:
    """Increment view count and update last_viewed_at."""
    embed.view_count = (embed.view_count or 0) + 1
    embed.last_viewed_at = datetime.now(UTC)
    await db.flush()


async def get_viewer_profile(db: AsyncSession, profile_id: UUID) -> ExternalViewerProfile | None:
    """Fetch a viewer profile by ID."""
    result = await db.execute(select(ExternalViewerProfile).where(ExternalViewerProfile.id == profile_id))
    return result.scalar_one_or_none()


async def list_viewer_profiles(db: AsyncSession) -> list[ExternalViewerProfile]:
    """List all external viewer profiles."""
    result = await db.execute(select(ExternalViewerProfile).order_by(ExternalViewerProfile.name))
    return list(result.scalars().all())
