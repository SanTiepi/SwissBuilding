"""Tests for trust_annotation_service — pure function annotations."""

from datetime import UTC, date, datetime

from app.services.trust_annotation_service import (
    annotate_identity_confidence,
    annotate_obligation_urgency,
    annotate_publication_freshness,
)

# ─── Freshness ──────────────────────────────────────────────────────


class TestPublicationFreshness:
    def test_current_when_recent(self):
        now = datetime(2026, 3, 1, tzinfo=UTC)
        published = datetime(2026, 1, 1, tzinfo=UTC)
        result = annotate_publication_freshness(published, now=now)
        assert result.state == "current"
        assert result.age_days == 59

    def test_aging_at_one_year(self):
        now = datetime(2027, 6, 1, tzinfo=UTC)
        published = datetime(2026, 3, 1, tzinfo=UTC)
        result = annotate_publication_freshness(published, now=now)
        assert result.state == "aging"
        assert result.age_days >= 365

    def test_stale_after_two_years(self):
        now = datetime(2028, 6, 1, tzinfo=UTC)
        published = datetime(2026, 1, 1, tzinfo=UTC)
        result = annotate_publication_freshness(published, now=now)
        assert result.state == "stale"
        assert result.age_days > 730

    def test_superseded_overrides_age(self):
        now = datetime(2026, 2, 1, tzinfo=UTC)
        published = datetime(2026, 1, 1, tzinfo=UTC)
        result = annotate_publication_freshness(published, now=now, has_newer_version=True)
        assert result.state == "superseded"

    def test_handles_naive_datetime(self):
        now = datetime(2026, 6, 1)
        published = datetime(2026, 1, 1)
        result = annotate_publication_freshness(published, now=now)
        assert result.state == "current"

    def test_boundary_365_days(self):
        now = datetime(2027, 1, 1, tzinfo=UTC)
        published = datetime(2026, 1, 1, tzinfo=UTC)
        result = annotate_publication_freshness(published, now=now)
        assert result.state == "aging"
        assert result.age_days == 365


# ─── Identity confidence ───────────────────────────────────────────


class TestIdentityConfidence:
    def test_auto_matched_egid_is_high(self):
        result = annotate_identity_confidence("auto_matched", "egid")
        assert result.confidence == "high"

    def test_auto_matched_egrid_is_medium(self):
        result = annotate_identity_confidence("auto_matched", "egrid")
        assert result.confidence == "medium"

    def test_auto_matched_address_is_medium(self):
        result = annotate_identity_confidence("auto_matched", "address")
        assert result.confidence == "medium"

    def test_manual_matched_is_high(self):
        result = annotate_identity_confidence("manual_matched", "egid")
        assert result.confidence == "high"

    def test_needs_review_is_low(self):
        result = annotate_identity_confidence("needs_review", "none")
        assert result.confidence == "low"

    def test_unmatched_is_unverified(self):
        result = annotate_identity_confidence("unmatched", "none")
        assert result.confidence == "unverified"


# ─── Obligation urgency ────────────────────────────────────────────


class TestObligationUrgency:
    def test_overdue(self):
        today = date(2026, 3, 25)
        due = date(2026, 3, 20)
        result = annotate_obligation_urgency(due, today=today)
        assert result.urgency == "overdue"
        assert result.days_remaining == -5

    def test_critical_same_day(self):
        today = date(2026, 3, 25)
        due = date(2026, 3, 25)
        result = annotate_obligation_urgency(due, today=today)
        assert result.urgency == "critical"
        assert result.days_remaining == 0

    def test_critical_3_days(self):
        today = date(2026, 3, 25)
        due = date(2026, 3, 28)
        result = annotate_obligation_urgency(due, today=today)
        assert result.urgency == "critical"
        assert result.days_remaining == 3

    def test_due_soon_7_days(self):
        today = date(2026, 3, 25)
        due = date(2026, 4, 1)
        result = annotate_obligation_urgency(due, today=today)
        assert result.urgency == "due_soon"
        assert result.days_remaining == 7

    def test_upcoming_20_days(self):
        today = date(2026, 3, 25)
        due = date(2026, 4, 14)
        result = annotate_obligation_urgency(due, today=today)
        assert result.urgency == "upcoming"
        assert result.days_remaining == 20

    def test_distant_60_days(self):
        today = date(2026, 3, 25)
        due = date(2026, 5, 24)
        result = annotate_obligation_urgency(due, today=today)
        assert result.urgency == "distant"
        assert result.days_remaining == 60
