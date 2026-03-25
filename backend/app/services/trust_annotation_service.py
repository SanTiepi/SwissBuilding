"""Trust annotation service — pure functions that compute trust semantics.

These annotate entities with freshness, identity confidence, and urgency
without performing any database writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

# ─── Freshness ──────────────────────────────────────────────────────

FreshnessState = Literal["current", "aging", "stale", "superseded"]


@dataclass(frozen=True)
class FreshnessAnnotation:
    state: FreshnessState
    age_days: int
    description: str


def annotate_publication_freshness(
    published_at: datetime,
    *,
    now: datetime | None = None,
    has_newer_version: bool = False,
) -> FreshnessAnnotation:
    """Compute freshness based on publication age.

    - < 1 year = current
    - 1-2 years = aging
    - > 2 years = stale
    - has_newer_version = superseded (regardless of age)
    """
    if now is None:
        now = datetime.now(UTC)

    # Ensure both are timezone-aware for comparison
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    age_days = max(0, (now - published_at).days)

    if has_newer_version:
        return FreshnessAnnotation(
            state="superseded",
            age_days=age_days,
            description="A newer version exists",
        )

    if age_days < 365:
        return FreshnessAnnotation(state="current", age_days=age_days, description="Less than 1 year old")
    if age_days < 730:
        return FreshnessAnnotation(state="aging", age_days=age_days, description="Between 1 and 2 years old")
    return FreshnessAnnotation(state="stale", age_days=age_days, description="More than 2 years old")


# ─── Identity confidence ───────────────────────────────────────────

IdentityConfidence = Literal["high", "medium", "low", "unverified"]


@dataclass(frozen=True)
class IdentityAnnotation:
    confidence: IdentityConfidence
    reason: str


def annotate_identity_confidence(
    match_state: str,
    match_key_type: str,
) -> IdentityAnnotation:
    """Compute identity confidence from match_state and match_key_type.

    - auto_matched + egid → high
    - auto_matched + egrid → medium
    - auto_matched + other → medium
    - manual_matched → high
    - needs_review → low
    - unmatched → unverified
    """
    if match_state == "manual_matched":
        return IdentityAnnotation(confidence="high", reason="Manually verified match")

    if match_state == "auto_matched":
        if match_key_type == "egid":
            return IdentityAnnotation(confidence="high", reason="Auto-matched by EGID")
        if match_key_type == "egrid":
            return IdentityAnnotation(confidence="medium", reason="Auto-matched by EGRID")
        return IdentityAnnotation(confidence="medium", reason=f"Auto-matched by {match_key_type}")

    if match_state == "needs_review":
        return IdentityAnnotation(confidence="low", reason="Needs manual review")

    return IdentityAnnotation(confidence="unverified", reason="No match established")


# ─── Obligation urgency ────────────────────────────────────────────

UrgencyHint = Literal["overdue", "critical", "due_soon", "upcoming", "distant"]


@dataclass(frozen=True)
class UrgencyAnnotation:
    urgency: UrgencyHint
    days_remaining: int
    description: str


def annotate_obligation_urgency(
    due_date: date,
    *,
    today: date | None = None,
) -> UrgencyAnnotation:
    """Compute urgency hint based on days to due_date.

    - past due → overdue
    - 0-3 days → critical
    - 4-14 days → due_soon
    - 15-30 days → upcoming
    - > 30 days → distant
    """
    if today is None:
        today = date.today()

    days_remaining = (due_date - today).days

    if days_remaining < 0:
        return UrgencyAnnotation(
            urgency="overdue",
            days_remaining=days_remaining,
            description=f"Overdue by {abs(days_remaining)} days",
        )
    if days_remaining <= 3:
        return UrgencyAnnotation(
            urgency="critical",
            days_remaining=days_remaining,
            description=f"Due in {days_remaining} days",
        )
    if days_remaining <= 14:
        return UrgencyAnnotation(
            urgency="due_soon",
            days_remaining=days_remaining,
            description=f"Due in {days_remaining} days",
        )
    if days_remaining <= 30:
        return UrgencyAnnotation(
            urgency="upcoming",
            days_remaining=days_remaining,
            description=f"Due in {days_remaining} days",
        )
    return UrgencyAnnotation(
        urgency="distant",
        days_remaining=days_remaining,
        description=f"Due in {days_remaining} days",
    )
