"""Tests for composite geo risk score from score_computers.py."""

from __future__ import annotations

from app.services.enrichment.score_computers import compute_geo_risk_score


class TestCompositeGeoRiskScore:
    """Test compute_geo_risk_score with various risk combinations."""

    def test_no_data_returns_none(self):
        """No enrichment data at all -> None (cannot compute)."""
        assert compute_geo_risk_score({}) is None

    def test_all_low_risk(self):
        """All dimensions present but low risk -> low score, grade A or B."""
        meta = {
            "natural_hazards": {"flood_risk": "low", "landslide_risk": "low", "rockfall_risk": "low"},
            "flood_zones": {"flood_danger_level": "gering"},
            "seismic": {"seismic_zone": "1"},
            "contaminated_sites": {"is_contaminated": False},
            "radon": {"radon_level": "low"},
            "noise": {"road_noise_day_db": 35},
            "railway_noise": {"railway_noise_day_db": 30},
            "aircraft_noise": {"aircraft_noise_db": 25},
            "groundwater_zones": {"protection_zone": "S3"},
            "accident_sites": {"near_seveso_site": False},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert 0 <= result["geo_risk_score"] <= 30
        assert result["geo_risk_grade"] in ("A", "B")
        assert "breakdown" in result
        assert "top_risks" in result
        assert result["data_completeness"] == 1.0

    def test_all_high_risk(self):
        """All dimensions at maximum -> high score, grade E or F."""
        meta = {
            "natural_hazards": {"flood_risk": "high", "landslide_risk": "high", "rockfall_risk": "high"},
            "flood_zones": {"flood_danger_level": "hoch"},
            "seismic": {"seismic_zone": "3b"},
            "contaminated_sites": {"is_contaminated": True},
            "radon": {"radon_level": "high"},
            "noise": {"road_noise_day_db": 75},
            "railway_noise": {},
            "aircraft_noise": {},
            "groundwater_zones": {"protection_zone": "S1"},
            "accident_sites": {"near_seveso_site": True, "distance_m": 100},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["geo_risk_score"] >= 70
        assert result["geo_risk_grade"] in ("D", "E", "F")
        assert len(result["top_risks"]) <= 3

    def test_mixed_risk(self):
        """Some high, some low -> mid-range score."""
        meta = {
            "flood_zones": {"flood_danger_level": "hoch"},  # high flood
            "seismic": {"seismic_zone": "1"},  # low seismic
            "contaminated_sites": {"is_contaminated": False},  # low contam
            "radon": {"radon_level": "high"},  # high radon
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert 20 <= result["geo_risk_score"] <= 80
        assert result["geo_risk_grade"] in ("B", "C", "D", "E")

    def test_partial_data_completeness(self):
        """Only a few dimensions present -> data_completeness < 1.0."""
        meta = {
            "seismic": {"seismic_zone": "2"},
            "radon": {"radon_level": "medium"},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["data_completeness"] < 1.0
        assert result["data_completeness"] == round(2 / 9, 2)

    def test_result_structure(self):
        """Output has all required keys."""
        meta = {"seismic": {"seismic_zone": "2"}}
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert "geo_risk_score" in result
        assert "geo_risk_grade" in result
        assert "breakdown" in result
        assert "top_risks" in result
        assert "data_completeness" in result
        assert isinstance(result["breakdown"], dict)
        assert isinstance(result["top_risks"], list)

    def test_breakdown_has_weight_score_level(self):
        """Each breakdown dimension includes score, weight, and level."""
        meta = {
            "flood_zones": {"flood_danger_level": "mittel"},
            "seismic": {"seismic_zone": "3a"},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        for _dim_name, dim_data in result["breakdown"].items():
            assert "score" in dim_data
            assert "weight" in dim_data
            assert "level" in dim_data
            assert dim_data["level"] in ("low", "moderate", "elevated", "high")

    def test_grade_boundaries(self):
        """Verify grade thresholds: A<=15, B<=30, C<=50, D<=70, E<=85, F>85."""
        # Single dim with known score to test grade
        # seismic zone 1 -> 20.0 score, only dim -> weighted avg = 20.0 -> grade B
        meta = {"seismic": {"seismic_zone": "1"}}
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["geo_risk_score"] == 20.0
        assert result["geo_risk_grade"] == "B"

    def test_top_risks_ordered(self):
        """Top risks are the dimensions with highest weighted contribution."""
        meta = {
            "contaminated_sites": {"is_contaminated": True},  # 90 * 3.0 = 270
            "seismic": {"seismic_zone": "1"},  # 20 * 2.5 = 50
            "radon": {"radon_level": "low"},  # 10 * 2.0 = 20
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["top_risks"][0] == "contamination"

    def test_seveso_proximity_distance_modulates(self):
        """Seveso score varies by distance."""
        close = {"accident_sites": {"near_seveso_site": True, "distance_m": 100}}
        far = {"accident_sites": {"near_seveso_site": True, "distance_m": 800}}
        r_close = compute_geo_risk_score(close)
        r_far = compute_geo_risk_score(far)
        assert r_close is not None and r_far is not None
        assert r_close["geo_risk_score"] > r_far["geo_risk_score"]

    def test_noise_loudest_source_wins(self):
        """Noise score is based on the loudest source."""
        meta = {
            "noise": {"road_noise_day_db": 40},
            "railway_noise": {"railway_noise_day_db": 72},
            "aircraft_noise": {"aircraft_noise_db": 30},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["breakdown"]["noise"]["score"] == 85.0  # >70 dB

    def test_groundwater_s1_highest_risk(self):
        """S1 protection zone = highest groundwater restriction score."""
        meta = {"groundwater_zones": {"protection_zone": "S1"}}
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["breakdown"]["groundwater_restriction"]["score"] == 90.0

    def test_score_clamped_to_100(self):
        """Score never exceeds 100."""
        meta = {
            "natural_hazards": {"flood_risk": "high", "landslide_risk": "high", "rockfall_risk": "high"},
            "flood_zones": {"flood_danger_level": "hoch"},
            "seismic": {"seismic_zone": "3b"},
            "contaminated_sites": {"is_contaminated": True},
            "radon": {"radon_level": "high"},
            "noise": {"road_noise_day_db": 80},
            "groundwater_zones": {"protection_zone": "S1"},
            "accident_sites": {"near_seveso_site": True, "distance_m": 50},
        }
        result = compute_geo_risk_score(meta)
        assert result is not None
        assert result["geo_risk_score"] <= 100.0
