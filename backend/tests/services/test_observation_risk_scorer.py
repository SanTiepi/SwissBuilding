"""Tests for observation risk scorer — pure scoring + persistence."""

import pytest

from app.services.observation_risk_scorer import (
    calculate_risk_score,
    determine_recommended_action,
    determine_urgency_level,
)


class TestCalculateRiskScore:
    def test_good_condition_no_flags(self):
        assert calculate_risk_score("good", []) == 10.0

    def test_fair_condition_no_flags(self):
        assert calculate_risk_score("fair", []) == 35.0

    def test_poor_condition_no_flags(self):
        assert calculate_risk_score("poor", []) == 60.0

    def test_critical_condition_no_flags(self):
        assert calculate_risk_score("critical", []) == 85.0

    def test_good_condition_single_flag(self):
        score = calculate_risk_score("good", ["crack"])
        assert score == pytest.approx(12.5, abs=0.1)

    def test_poor_with_mold(self):
        score = calculate_risk_score("poor", ["mold"])
        assert score == pytest.approx(84.0, abs=0.1)

    def test_critical_with_multiple_flags(self):
        score = calculate_risk_score("critical", ["water_stain", "crack", "mold"])
        # 85 * 1.3 * 1.25 * 1.4 = 193.375 -> capped at 100
        assert score == 100.0

    def test_score_capped_at_100(self):
        score = calculate_risk_score("critical", ["water_stain", "crack", "mold", "rust", "deformation"])
        assert score == 100.0

    def test_unknown_condition_returns_zero(self):
        assert calculate_risk_score("unknown", []) == 0.0

    def test_none_condition_returns_zero(self):
        assert calculate_risk_score(None, []) == 0.0

    def test_none_flags_returns_base(self):
        assert calculate_risk_score("fair", None) == 35.0

    def test_empty_flags_returns_base(self):
        assert calculate_risk_score("poor", []) == 60.0

    def test_unknown_flag_ignored(self):
        score = calculate_risk_score("fair", ["unknown_flag"])
        assert score == 35.0

    def test_rust_multiplier(self):
        score = calculate_risk_score("fair", ["rust"])
        assert score == pytest.approx(42.0, abs=0.1)

    def test_deformation_multiplier(self):
        score = calculate_risk_score("fair", ["deformation"])
        assert score == pytest.approx(47.2, abs=0.2)


class TestDetermineRecommendedAction:
    def test_low_score_monitor(self):
        assert determine_recommended_action(10.0) == "monitor"

    def test_medium_score_investigate(self):
        assert determine_recommended_action(50.0) == "investigate_further"

    def test_high_score_urgent(self):
        assert determine_recommended_action(80.0) == "urgent_diagnosis"

    def test_boundary_40_investigate(self):
        assert determine_recommended_action(40.0) == "investigate_further"

    def test_boundary_70_urgent(self):
        assert determine_recommended_action(70.0) == "urgent_diagnosis"

    def test_zero_monitor(self):
        assert determine_recommended_action(0.0) == "monitor"

    def test_100_urgent(self):
        assert determine_recommended_action(100.0) == "urgent_diagnosis"


class TestDetermineUrgencyLevel:
    def test_low(self):
        assert determine_urgency_level(10.0) == "low"

    def test_medium(self):
        assert determine_urgency_level(40.0) == "medium"

    def test_high(self):
        assert determine_urgency_level(65.0) == "high"

    def test_critical(self):
        assert determine_urgency_level(90.0) == "critical"

    def test_boundary_35_medium(self):
        assert determine_urgency_level(35.0) == "medium"

    def test_boundary_60_high(self):
        assert determine_urgency_level(60.0) == "high"

    def test_boundary_80_critical(self):
        assert determine_urgency_level(80.0) == "critical"
