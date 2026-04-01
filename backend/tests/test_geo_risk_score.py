"""Tests for compute_geo_risk_score — composite geospatial risk."""

from __future__ import annotations

import pytest

from app.services.enrichment.score_computers import compute_geo_risk_score

# ---------------------------------------------------------------------------
# Helpers: build enrichment_meta fixtures
# ---------------------------------------------------------------------------


def _all_low_risk() -> dict:
    """All dimensions present with low/safe values."""
    return {
        "natural_hazards": {
            "flood_risk": "low",
            "landslide_risk": "none",
            "rockfall_risk": "none",
        },
        "flood_zones": {"flood_danger_level": "gering"},
        "seismic": {"seismic_zone": "1"},
        "contaminated_sites": {"is_contaminated": False},
        "radon": {"radon_level": "low"},
        "noise": {"road_noise_day_db": 38},
        "railway_noise": {"railway_noise_day_db": 30},
        "aircraft_noise": {"aircraft_noise_db": 25},
        "groundwater_zones": {"protection_zone": "S3"},
        "accident_sites": {"near_seveso_site": False},
    }


def _all_high_risk() -> dict:
    """All dimensions present with high/dangerous values."""
    return {
        "natural_hazards": {
            "flood_risk": "high",
            "landslide_risk": "high",
            "rockfall_risk": "high",
        },
        "flood_zones": {"flood_danger_level": "hoch"},
        "seismic": {"seismic_zone": "3b"},
        "contaminated_sites": {"is_contaminated": True},
        "radon": {"radon_level": "high"},
        "noise": {"road_noise_day_db": 72},
        "railway_noise": {"railway_noise_day_db": 70},
        "aircraft_noise": {"aircraft_noise_db": 68},
        "groundwater_zones": {"protection_zone": "S1"},
        "accident_sites": {"near_seveso_site": True, "distance_m": 100},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGeoRiskScoreLowRisk:
    """All-safe scenario."""

    def test_all_low_risk(self):
        meta = _all_low_risk()
        result = compute_geo_risk_score(meta)
        assert result is not None
        score = result["geo_risk_score"]
        assert score <= 20, f"All-safe should score low, got {score}"
        assert result["geo_risk_grade"] == "A"
        assert result["data_completeness"] == 1.0


class TestGeoRiskScoreHighRisk:
    """All-dangerous scenario."""

    def test_all_high_risk(self):
        meta = _all_high_risk()
        result = compute_geo_risk_score(meta)
        assert result is not None
        score = result["geo_risk_score"]
        assert score >= 80, f"All-dangerous should score high, got {score}"
        assert result["geo_risk_grade"] in ("E", "F")
        assert result["data_completeness"] == 1.0


class TestFloodHeavyWeight:
    """Flood dominates when high."""

    def test_flood_heavy_weight(self):
        meta = _all_low_risk()
        # Override flood to high
        meta["natural_hazards"]["flood_risk"] = "high"
        meta["flood_zones"]["flood_danger_level"] = "hoch"
        result = compute_geo_risk_score(meta)
        assert result is not None
        breakdown = result["breakdown"]
        # Flood should be top risk contributor
        flood_contribution = breakdown["flood_risk"]["score"] * breakdown["flood_risk"]["weight"]
        for dim, info in breakdown.items():
            if dim == "flood_risk":
                continue
            other_contribution = info["score"] * info["weight"]
            assert flood_contribution >= other_contribution, (
                f"Flood ({flood_contribution}) should dominate {dim} ({other_contribution})"
            )


class TestContaminatedSiteHeavyWeight:
    """Contamination dominates when present."""

    def test_contaminated_site_heavy_weight(self):
        meta = _all_low_risk()
        meta["contaminated_sites"] = {"is_contaminated": True}
        result = compute_geo_risk_score(meta)
        assert result is not None
        breakdown = result["breakdown"]
        assert breakdown["contamination"]["score"] == 90.0
        assert "contamination" in result["top_risks"]


class TestRadonHighZone:
    """Radon high zone produces elevated score."""

    def test_radon_high_zone(self):
        meta = _all_low_risk()
        meta["radon"] = {"radon_level": "high"}
        result = compute_geo_risk_score(meta)
        assert result is not None
        breakdown = result["breakdown"]
        assert breakdown["radon"]["score"] == 80.0
        assert breakdown["radon"]["level"] == "high"


class TestNoiseLoud:
    """>65 dB noise."""

    def test_noise_loud(self):
        meta = _all_low_risk()
        meta["noise"] = {"road_noise_day_db": 68}
        result = compute_geo_risk_score(meta)
        assert result is not None
        breakdown = result["breakdown"]
        assert breakdown["noise"]["score"] >= 65.0


class TestMixedRiskProfile:
    """Mix of high and low risk dimensions."""

    def test_mixed_risk_profile(self):
        meta = _all_low_risk()
        # Raise a few dimensions
        meta["radon"] = {"radon_level": "high"}
        meta["natural_hazards"]["landslide_risk"] = "high"
        meta["contaminated_sites"] = {"is_contaminated": True}
        result = compute_geo_risk_score(meta)
        assert result is not None
        score = result["geo_risk_score"]
        # Should be in the middle band (C or D), not extreme
        assert 30 <= score <= 70, f"Mixed profile should be mid-range, got {score}"
        assert result["geo_risk_grade"] in ("C", "D")


class TestMissingDataGraceful:
    """Partial data should still compute a score."""

    def test_missing_data_graceful(self):
        meta = {
            "radon": {"radon_level": "medium"},
            "seismic": {"seismic_zone": "2"},
            # Only 2 out of 9 dimensions have data
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert 0 < result["geo_risk_score"] <= 100
        assert len(result["breakdown"]) == 2
        assert result["data_completeness"] == pytest.approx(2 / 9, abs=0.01)


class TestNoDataReturnsNone:
    """Empty enrichment_meta → None."""

    def test_no_data_returns_none(self):
        assert compute_geo_risk_score({}) is None

    def test_irrelevant_keys_returns_none(self):
        meta = {"solar": {"suitability": "high"}, "transport": {"transport_quality_class": "A"}}
        assert compute_geo_risk_score(meta) is None


class TestGradeBoundaries:
    """Grade thresholds: A<=15, B<=30, C<=50, D<=70, E<=85, F>85."""

    @pytest.mark.parametrize(
        "score, expected_grade",
        [
            (0.0, "A"),
            (15.0, "A"),
            (15.1, "B"),
            (30.0, "B"),
            (30.1, "C"),
            (50.0, "C"),
            (50.1, "D"),
            (70.0, "D"),
            (70.1, "E"),
            (85.0, "E"),
            (85.1, "F"),
            (100.0, "F"),
        ],
    )
    def test_grade_boundaries(self, score, expected_grade):
        from app.services.enrichment.score_computers import _geo_grade

        assert _geo_grade(score) == expected_grade


class TestTopRisksReturnsTop3:
    """top_risks should contain at most 3 dimension names."""

    def test_top_risks_returns_top_3(self):
        meta = _all_high_risk()
        result = compute_geo_risk_score(meta)
        assert result is not None
        top = result["top_risks"]
        assert len(top) == 3
        # Each entry should be a valid dimension name
        valid_dims = {
            "flood_risk",
            "seismic_risk",
            "contamination",
            "radon",
            "noise",
            "landslide",
            "rockfall",
            "groundwater_restriction",
            "seveso_proximity",
        }
        for name in top:
            assert name in valid_dims

    def test_top_risks_with_few_dimensions(self):
        meta = {"radon": {"radon_level": "high"}, "seismic": {"seismic_zone": "2"}}
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert len(result["top_risks"]) == 2  # only 2 dimensions available


class TestDataCompletenessCalculation:
    """data_completeness = available_dimensions / 9."""

    def test_data_completeness_calculation(self):
        meta = _all_low_risk()
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["data_completeness"] == 1.0

    def test_partial_completeness(self):
        meta = {
            "radon": {"radon_level": "low"},
            "contaminated_sites": {"is_contaminated": False},
            "accident_sites": {"near_seveso_site": False},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["data_completeness"] == pytest.approx(3 / 9, abs=0.01)


class TestSevesoProximityHighRisk:
    """Seveso/major accident site nearby."""

    def test_seveso_proximity_high_risk(self):
        meta = _all_low_risk()
        meta["accident_sites"] = {"near_seveso_site": True, "distance_m": 150}
        result = compute_geo_risk_score(meta)
        assert result is not None
        breakdown = result["breakdown"]
        assert breakdown["seveso_proximity"]["score"] == 95.0
        assert breakdown["seveso_proximity"]["level"] == "high"
        assert "seveso_proximity" in result["top_risks"]

    def test_seveso_far_away(self):
        meta = _all_low_risk()
        meta["accident_sites"] = {"near_seveso_site": True, "distance_m": 1500}
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["breakdown"]["seveso_proximity"]["score"] == 30.0

    def test_seveso_no_distance_info(self):
        meta = _all_low_risk()
        meta["accident_sites"] = {"near_seveso_site": True}
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["breakdown"]["seveso_proximity"]["score"] == 80.0
