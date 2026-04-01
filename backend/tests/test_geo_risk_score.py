"""Tests for geo risk score composite service."""

from __future__ import annotations

from app.services.geo_risk_score_service import (
    _score_contamination,
    _score_grele,
    _score_inondation,
    _score_radon,
    _score_seismic,
    compute_geo_risk_score,
)


class TestSubScores:
    """Test individual sub-dimension scoring functions."""

    def test_inondation_erheblich(self):
        ctx = {"natural_hazards": {"gefahrenstufe": "erheblich"}}
        assert _score_inondation(ctx) == 10.0

    def test_inondation_mittel(self):
        ctx = {"natural_hazards": {"gefahrenstufe": "mittel"}}
        assert _score_inondation(ctx) == 7.0

    def test_inondation_gering(self):
        ctx = {"natural_hazards": {"gefahrenstufe": "gering"}}
        assert _score_inondation(ctx) == 4.0

    def test_inondation_missing(self):
        assert _score_inondation({}) == 0.0

    def test_seismic_class_e(self):
        ctx = {"seismic": {"baugrundklasse": "E"}}
        assert _score_seismic(ctx) == 10.0

    def test_seismic_class_b(self):
        ctx = {"seismic": {"baugrundklasse": "B"}}
        assert _score_seismic(ctx) == 4.0

    def test_seismic_missing(self):
        assert _score_seismic({}) == 0.0

    def test_grele_frequency(self):
        ctx = {"grele": {"frequency": 6.5}}
        assert _score_grele(ctx) == 6.5

    def test_grele_zone_high(self):
        ctx = {"grele": {"zone": "high"}}
        assert _score_grele(ctx) == 8.0

    def test_grele_missing(self):
        assert _score_grele({}) == 0.0

    def test_contamination_sanierung(self):
        ctx = {"contaminated_sites": {"status": "sanierungsbedürftig"}}
        assert _score_contamination(ctx) == 10.0

    def test_contamination_belastet(self):
        ctx = {"contaminated_sites": {"status": "belastet"}}
        assert _score_contamination(ctx) == 5.0

    def test_contamination_missing(self):
        assert _score_contamination({}) == 0.0

    def test_radon_high_bq(self):
        ctx = {"radon": {"radon_bq_m3": "600-1000"}}
        assert _score_radon(ctx) == 10.0

    def test_radon_moderate_bq(self):
        ctx = {"radon": {"radon_bq_m3": "200-400"}}
        assert _score_radon(ctx) == 7.0

    def test_radon_zone_based(self):
        ctx = {"radon": {"zone": "moderate", "radonrisiko": "mittel"}}
        assert _score_radon(ctx) == 5.0

    def test_radon_missing(self):
        assert _score_radon({}) == 0.0


class TestComposite:
    """Test composite score computation."""

    def test_all_zero(self):
        result = compute_geo_risk_score({})
        assert result["score"] == 0
        for dim in ["inondation", "seismic", "grele", "contamination", "radon"]:
            assert result[dim] == 0.0

    def test_full_risk(self):
        ctx = {
            "natural_hazards": {"gefahrenstufe": "erheblich"},
            "seismic": {"baugrundklasse": "E"},
            "grele": {"frequency": 10},
            "contaminated_sites": {"status": "sanierungsbedürftig"},
            "radon": {"radon_bq_m3": "1500"},
        }
        result = compute_geo_risk_score(ctx)
        assert result["score"] == 100
        assert result["inondation"] == 10.0
        assert result["seismic"] == 10.0
        assert result["grele"] == 10.0
        assert result["contamination"] == 10.0
        assert result["radon"] == 10.0

    def test_partial_data(self):
        ctx = {
            "natural_hazards": {"gefahrenstufe": "gering"},
            "radon": {"radon_bq_m3": "200-400"},
        }
        result = compute_geo_risk_score(ctx)
        # inondation=4 + radon=7 = 11 x 2 = 22
        assert result["score"] == 22
        assert result["inondation"] == 4.0
        assert result["radon"] == 7.0
        assert result["seismic"] == 0.0

    def test_result_structure(self):
        result = compute_geo_risk_score({})
        assert "score" in result
        assert "inondation" in result
        assert "seismic" in result
        assert "grele" in result
        assert "contamination" in result
        assert "radon" in result
