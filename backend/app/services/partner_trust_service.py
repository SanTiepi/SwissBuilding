"""BatiConnect — Partner trust signal and evaluation service.

V3 doctrine integration: trust signals are building-rooted via BuildingCase.
Signals are OBSERVATIONS, not rankings. No ranking influenced by payment (invariant #6).
Partner trust informs panel selection guidance, not automatic filtering.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_case import BuildingCase
from app.models.partner_trust import PartnerTrustProfile, PartnerTrustSignal
from app.models.rfq import TenderInvitation, TenderQuote


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


# ---------------------------------------------------------------------------
# V3 doctrine integration: BuildingCase + ritual linkage
# ---------------------------------------------------------------------------


async def record_signal_from_case(
    db: AsyncSession,
    partner_org_id: UUID,
    case_id: UUID,
    signal_type: str,
    value: float | None = None,
    notes: str | None = None,
) -> PartnerTrustSignal:
    """Record a trust signal from a BuildingCase interaction.

    Called when: tender response received, quote quality assessed,
    work completed, complement triggered by partner submission.
    """
    signal = PartnerTrustSignal(
        partner_org_id=partner_org_id,
        signal_type=signal_type,
        source_entity_type="building_case",
        source_entity_id=case_id,
        value=value,
        notes=notes,
    )
    db.add(signal)
    await db.flush()
    await db.refresh(signal)
    # Auto-evaluate after recording
    await evaluate_partner(db, partner_org_id)
    return signal


async def record_signal_from_ritual(
    db: AsyncSession,
    partner_org_id: UUID,
    ritual_id: UUID,
    signal_type: str,
) -> PartnerTrustSignal:
    """Record trust signal from a ritual event.

    Called when: partner acknowledges a transfer, delivers on time,
    evidence is clean vs needs rework.
    """
    signal = PartnerTrustSignal(
        partner_org_id=partner_org_id,
        signal_type=signal_type,
        source_entity_type="truth_ritual",
        source_entity_id=ritual_id,
    )
    db.add(signal)
    await db.flush()
    await db.refresh(signal)
    await evaluate_partner(db, partner_org_id)
    return signal


async def get_partner_trust_for_case(
    db: AsyncSession,
    case_id: UUID,
) -> list[dict]:
    """Get trust profiles for all partners involved in a case.

    Looks up the case's linked tender to find contractor org IDs,
    then returns their trust profiles.
    """
    # Find the case
    case_result = await db.execute(select(BuildingCase).where(BuildingCase.id == case_id))
    case = case_result.scalar_one_or_none()
    if case is None:
        return []

    partner_org_ids: set[UUID] = set()

    # If case has a linked tender, get all invited/quoting contractors
    if case.tender_id is not None:
        inv_result = await db.execute(
            select(TenderInvitation.contractor_org_id).where(TenderInvitation.tender_id == case.tender_id)
        )
        for row in inv_result.all():
            partner_org_ids.add(row[0])

        quote_result = await db.execute(
            select(TenderQuote.contractor_org_id).where(TenderQuote.tender_id == case.tender_id)
        )
        for row in quote_result.all():
            partner_org_ids.add(row[0])

    # Also find partners who have signals linked to this case
    signal_result = await db.execute(
        select(PartnerTrustSignal.partner_org_id).where(
            PartnerTrustSignal.source_entity_type == "building_case",
            PartnerTrustSignal.source_entity_id == case_id,
        )
    )
    for row in signal_result.all():
        partner_org_ids.add(row[0])

    if not partner_org_ids:
        return []

    # Fetch profiles for each partner
    entries = []
    for org_id in partner_org_ids:
        profile = await get_profile(db, org_id)
        signals_for_case = (
            await db.execute(
                select(func.count())
                .select_from(PartnerTrustSignal)
                .where(
                    PartnerTrustSignal.partner_org_id == org_id,
                    PartnerTrustSignal.source_entity_type == "building_case",
                    PartnerTrustSignal.source_entity_id == case_id,
                )
            )
        ).scalar() or 0

        entries.append(
            {
                "partner_org_id": str(org_id),
                "case_id": str(case_id),
                "overall_trust_level": profile.overall_trust_level if profile else "unknown",
                "delivery_reliability_score": profile.delivery_reliability_score if profile else None,
                "evidence_quality_score": profile.evidence_quality_score if profile else None,
                "responsiveness_score": profile.responsiveness_score if profile else None,
                "total_signal_count": profile.signal_count if profile else 0,
                "case_signal_count": signals_for_case,
            }
        )

    return entries


async def get_trusted_partners_for_work_family(
    db: AsyncSession,
    org_id: UUID,
    work_family: str,
) -> list[dict]:
    """Get partners with adequate+ trust for a specific work family.

    For RFQ panel selection guidance (not ranking -- just qualification).
    Returns partners that have trust level 'strong' or 'adequate'.
    work_family is used as context info; all adequate+ partners are returned
    since trust profiles are org-level, not work-family-specific.
    """
    result = await db.execute(
        select(PartnerTrustProfile).where(
            PartnerTrustProfile.overall_trust_level.in_(("strong", "adequate")),
        )
    )
    profiles = list(result.scalars().all())

    entries = []
    for p in profiles:
        # Skip the requesting org itself
        if p.partner_org_id == org_id:
            continue
        entries.append(
            {
                "partner_org_id": str(p.partner_org_id),
                "overall_trust_level": p.overall_trust_level,
                "delivery_reliability_score": p.delivery_reliability_score,
                "evidence_quality_score": p.evidence_quality_score,
                "responsiveness_score": p.responsiveness_score,
                "signal_count": p.signal_count,
                "work_family": work_family,
                "guidance": "qualified",  # adequate+ = qualified for panel
            }
        )

    return entries
