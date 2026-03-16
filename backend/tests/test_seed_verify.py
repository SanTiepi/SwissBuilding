"""
Tests for seed_verify.py — validates the verification logic,
thresholds, and informational checks for runtime-generated models.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.seeds.seed_verify import (
    CORE_MODELS,
    INFO_CHECKS,
    THRESHOLDS,
    verify,
)

# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------


class TestSeedVerifyConfig:
    """Tests for seed_verify configuration constants."""

    def test_thresholds_cover_core_models(self):
        """Every core model label must have a threshold entry."""
        core_labels = {label for label, _model in CORE_MODELS}
        threshold_labels = set(THRESHOLDS.keys())
        assert core_labels == threshold_labels

    def test_campaigns_threshold_at_least_one(self):
        """Campaigns must require at least 1 seeded record."""
        assert THRESHOLDS["campaigns"] >= 1

    def test_info_checks_have_required_fields(self):
        """Each info check must have a label, model, and note."""
        for check in INFO_CHECKS:
            assert check.label, "InfoCheck must have a label"
            assert check.model is not None, "InfoCheck must have a model"
            assert check.note, "InfoCheck must have a note"

    def test_info_checks_cover_expected_models(self):
        """All Wave 6-11 runtime-generated models must be covered."""
        labels = {check.label for check in INFO_CHECKS}
        expected = {
            "saved_simulations",
            "data_quality_issues",
            "change_signals",
            "readiness_assessments",
            "building_trust_scores",
            "unknown_issues",
            "post_works_states",
            "compliance_artefacts",
        }
        assert expected.issubset(labels)

    def test_no_duplicate_labels(self):
        """No duplicate labels across core models and info checks."""
        all_labels = [label for label, _model in CORE_MODELS]
        all_labels += [check.label for check in INFO_CHECKS]
        assert len(all_labels) == len(set(all_labels))


# ---------------------------------------------------------------------------
# Verify logic tests (mocked DB)
# ---------------------------------------------------------------------------


def _mock_session_with_counts(count_map: dict[str, int]):
    """Create a mock AsyncSessionLocal that returns counts from count_map."""
    call_index = 0
    all_labels = [label for label, _model in CORE_MODELS] + [c.label for c in INFO_CHECKS]

    async def mock_execute(_query):
        nonlocal call_index
        label = all_labels[call_index]
        call_index += 1
        result = MagicMock()
        result.scalar.return_value = count_map.get(label, 0)
        return result

    session = AsyncMock()
    session.execute = mock_execute
    return session


@pytest.mark.asyncio
class TestVerifyFunction:
    """Tests for the verify() function with mocked database."""

    async def test_verify_all_pass(self):
        """When all counts meet thresholds, no failures are returned."""
        counts = {label: minimum for label, minimum in THRESHOLDS.items()}
        session = _mock_session_with_counts(counts)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.seeds.seed_verify.AsyncSessionLocal", return_value=ctx):
            failures, result_counts, _info_messages = await verify()

        assert failures == []
        for label, minimum in THRESHOLDS.items():
            assert result_counts[label] >= minimum

    async def test_verify_detects_insufficient_data(self):
        """When a core model count is below threshold, it's reported as a failure."""
        counts = {label: minimum for label, minimum in THRESHOLDS.items()}
        counts["buildings"] = 0  # Below threshold of 3

        session = _mock_session_with_counts(counts)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.seeds.seed_verify.AsyncSessionLocal", return_value=ctx):
            failures, _result_counts, _info_messages = await verify()

        assert len(failures) == 1
        assert "buildings" in failures[0]
        assert "0" in failures[0]

    async def test_verify_info_checks_report_zero(self):
        """Runtime-generated models with 0 records produce info messages with notes."""
        counts = {label: minimum for label, minimum in THRESHOLDS.items()}
        # All info checks default to 0

        session = _mock_session_with_counts(counts)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.seeds.seed_verify.AsyncSessionLocal", return_value=ctx):
            failures, _result_counts, info_messages = await verify()

        assert failures == []
        assert len(info_messages) == len(INFO_CHECKS)
        # Each message for 0-count should contain the note
        for check in INFO_CHECKS:
            matching = [m for m in info_messages if check.label in m]
            assert len(matching) == 1
            assert "0 records" in matching[0]
            assert check.note in matching[0]

    async def test_verify_info_checks_report_nonzero(self):
        """Runtime-generated models with >0 records report count without note."""
        counts = {label: minimum for label, minimum in THRESHOLDS.items()}
        counts["change_signals"] = 5

        session = _mock_session_with_counts(counts)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.seeds.seed_verify.AsyncSessionLocal", return_value=ctx):
            _failures, _result_counts, info_messages = await verify()

        signal_msgs = [m for m in info_messages if "change_signals" in m]
        assert len(signal_msgs) == 1
        assert "5 records" in signal_msgs[0]
