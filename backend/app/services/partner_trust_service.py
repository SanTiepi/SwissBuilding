"""BatiConnect — Partner trust signal and evaluation service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partner_trust import PartnerTrustProfile, PartnerTrustSignal


async def record_signal(db: AsyncSession, data: dict) -> PartnerTrustSignal:
    signal = PartnerTrustSignal(**data)
    db.add(signal)
    await db.flush()
    await db.refresh(signal)
    return signal


async def evaluate_partner(db: AsyncSession, partner_org_id: UUID) -> PartnerTrustProfile:
    """Recompute trust profile from all signals for a partner."""
    signals = (
        (await db.execute(select(PartnerTrustSignal).where(PartnerTrustSignal.partner_org_id == partner_org_id)))
        .scalars()
        .all()
    )

    signal_count = len(signals)

    # Compute sub-scores from signal types
    delivery_signals = [s for s in signals if s.signal_type in ("delivery_success", "delivery_failure")]
    evidence_signals = [
        s for s in signals if s.signal_type in ("evidence_clean", "evidence_rework", "evidence_rejected")
    ]
    response_signals = [s for s in signals if s.signal_type in ("response_fast", "response_slow")]

    delivery_score = _compute_positive_ratio(delivery_signals, positive_types={"delivery_success"})
    evidence_score = _compute_positive_ratio(evidence_signals, positive_types={"evidence_clean"})
    responsiveness_score = _compute_positive_ratio(response_signals, positive_types={"response_fast"})

    # Overall trust level from average of available scores
    available_scores = [s for s in [delivery_score, evidence_score, responsiveness_score] if s is not None]
    if not available_scores:
        overall = "unknown"
    else:
        avg = sum(available_scores) / len(available_scores)
        if avg >= 0.8:
            overall = "strong"
        elif avg >= 0.6:
            overall = "adequate"
        elif avg >= 0.4:
            overall = "review"
        else:
            overall = "weak"

    # Upsert profile
    result = await db.execute(select(PartnerTrustProfile).where(PartnerTrustProfile.partner_org_id == partner_org_id))
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = PartnerTrustProfile(partner_org_id=partner_org_id)
        db.add(profile)

    profile.delivery_reliability_score = delivery_score
    profile.evidence_quality_score = evidence_score
    profile.responsiveness_score = responsiveness_score
    profile.overall_trust_level = overall
    profile.signal_count = signal_count
    profile.last_evaluated_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(profile)
    return profile


def _compute_positive_ratio(
    signals: list[PartnerTrustSignal],
    *,
    positive_types: set[str],
) -> float | None:
    if not signals:
        return None
    positive = sum(1 for s in signals if s.signal_type in positive_types)
    return positive / len(signals)


async def get_profile(db: AsyncSession, partner_org_id: UUID) -> PartnerTrustProfile | None:
    result = await db.execute(select(PartnerTrustProfile).where(PartnerTrustProfile.partner_org_id == partner_org_id))
    return result.scalar_one_or_none()


async def list_profiles(db: AsyncSession) -> list[PartnerTrustProfile]:
    result = await db.execute(select(PartnerTrustProfile).order_by(PartnerTrustProfile.overall_trust_level))
    return list(result.scalars().all())


async def get_signal_count(db: AsyncSession, partner_org_id: UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(PartnerTrustSignal).where(PartnerTrustSignal.partner_org_id == partner_org_id)
    )
    return result.scalar() or 0


async def get_routing_hint(db: AsyncSession, partner_org_id: UUID, workflow_type: str) -> dict:
    """Return routing recommendation for a partner in a given workflow context."""
    profile = await get_profile(db, partner_org_id)

    if profile is None:
        return {
            "partner_org_id": str(partner_org_id),
            "workflow_type": workflow_type,
            "recommendation": "review",
            "overall_trust_level": "unknown",
            "signal_count": 0,
        }

    level = profile.overall_trust_level
    if level == "strong":
        recommendation = "preferred"
    elif level in ("adequate", "unknown"):
        recommendation = "review"
    else:
        recommendation = "avoid"

    return {
        "partner_org_id": str(partner_org_id),
        "workflow_type": workflow_type,
        "recommendation": recommendation,
        "overall_trust_level": level,
        "signal_count": profile.signal_count,
    }
