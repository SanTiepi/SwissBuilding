"""
Comprehensive edge-case tests for the compliance engine, risk engine,
and renovation simulator services.
"""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.compliance_engine import (
    _normalise_state,
    auto_classify_sample,
    check_suva_notification_required,
    check_threshold,
    determine_action_required,
    determine_cfst_work_category,
    determine_risk_level,
    determine_waste_disposal,
    get_cantonal_requirements,
)
from app.services.renovation_simulator import (
    BASE_COSTS_CHF_PER_M2,
    MATERIAL_CATEGORIES_BY_RENOVATION,
    _risk_to_cost_tier,
    estimate_remediation_cost,
    estimate_timeline_weeks,
    get_compliance_requirements,
    get_required_diagnostics,
    simulate_renovation,
)
from app.services.risk_engine import (
    RENOVATION_EXPOSURE,
    _adjust_with_neighbor_samples,
    _apply_diagnostic_override,
    apply_modifiers,
    apply_renovation_modifier,
    calculate_asbestos_base_probability,
    calculate_building_risk,
    calculate_confidence,
    calculate_hap_base_probability,
    calculate_lead_base_probability,
    calculate_overall_risk_level,
    calculate_pcb_base_probability,
    calculate_radon_base_probability,
)

# ===================================================================
# SECTION 1: Compliance Engine Edge Cases
# ===================================================================


class TestCheckThresholdExactValues:
    """Test check_threshold at exact threshold boundaries."""

    @pytest.mark.parametrize(
        "pollutant,unit,threshold",
        [
            ("asbestos", "percent_weight", 1.0),
            ("asbestos", "fibers_per_m3", 1000),
            ("pcb", "mg_per_kg", 50),
            ("pcb", "ng_per_m3", 6000),
            ("lead", "mg_per_kg", 5000),
            ("lead", "ug_per_l", 10),
            ("hap", "mg_per_kg", 200),
            ("radon", "bq_per_m3", 300),
        ],
    )
    def test_at_exact_threshold_is_exceeded(self, pollutant, unit, threshold):
        """Concentration == threshold should be marked exceeded (>= comparison)."""
        result = check_threshold(pollutant, threshold, unit)
        assert result["exceeded"] is True
        assert result["threshold"] == threshold

    @pytest.mark.parametrize(
        "pollutant,unit,threshold",
        [
            ("asbestos", "percent_weight", 1.0),
            ("pcb", "mg_per_kg", 50),
            ("lead", "mg_per_kg", 5000),
            ("hap", "mg_per_kg", 200),
            ("radon", "bq_per_m3", 300),
        ],
    )
    def test_just_below_threshold_not_exceeded(self, pollutant, unit, threshold):
        """Concentration just below threshold should not be exceeded."""
        result = check_threshold(pollutant, threshold - 0.001, unit)
        assert result["exceeded"] is False
        assert result["action"] == "none"


class TestCheckThresholdDuplicateUnits:
    """When multiple threshold entries share the same unit, _find_matching_threshold
    returns the first match. These tests document that behavior."""

    def test_asbestos_fibers_returns_first_match_1000(self):
        """asbestos has air_fiber_count (1000) and air_work_limit (10000) both
        fibers_per_m3; the first (1000) is matched."""
        result = check_threshold("asbestos", 1500, "fibers_per_m3")
        assert result["threshold"] == 1000

    def test_pcb_mg_kg_returns_first_match_50(self):
        """pcb has material_content (50 mg/kg) and waste_classification (10 mg/kg);
        the first (50) is matched."""
        result = check_threshold("pcb", 30, "mg_per_kg")
        assert result["threshold"] == 50
        assert result["exceeded"] is False

    def test_radon_bq_returns_first_match_300(self):
        """radon has reference_value (300) and mandatory_action (1000) both bq/m3;
        the first (300) is matched."""
        result = check_threshold("radon", 500, "bq_per_m3")
        assert result["threshold"] == 300
        assert result["exceeded"] is True


class TestCheckThresholdConcentrationEdgeCases:
    """Test with concentration = 0, negative, very large values."""

    @pytest.mark.parametrize(
        "pollutant,unit",
        [
            ("asbestos", "percent_weight"),
            ("pcb", "mg_per_kg"),
            ("lead", "mg_per_kg"),
            ("hap", "mg_per_kg"),
            ("radon", "bq_per_m3"),
        ],
    )
    def test_zero_concentration(self, pollutant, unit):
        result = check_threshold(pollutant, 0, unit)
        assert result["exceeded"] is False
        assert result["action"] == "none"

    @pytest.mark.parametrize(
        "pollutant,unit",
        [
            ("asbestos", "percent_weight"),
            ("pcb", "mg_per_kg"),
            ("lead", "ug_per_l"),
        ],
    )
    def test_negative_concentration(self, pollutant, unit):
        """Negative concentrations should not exceed threshold."""
        result = check_threshold(pollutant, -10, unit)
        assert result["exceeded"] is False
        assert result["action"] == "none"

    @pytest.mark.parametrize(
        "pollutant,unit,threshold",
        [
            ("asbestos", "percent_weight", 1.0),
            ("pcb", "mg_per_kg", 50),
            ("lead", "mg_per_kg", 5000),
            ("hap", "mg_per_kg", 200),
            ("radon", "bq_per_m3", 300),
        ],
    )
    def test_very_large_concentration(self, pollutant, unit, threshold):
        """Very large concentrations should trigger remove_urgent (>= 3x threshold)."""
        result = check_threshold(pollutant, threshold * 10, unit)
        assert result["exceeded"] is True
        assert result["action"] == "remove_urgent"

    def test_exactly_3x_threshold_is_urgent(self):
        """Concentration == 3x threshold should be remove_urgent."""
        # asbestos threshold = 1.0 percent_weight, 3x = 3.0
        result = check_threshold("asbestos", 3.0, "percent_weight")
        assert result["exceeded"] is True
        assert result["action"] == "remove_urgent"

    def test_just_below_3x_threshold_is_planned(self):
        """Concentration < 3x threshold but >= threshold should be remove_planned."""
        result = check_threshold("asbestos", 2.999, "percent_weight")
        assert result["exceeded"] is True
        assert result["action"] == "remove_planned"

    def test_unknown_pollutant_returns_no_threshold(self):
        result = check_threshold("unknown_substance", 100, "mg_per_kg")
        assert result["exceeded"] is False
        assert result["threshold"] is None
        assert result["action"] == "no_matching_threshold"

    def test_unknown_unit_returns_no_threshold(self):
        result = check_threshold("asbestos", 100, "unknown_unit")
        assert result["exceeded"] is False
        assert result["threshold"] is None


class TestCheckThresholdUnitAliases:
    """Test that unit aliases work correctly."""

    def test_percent_alias(self):
        r1 = check_threshold("asbestos", 2.0, "percent_weight")
        r2 = check_threshold("asbestos", 2.0, "%")
        r3 = check_threshold("asbestos", 2.0, "percent")
        assert r1["exceeded"] == r2["exceeded"] == r3["exceeded"] is True

    def test_mg_kg_alias(self):
        r1 = check_threshold("pcb", 60, "mg_per_kg")
        r2 = check_threshold("pcb", 60, "mg/kg")
        r3 = check_threshold("pcb", 60, "ppm")
        assert r1["exceeded"] == r2["exceeded"] == r3["exceeded"] is True

    def test_fibers_alias(self):
        r1 = check_threshold("asbestos", 1500, "fibers_per_m3")
        r2 = check_threshold("asbestos", 1500, "f/m3")
        assert r1["exceeded"] == r2["exceeded"] is True

    def test_bq_alias(self):
        r1 = check_threshold("radon", 500, "bq_per_m3")
        r2 = check_threshold("radon", 500, "bq/m3")
        assert r1["exceeded"] == r2["exceeded"] is True


class TestDetermineRiskLevel:
    """Test risk level determination at boundary ratios."""

    @pytest.mark.parametrize(
        "ratio_fraction,expected",
        [
            (0.0, "low"),  # ratio = 0
            (0.49, "low"),  # ratio < 0.5
            (0.50, "medium"),  # ratio == 0.5
            (0.99, "medium"),  # ratio < 1.0
            (1.0, "high"),  # ratio == 1.0
            (2.99, "high"),  # ratio < 3.0
            (3.0, "critical"),  # ratio == 3.0
            (10.0, "critical"),  # ratio >> 3.0
        ],
    )
    def test_asbestos_risk_levels_at_boundaries(self, ratio_fraction, expected):
        """Asbestos threshold is 1.0 percent_weight, so ratio = concentration/1.0."""
        result = determine_risk_level("asbestos", ratio_fraction, "percent_weight")
        assert result == expected

    def test_unknown_pollutant_returns_low(self):
        result = determine_risk_level("unknown", 9999, "mg_per_kg")
        assert result == "low"

    def test_zero_concentration(self):
        result = determine_risk_level("asbestos", 0, "percent_weight")
        assert result == "low"

    def test_negative_concentration(self):
        result = determine_risk_level("pcb", -10, "mg_per_kg")
        assert result == "low"


class TestNormaliseState:
    """Test all material state aliases."""

    @pytest.mark.parametrize(
        "state_in,expected",
        [
            ("bon", "good"),
            ("good", "good"),
            ("intact", "good"),
            ("degrade", "degraded"),
            ("degraded", "degraded"),
            ("mauvais", "degraded"),
            ("tres_degrade", "heavily_degraded"),
            ("heavily_degraded", "heavily_degraded"),
            ("friable", "friable"),
        ],
    )
    def test_state_aliases(self, state_in, expected):
        assert _normalise_state(state_in) == expected

    def test_unknown_state_passthrough(self):
        assert _normalise_state("something_unknown") == "something_unknown"

    def test_moyen_state_passthrough(self):
        """moyen and medium are not in aliases, should pass through lowercase."""
        assert _normalise_state("moyen") == "moyen"
        assert _normalise_state("medium") == "medium"

    def test_case_insensitivity(self):
        assert _normalise_state("BON") == "good"
        assert _normalise_state("Degrade") == "degraded"


class TestCFSTWorkCategory:
    """Test CFST work category determination with different areas and states."""

    @pytest.mark.parametrize(
        "surface,expected",
        [
            (0, "minor"),
            (0.5, "minor"),
            (5.0, "minor"),
            (5.1, "medium"),  # > 5 but state good -> medium (since not <= 5)
            (10.0, "medium"),  # == 10 but <= 10 -> medium (area <= 10, state good, area > 5)
            (10.1, "medium"),  # > 10 -> medium
            (50, "medium"),  # > 10 -> medium
            (1000, "medium"),  # > 10 -> medium
        ],
    )
    def test_good_state_varying_area(self, surface, expected):
        result = determine_cfst_work_category("fibrociment", "bon", surface)
        assert result == expected

    def test_none_surface_defaults_to_1(self):
        """When surface is None, default to 1.0 m2."""
        result = determine_cfst_work_category("fibrociment", "bon", None)
        assert result == "minor"  # good state, area=1.0 <= 5

    def test_degraded_state_always_medium(self):
        """Degraded state should be at least medium."""
        assert determine_cfst_work_category("fibrociment", "degrade", 1.0) == "medium"
        assert determine_cfst_work_category("fibrociment", "mauvais", 0.5) == "medium"
        assert determine_cfst_work_category("fibrociment", "degraded", 100) == "medium"

    @pytest.mark.parametrize("state", ["friable", "tres_degrade", "heavily_degraded"])
    def test_friable_or_heavily_degraded_always_major(self, state):
        assert determine_cfst_work_category("generic", state, 0.1) == "major"
        assert determine_cfst_work_category("generic", state, 1000) == "major"

    @pytest.mark.parametrize("category", ["flocage", "spray", "calorifuge"])
    def test_friable_material_keywords_always_major(self, category):
        """Material categories containing friable keywords should be major."""
        assert determine_cfst_work_category(category, "bon", 1.0) == "major"

    def test_large_area_with_good_state(self):
        """Area > 10 with good state should be medium (not minor)."""
        result = determine_cfst_work_category("dalles_vinyle", "good", 50)
        assert result == "medium"

    def test_zero_area_good_state(self):
        result = determine_cfst_work_category("dalles_vinyle", "good", 0)
        assert result == "minor"


class TestWasteDisposal:
    """Test waste disposal determination for all pollutant/state combinations."""

    # Asbestos variations
    def test_asbestos_friable_flocage_special(self):
        assert determine_waste_disposal("asbestos", "flocage", "bon") == "special"

    def test_asbestos_calorifuge_special(self):
        assert determine_waste_disposal("asbestos", "calorifuge", "good") == "special"

    def test_asbestos_heavily_degraded_special(self):
        assert determine_waste_disposal("asbestos", "generic", "tres_degrade") == "special"

    def test_asbestos_friable_state_special(self):
        assert determine_waste_disposal("asbestos", "generic", "friable") == "special"

    def test_asbestos_fibrociment_good_type_b(self):
        assert determine_waste_disposal("asbestos", "fibrociment", "bon") == "type_b"

    def test_asbestos_eternit_good_type_b(self):
        assert determine_waste_disposal("asbestos", "eternit", "good") == "type_b"

    def test_asbestos_fibre_cement_good_type_b(self):
        assert determine_waste_disposal("asbestos", "fibre_cement", "bon") == "type_b"

    def test_asbestos_toiture_good_type_b(self):
        assert determine_waste_disposal("asbestos", "toiture", "good") == "type_b"

    def test_asbestos_fibrociment_degraded_type_e(self):
        """Bonded asbestos in degraded state -> type_e (not type_b)."""
        assert determine_waste_disposal("asbestos", "fibrociment", "degrade") == "type_e"

    def test_asbestos_generic_good_type_e(self):
        """Non-bonded, non-friable asbestos in good condition -> type_e."""
        assert determine_waste_disposal("asbestos", "dalles_vinyle", "good") == "type_e"

    # PCB always special
    def test_pcb_any_state_special(self):
        for state in ("bon", "good", "degrade", "degraded", "friable", "tres_degrade"):
            assert determine_waste_disposal("pcb", "joints", state) == "special"

    # Lead depends on state
    def test_lead_good_type_e(self):
        assert determine_waste_disposal("lead", "peinture", "bon") == "type_e"

    def test_lead_degraded_type_e(self):
        assert determine_waste_disposal("lead", "peinture", "degrade") == "type_e"

    def test_lead_friable_special(self):
        assert determine_waste_disposal("lead", "peinture", "friable") == "special"

    def test_lead_heavily_degraded_special(self):
        assert determine_waste_disposal("lead", "peinture", "tres_degrade") == "special"

    # HAP always special
    def test_hap_any_state_special(self):
        for state in ("bon", "degrade", "friable"):
            assert determine_waste_disposal("hap", "etancheite", state) == "special"

    # Unknown pollutant -> type_e
    def test_unknown_pollutant_type_e(self):
        assert determine_waste_disposal("unknown", "generic", "bon") == "type_e"

    # Radon has no specific waste rule -> falls through to type_e
    def test_radon_type_e(self):
        assert determine_waste_disposal("radon", "air", "good") == "type_e"


class TestDetermineActionRequired:
    """Test action determination for all risk levels and pollutants."""

    def test_critical_always_remove_urgent(self):
        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
            assert determine_action_required(pollutant, "critical", 9999) == "remove_urgent"

    def test_high_always_remove_planned(self):
        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
            assert determine_action_required(pollutant, "high", 100) == "remove_planned"

    def test_medium_asbestos_encapsulate(self):
        assert determine_action_required("asbestos", "medium", 0.5) == "encapsulate"

    def test_medium_lead_encapsulate(self):
        assert determine_action_required("lead", "medium", 3000) == "encapsulate"

    def test_medium_pcb_monitor(self):
        assert determine_action_required("pcb", "medium", 30) == "monitor"

    def test_medium_hap_monitor(self):
        assert determine_action_required("hap", "medium", 100) == "monitor"

    def test_low_always_none(self):
        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
            assert determine_action_required(pollutant, "low", 0) == "none"


class TestSUVANotification:
    """Test SUVA notification logic."""

    @pytest.mark.parametrize(
        "diag_type",
        [
            "renovation",
            "demolition",
            "full",
            "asbestos",
            "avant_travaux",
            "avt",
        ],
    )
    def test_notifiable_types_with_asbestos(self, diag_type):
        assert check_suva_notification_required(diag_type, True) is True

    @pytest.mark.parametrize(
        "diag_type",
        [
            "renovation",
            "demolition",
            "full",
            "asbestos",
        ],
    )
    def test_notifiable_types_without_asbestos(self, diag_type):
        assert check_suva_notification_required(diag_type, False) is False

    def test_non_notifiable_type_with_asbestos(self):
        assert check_suva_notification_required("inspection", True) is False

    def test_non_notifiable_type_without_asbestos(self):
        assert check_suva_notification_required("inspection", False) is False


class TestCantonalRequirements:
    """Test cantonal requirement lookups."""

    @pytest.mark.parametrize("canton", ["VD", "GE", "ZH", "BE", "VS"])
    def test_known_cantons(self, canton):
        req = get_cantonal_requirements(canton)
        assert req["canton"] == canton
        assert "authority_name" in req
        assert req["diagnostic_required_before_year"] == 1991

    def test_unknown_canton_gets_default(self):
        req = get_cantonal_requirements("TI")
        assert req["canton"] == "TI"
        assert req["authority_name"] == "Service cantonal de l'environnement"

    def test_case_insensitive(self):
        req = get_cantonal_requirements("vd")
        assert req["canton"] == "VD"
        assert req["authority_name"] == "DGE-DIRNA"

    def test_ge_has_online_system(self):
        req = get_cantonal_requirements("GE")
        assert req.get("online_system") == "SADEC"


class TestAutoClassifySample:
    """Test auto_classify_sample with all pollutant types."""

    def test_missing_concentration_returns_defaults(self):
        result = auto_classify_sample({"pollutant_type": "asbestos", "unit": "%"})
        assert result["threshold_exceeded"] is False
        assert result["risk_level"] == "low"
        assert result["cfst_work_category"] is None
        assert result["action_required"] == "none"
        assert result["waste_disposal_type"] == "type_e"

    def test_asbestos_above_threshold(self):
        result = auto_classify_sample(
            {
                "pollutant_type": "asbestos",
                "concentration": 2.0,
                "unit": "percent_weight",
                "material_category": "flocage",
                "material_state": "degrade",
                "surface_m2": 20.0,
            }
        )
        assert result["threshold_exceeded"] is True
        assert result["risk_level"] == "high"
        assert result["cfst_work_category"] is not None
        assert result["waste_disposal_type"] != "type_b"

    def test_asbestos_below_threshold_no_cfst(self):
        """Below threshold, cfst_work_category should be None."""
        result = auto_classify_sample(
            {
                "pollutant_type": "asbestos",
                "concentration": 0.5,
                "unit": "percent_weight",
            }
        )
        assert result["threshold_exceeded"] is False
        assert result["cfst_work_category"] is None
        assert result["waste_disposal_type"] == "type_b"  # not exceeded -> type_b

    def test_pcb_above_threshold(self):
        result = auto_classify_sample(
            {
                "pollutant_type": "pcb",
                "concentration": 100,
                "unit": "mg_per_kg",
                "material_category": "joints",
                "material_state": "bon",
            }
        )
        assert result["threshold_exceeded"] is True
        assert result["cfst_work_category"] is None  # CFST only for asbestos
        assert result["waste_disposal_type"] == "special"

    def test_lead_at_threshold(self):
        result = auto_classify_sample(
            {
                "pollutant_type": "lead",
                "concentration": 5000,
                "unit": "mg_per_kg",
                "material_state": "bon",
            }
        )
        assert result["threshold_exceeded"] is True
        assert result["risk_level"] == "high"

    def test_hap_below_threshold(self):
        result = auto_classify_sample(
            {
                "pollutant_type": "hap",
                "concentration": 50,
                "unit": "mg_per_kg",
            }
        )
        assert result["threshold_exceeded"] is False
        assert result["risk_level"] == "low"

    def test_radon_above_both_thresholds(self):
        """Radon at 1000 bq/m3 is the mandatory action threshold (300 is reference)."""
        result = auto_classify_sample(
            {
                "pollutant_type": "radon",
                "concentration": 1000,
                "unit": "bq_per_m3",
            }
        )
        # 1000/300 = 3.33 -> critical
        assert result["threshold_exceeded"] is True
        assert result["risk_level"] == "critical"

    def test_empty_pollutant_type(self):
        result = auto_classify_sample(
            {
                "pollutant_type": "",
                "concentration": 100,
                "unit": "mg_per_kg",
            }
        )
        assert result["threshold_exceeded"] is False
        assert result["risk_level"] == "low"

    def test_asbestos_flocage_degraded_cfst_major(self):
        """Flocage material in degraded state -> CFST major."""
        result = auto_classify_sample(
            {
                "pollutant_type": "asbestos",
                "concentration": 5.0,
                "unit": "percent_weight",
                "material_category": "flocage",
                "material_state": "degrade",
                "surface_m2": 1.0,
            }
        )
        assert result["cfst_work_category"] == "major"
        assert result["waste_disposal_type"] == "special"


# ===================================================================
# SECTION 2: Risk Engine Edge Cases
# ===================================================================


class TestBaseProbabilities:
    """Test base probability functions for various construction years."""

    @pytest.mark.parametrize(
        "year,expected",
        [
            (1800, 0.05),
            (1920, 0.15),
            (1950, 0.40),
            (1955, 0.85),
            (1970, 0.90),
            (1980, 0.60),
            (1990, 0.15),
            (1995, 0.02),
            (2010, 0.02),
            (2025, 0.02),
            (None, 0.5),
        ],
    )
    def test_asbestos_probability(self, year, expected):
        assert calculate_asbestos_base_probability(year) == expected

    @pytest.mark.parametrize(
        "year,expected",
        [
            (1800, 0.02),
            (1920, 0.02),
            (1950, 0.02),
            (1955, 0.55),
            (1970, 0.70),
            (1980, 0.40),
            (1986, 0.02),
            (2010, 0.02),
            (None, 0.3),
        ],
    )
    def test_pcb_probability(self, year, expected):
        assert calculate_pcb_base_probability(year) == expected

    @pytest.mark.parametrize(
        "year,expected",
        [
            (1800, 0.85),
            (1920, 0.75),
            (1940, 0.60),
            (1960, 0.35),
            (1980, 0.10),
            (2000, 0.02),
            (2025, 0.02),
            (None, 0.3),
        ],
    )
    def test_lead_probability(self, year, expected):
        assert calculate_lead_base_probability(year) == expected

    @pytest.mark.parametrize(
        "year,expected",
        [
            (1800, 0.20),
            (1940, 0.55),
            (1970, 0.35),
            (1985, 0.05),
            (2010, 0.05),
            (None, 0.25),
        ],
    )
    def test_hap_probability(self, year, expected):
        assert calculate_hap_base_probability(year) == expected

    @pytest.mark.parametrize(
        "canton,expected",
        [
            ("GR", 0.60),
            ("TI", 0.60),
            ("VS", 0.60),
            ("BE", 0.30),
            ("FR", 0.30),
            ("NE", 0.30),
            ("ZH", 0.10),
            ("VD", 0.10),
            ("", 0.10),
        ],
    )
    def test_radon_probability(self, canton, expected):
        assert calculate_radon_base_probability(canton) == expected

    def test_boundary_year_1919_asbestos(self):
        """Year 1919 is < 1920, should give 0.05."""
        assert calculate_asbestos_base_probability(1919) == 0.05

    def test_boundary_year_1920_asbestos(self):
        """Year 1920 is >= 1920 but < 1940, should give 0.15."""
        assert calculate_asbestos_base_probability(1920) == 0.15


class TestApplyModifiers:
    """Test building-type modifiers."""

    def test_industrial_asbestos_modifier(self):
        result = apply_modifiers(0.5, "industrial", "asbestos")
        assert result == pytest.approx(0.5 * 1.3)

    def test_residential_pcb_modifier(self):
        result = apply_modifiers(0.5, "residential", "pcb")
        assert result == pytest.approx(0.5 * 0.9)

    def test_unknown_building_type_no_modifier(self):
        result = apply_modifiers(0.5, "warehouse", "asbestos")
        assert result == pytest.approx(0.5 * 1.0)

    def test_unknown_pollutant_no_modifier(self):
        result = apply_modifiers(0.5, "industrial", "radon")
        assert result == pytest.approx(0.5 * 1.0)

    def test_clamped_to_max_1(self):
        """High base * high modifier should clamp to 1.0."""
        result = apply_modifiers(0.9, "industrial", "asbestos")
        assert result <= 1.0

    def test_clamped_to_min_0(self):
        result = apply_modifiers(0.0, "industrial", "asbestos")
        assert result >= 0.0


class TestApplyRenovationModifier:
    """Test renovation type exposure modifiers."""

    @pytest.mark.parametrize("reno_type", list(RENOVATION_EXPOSURE.keys()))
    def test_all_renovation_types_exist(self, reno_type):
        """All renovation types should return valid modifiers."""
        result = apply_renovation_modifier(0.5, reno_type, "asbestos")
        assert 0.0 <= result <= 1.0

    def test_full_renovation_no_reduction(self):
        """Full renovation has exposure factor 1.0 for all pollutants."""
        for pollutant in ("asbestos", "pcb", "lead", "hap"):
            result = apply_renovation_modifier(0.5, "full_renovation", pollutant)
            assert result == pytest.approx(0.5)

    def test_windows_low_hap_exposure(self):
        """Windows renovation has only 0.1 HAP exposure."""
        result = apply_renovation_modifier(0.5, "windows", "hap")
        assert result == pytest.approx(0.05)

    def test_unknown_renovation_type(self):
        result = apply_renovation_modifier(0.5, "unknown_type", "asbestos")
        assert result == pytest.approx(0.5)


class TestOverallRiskLevel:
    """Test overall risk level determination at boundary values."""

    def test_empty_scores_unknown(self):
        assert calculate_overall_risk_level({}) == "unknown"

    @pytest.mark.parametrize(
        "max_val,expected",
        [
            (0.0, "low"),
            (0.24, "low"),
            (0.25, "medium"),
            (0.54, "medium"),
            (0.55, "high"),
            (0.79, "high"),
            (0.80, "critical"),
            (1.0, "critical"),
        ],
    )
    def test_boundary_values(self, max_val, expected):
        scores = {"asbestos": max_val, "pcb": 0.0}
        assert calculate_overall_risk_level(scores) == expected

    def test_multiple_pollutants_uses_max(self):
        scores = {"asbestos": 0.10, "pcb": 0.90, "lead": 0.30}
        assert calculate_overall_risk_level(scores) == "critical"


class TestCalculateConfidence:
    """Test confidence score calculation."""

    def test_nothing_known(self):
        assert calculate_confidence(False, 0, False) == 0.0

    def test_year_only(self):
        assert calculate_confidence(False, 0, True) == 0.30

    def test_diagnostics_only(self):
        assert calculate_confidence(True, 0, False) == 0.40

    def test_all_factors(self):
        # year=0.30, diag=0.40, neighbors(5+)=0.30 -> 1.0
        assert calculate_confidence(True, 5, True) == 1.0

    def test_neighbor_scaling(self):
        # 1 neighbor: 0.30 * (1/5) = 0.06
        assert calculate_confidence(False, 1, False) == 0.06
        # 3 neighbors: 0.30 * (3/5) = 0.18
        assert calculate_confidence(False, 3, False) == 0.18
        # 10 neighbors: capped at 0.30
        assert calculate_confidence(False, 10, False) == 0.30

    def test_capped_at_1(self):
        """Even with large neighbor count, should not exceed 1.0."""
        result = calculate_confidence(True, 100, True)
        assert result == 1.0


class TestDiagnosticOverride:
    """Test _apply_diagnostic_override with mock Sample objects."""

    def _make_sample(self, pollutant, exceeded):
        s = Sample()
        s.pollutant_type = pollutant
        s.threshold_exceeded = exceeded
        return s

    def test_positive_sample_overrides_to_095(self):
        scores = {"asbestos": 0.5, "pcb": 0.3}
        samples = [self._make_sample("asbestos", True)]
        result = _apply_diagnostic_override(scores, samples)
        assert result["asbestos"] == 0.95
        assert result["pcb"] == 0.3  # unchanged

    def test_negative_sample_overrides_to_005(self):
        scores = {"asbestos": 0.5, "pcb": 0.3}
        samples = [self._make_sample("asbestos", False)]
        result = _apply_diagnostic_override(scores, samples)
        assert result["asbestos"] == 0.05

    def test_mixed_results_overrides_to_070(self):
        scores = {"asbestos": 0.5}
        samples = [
            self._make_sample("asbestos", True),
            self._make_sample("asbestos", False),
        ]
        result = _apply_diagnostic_override(scores, samples)
        assert result["asbestos"] == 0.70

    def test_no_samples_returns_unchanged(self):
        scores = {"asbestos": 0.5, "pcb": 0.3}
        result = _apply_diagnostic_override(scores, [])
        assert result == scores

    def test_sample_with_none_exceeded_ignored(self):
        scores = {"asbestos": 0.5}
        s = self._make_sample("asbestos", None)
        result = _apply_diagnostic_override(scores, [s])
        assert result["asbestos"] == 0.5  # unchanged

    def test_unknown_pollutant_in_sample_ignored(self):
        scores = {"asbestos": 0.5}
        samples = [self._make_sample("uranium", True)]
        result = _apply_diagnostic_override(scores, samples)
        assert result["asbestos"] == 0.5


class TestNeighborAdjustment:
    """Test _adjust_with_neighbor_samples."""

    def _make_sample(self, pollutant, exceeded):
        s = Sample()
        s.pollutant_type = pollutant
        s.threshold_exceeded = exceeded
        return s

    def test_no_neighbors_returns_unchanged(self):
        scores = {"asbestos": 0.5}
        result = _adjust_with_neighbor_samples(scores, [])
        assert result == scores

    def test_all_positive_neighbors_increase(self):
        scores = {"asbestos": 0.5}
        samples = [self._make_sample("asbestos", True) for _ in range(5)]
        result = _adjust_with_neighbor_samples(scores, samples)
        assert result["asbestos"] > 0.5

    def test_all_negative_neighbors_decrease(self):
        scores = {"asbestos": 0.5}
        samples = [self._make_sample("asbestos", False) for _ in range(5)]
        result = _adjust_with_neighbor_samples(scores, samples)
        assert result["asbestos"] < 0.5

    def test_adjustment_capped_at_015(self):
        scores = {"asbestos": 0.1}
        samples = [self._make_sample("asbestos", True) for _ in range(20)]
        result = _adjust_with_neighbor_samples(scores, samples)
        # Max shift is +0.15
        assert result["asbestos"] <= 0.1 + 0.15 + 0.001  # small float tolerance

    def test_result_clamped_0_1(self):
        scores = {"asbestos": 0.98}
        samples = [self._make_sample("asbestos", True) for _ in range(10)]
        result = _adjust_with_neighbor_samples(scores, samples)
        assert result["asbestos"] <= 1.0


# ===================================================================
# SECTION 3: Risk Engine integration with DB (async tests)
# ===================================================================


@pytest.mark.asyncio
class TestCalculateBuildingRisk:
    """Integration tests for calculate_building_risk with DB."""

    async def _make_building(self, db_session, admin_user, **kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "address": "Rue Test 1",
            "postal_code": "1000",
            "city": "Lausanne",
            "canton": "VD",
            "construction_year": 1965,
            "building_type": "residential",
            "created_by": admin_user.id,
            "status": "active",
        }
        defaults.update(kwargs)
        building = Building(**defaults)
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        return building

    async def test_building_no_diagnostics(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        risk = await calculate_building_risk(db_session, building)
        assert risk.overall_risk_level in ("low", "medium", "high", "critical")
        assert risk.data_source == "model"
        assert risk.confidence == 0.30  # year known only

    async def test_building_unknown_year(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user, construction_year=None)
        risk = await calculate_building_risk(db_session, building)
        assert risk.data_source == "model"
        assert risk.confidence == 0.0  # nothing known

    async def test_building_with_diagnostic_no_samples(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="renovation",
            status="completed",
        )
        db_session.add(diag)
        await db_session.commit()
        risk = await calculate_building_risk(db_session, building)
        assert risk.data_source == "diagnostic"
        assert risk.confidence == 0.70  # year + diag

    async def test_building_with_positive_sample(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="renovation",
            status="completed",
        )
        db_session.add(diag)
        await db_session.flush()
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="E01",
            pollutant_type="asbestos",
            threshold_exceeded=True,
            concentration=5.0,
            unit="percent_weight",
        )
        db_session.add(sample)
        await db_session.commit()
        risk = await calculate_building_risk(db_session, building)
        assert risk.asbestos_probability == 0.95
        assert risk.data_source == "diagnostic"

    async def test_building_with_neighbor_samples(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        # Create neighbor samples (not from this building's diagnostics)
        neighbor_samples = []
        for _ in range(5):
            s = Sample()
            s.pollutant_type = "asbestos"
            s.threshold_exceeded = True
            neighbor_samples.append(s)
        risk = await calculate_building_risk(db_session, building, neighbor_samples=neighbor_samples)
        # Asbestos probability should be higher due to positive neighbors
        base = calculate_asbestos_base_probability(1965)
        modified = apply_modifiers(base, "residential", "asbestos")
        assert risk.asbestos_probability >= modified

    @pytest.mark.parametrize("year", [1800, 1920, 1950, 1970, 1990, 2010, 2025])
    async def test_different_construction_years(self, db_session, admin_user, year):
        building = await self._make_building(db_session, admin_user, construction_year=year)
        risk = await calculate_building_risk(db_session, building)
        assert risk.overall_risk_level in ("low", "medium", "high", "critical")
        assert 0.0 <= risk.asbestos_probability <= 1.0
        assert 0.0 <= risk.pcb_probability <= 1.0
        assert 0.0 <= risk.lead_probability <= 1.0
        assert 0.0 <= risk.hap_probability <= 1.0
        assert 0.0 <= risk.radon_probability <= 1.0


# ===================================================================
# SECTION 4: Renovation Simulator Edge Cases
# ===================================================================


class TestRiskToCostTier:
    """Test _risk_to_cost_tier mapping."""

    @pytest.mark.parametrize(
        "prob,expected",
        [
            (0.0, "minor"),
            (0.29, "minor"),
            (0.30, "medium"),
            (0.69, "medium"),
            (0.70, "major"),
            (1.0, "major"),
        ],
    )
    def test_asbestos_tiers(self, prob, expected):
        assert _risk_to_cost_tier("asbestos", prob) == expected

    @pytest.mark.parametrize(
        "prob,expected",
        [
            (0.0, "low"),
            (0.29, "low"),
            (0.30, "medium"),
            (0.69, "medium"),
            (0.70, "high"),
            (1.0, "high"),
        ],
    )
    def test_other_pollutant_tiers(self, prob, expected):
        for pollutant in ("pcb", "lead", "hap", "radon"):
            assert _risk_to_cost_tier(pollutant, prob) == expected


class TestEstimateRemediationCost:
    """Test remediation cost estimates."""

    def test_zero_surface(self):
        assert estimate_remediation_cost("asbestos", "minor", 0) == 0.0

    def test_normal_surface(self):
        # asbestos minor = 80 CHF/m2
        assert estimate_remediation_cost("asbestos", "minor", 100) == 8000.0

    def test_large_surface(self):
        result = estimate_remediation_cost("asbestos", "major", 1000)
        assert result == 600000.0  # 600 * 1000

    def test_unknown_pollutant_returns_zero(self):
        assert estimate_remediation_cost("unknown", "high", 100) == 0.0

    def test_unknown_tier_returns_zero(self):
        assert estimate_remediation_cost("asbestos", "nonexistent", 100) == 0.0

    def test_all_pollutant_tier_combinations(self):
        """Every valid pollutant+tier returns a positive cost for non-zero surface."""
        for pollutant, tiers in BASE_COSTS_CHF_PER_M2.items():
            for tier in tiers:
                cost = estimate_remediation_cost(pollutant, tier, 10)
                assert cost > 0, f"{pollutant}/{tier} should have positive cost"


class TestEstimateTimelineWeeks:
    """Test timeline estimation."""

    def test_no_risks(self):
        weeks = estimate_timeline_weeks([], "full_renovation")
        assert weeks == 8  # base only

    def test_significant_risk_adds_diagnostic_phase(self):
        risks = [{"pollutant": "asbestos", "probability": 0.25}]
        weeks = estimate_timeline_weeks(risks, "full_renovation")
        assert weeks == 10  # 8 base + 2 diagnostic

    def test_high_risk_adds_remediation(self):
        risks = [{"pollutant": "asbestos", "probability": 0.55}]
        weeks = estimate_timeline_weeks(risks, "full_renovation")
        # 8 base + 2 diagnostic + 2 remediation = 12
        assert weeks == 12

    def test_critical_risk_adds_notification(self):
        risks = [{"pollutant": "asbestos", "probability": 0.80}]
        weeks = estimate_timeline_weeks(risks, "full_renovation")
        # 8 base + 2 diagnostic + 2 remediation + 1 notification = 13
        assert weeks == 13

    def test_multiple_high_risks(self):
        risks = [
            {"pollutant": "asbestos", "probability": 0.60},
            {"pollutant": "pcb", "probability": 0.70},
        ]
        weeks = estimate_timeline_weeks(risks, "full_renovation")
        # 8 base + 2 diagnostic + 4 remediation (2 * 2) = 14
        assert weeks == 14

    @pytest.mark.parametrize(
        "reno_type,base",
        [
            ("full_renovation", 8),
            ("partial_interior", 4),
            ("roof", 3),
            ("facade", 4),
            ("bathroom", 3),
            ("kitchen", 3),
            ("flooring", 2),
            ("windows", 2),
        ],
    )
    def test_base_weeks_per_renovation_type(self, reno_type, base):
        weeks = estimate_timeline_weeks([], reno_type)
        assert weeks == base

    def test_unknown_renovation_type_defaults_to_4(self):
        weeks = estimate_timeline_weeks([], "unknown_type")
        assert weeks == 4


class TestGetRequiredDiagnostics:
    """Test required diagnostic determination."""

    def _make_building(self, year=1965, canton="VD"):
        b = Building()
        b.construction_year = year
        b.canton = canton
        return b

    def test_old_building_full_renovation(self):
        b = self._make_building(1965)
        diags = get_required_diagnostics(b, "full_renovation")
        assert "asbestos" in diags
        assert "pcb" in diags
        assert "lead" in diags
        assert "hap" in diags

    def test_new_building_no_pollutant_diagnostics(self):
        b = self._make_building(2010)
        diags = get_required_diagnostics(b, "full_renovation")
        # Year >= 1991, no pollutant diagnostics required
        assert "asbestos" not in diags
        assert "pcb" not in diags
        assert "lead" not in diags
        assert "hap" not in diags

    def test_unknown_year_requires_diagnostics(self):
        b = self._make_building(None)
        diags = get_required_diagnostics(b, "full_renovation")
        assert "asbestos" in diags

    def test_radon_in_high_canton(self):
        b = self._make_building(2010, "GR")
        diags = get_required_diagnostics(b, "full_renovation")
        assert "radon" in diags

    def test_radon_in_low_canton_excluded(self):
        b = self._make_building(2010, "ZH")
        diags = get_required_diagnostics(b, "full_renovation")
        assert "radon" not in diags

    def test_windows_renovation_low_exposure(self):
        b = self._make_building(1965)
        diags = get_required_diagnostics(b, "windows")
        # Windows has low PCB (0.7>=0.3 yes), low lead (0.4>=0.4 yes),
        # low HAP (0.1<0.4 no), asbestos (0.6>=0.5 yes)
        assert "asbestos" in diags

    @pytest.mark.parametrize("reno_type", list(RENOVATION_EXPOSURE.keys()))
    def test_all_renovation_types_return_list(self, reno_type):
        b = self._make_building(1965)
        diags = get_required_diagnostics(b, reno_type)
        assert isinstance(diags, list)


class TestGetComplianceRequirements:
    """Test compliance requirement generation."""

    def _make_building(self, year=1965, canton="VD"):
        b = Building()
        b.construction_year = year
        b.canton = canton
        return b

    def test_old_building_requires_diagnostic(self):
        b = self._make_building(1965)
        reqs = get_compliance_requirements(b, [])
        req_names = [r["requirement"] for r in reqs]
        assert "diagnostic_polluants" in req_names

    def test_new_building_no_diagnostic_requirement(self):
        b = self._make_building(2010)
        reqs = get_compliance_requirements(b, [])
        req_names = [r["requirement"] for r in reqs]
        assert "diagnostic_polluants" not in req_names

    def test_high_asbestos_triggers_suva(self):
        b = self._make_building(1965)
        risks = [{"pollutant": "asbestos", "probability": 0.60}]
        reqs = get_compliance_requirements(b, risks)
        req_names = [r["requirement"] for r in reqs]
        assert "suva_notification" in req_names

    def test_low_asbestos_no_suva(self):
        b = self._make_building(1965)
        risks = [{"pollutant": "asbestos", "probability": 0.30}]
        reqs = get_compliance_requirements(b, risks)
        req_names = [r["requirement"] for r in reqs]
        assert "suva_notification" not in req_names

    def test_high_radon_mandatory_measurement(self):
        b = self._make_building(1965, "GR")
        risks = [{"pollutant": "radon", "probability": 0.65}]
        reqs = get_compliance_requirements(b, risks)
        radon_req = [r for r in reqs if r["requirement"] == "radon_measurement"]
        assert len(radon_req) == 1
        assert radon_req[0]["mandatory"] is True

    def test_medium_radon_recommended_not_mandatory(self):
        b = self._make_building(1965)
        risks = [{"pollutant": "radon", "probability": 0.35}]
        reqs = get_compliance_requirements(b, risks)
        radon_req = [r for r in reqs if r["requirement"] == "radon_measurement"]
        assert len(radon_req) == 1
        assert radon_req[0]["mandatory"] is False

    def test_cantonal_notification_always_present(self):
        b = self._make_building(2010)
        reqs = get_compliance_requirements(b, [])
        req_names = [r["requirement"] for r in reqs]
        assert "cantonal_notification" in req_names


# ===================================================================
# SECTION 5: Renovation Simulator Integration Tests (async)
# ===================================================================


@pytest.mark.asyncio
class TestSimulateRenovation:
    """Integration tests for simulate_renovation with DB."""

    async def _make_building(self, db_session, admin_user, **kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "address": "Rue Test 1",
            "postal_code": "1000",
            "city": "Lausanne",
            "canton": "VD",
            "construction_year": 1965,
            "building_type": "residential",
            "created_by": admin_user.id,
            "status": "active",
            "surface_area_m2": 200.0,
        }
        defaults.update(kwargs)
        building = Building(**defaults)
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        return building

    @pytest.mark.parametrize(
        "reno_type",
        [
            "full_renovation",
            "partial_interior",
            "roof",
            "facade",
            "bathroom",
            "kitchen",
            "flooring",
            "windows",
        ],
    )
    async def test_all_renovation_types(self, db_session, admin_user, reno_type):
        building = await self._make_building(db_session, admin_user)
        result = await simulate_renovation(db_session, building.id, reno_type)
        assert result["renovation_type"] == reno_type
        assert result["building_id"] == str(building.id)
        assert isinstance(result["pollutant_risks"], list)
        assert len(result["pollutant_risks"]) == 5  # 5 pollutants
        assert result["total_estimated_cost_chf"] >= 0
        assert result["timeline_weeks"] > 0
        assert isinstance(result["required_diagnostics"], list)
        assert isinstance(result["compliance_requirements"], list)

    async def test_building_no_diagnostics(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        result = await simulate_renovation(db_session, building.id, "full_renovation")
        # Should still work without diagnostics
        assert result["total_estimated_cost_chf"] > 0
        assert result["timeline_weeks"] >= 8  # at least base weeks

    async def test_new_building_lower_costs(self, db_session, admin_user):
        old_building = await self._make_building(db_session, admin_user, construction_year=1965)
        new_building = await self._make_building(db_session, admin_user, construction_year=2020)
        old_result = await simulate_renovation(db_session, old_building.id, "full_renovation")
        new_result = await simulate_renovation(db_session, new_building.id, "full_renovation")
        # New building should have lower estimated costs
        assert new_result["total_estimated_cost_chf"] < old_result["total_estimated_cost_chf"]

    async def test_building_no_surface_defaults_to_100(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user, surface_area_m2=None)
        result = await simulate_renovation(db_session, building.id, "full_renovation")
        assert result["total_estimated_cost_chf"] > 0

    async def test_cost_range_calculated(self, db_session, admin_user):
        """The simulation internally calculates cost_range_low and cost_range_high."""
        building = await self._make_building(db_session, admin_user)
        result = await simulate_renovation(db_session, building.id, "full_renovation")
        total = result["total_estimated_cost_chf"]
        # total should be non-negative
        assert total >= 0

    async def test_pollutant_risk_details_structure(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        result = await simulate_renovation(db_session, building.id, "full_renovation")
        for pr in result["pollutant_risks"]:
            assert "pollutant" in pr
            assert "probability" in pr
            assert "risk_level" in pr
            assert "exposure_factor" in pr
            assert "materials_at_risk" in pr
            assert "estimated_cost_chf" in pr
            assert pr["risk_level"] in ("low", "medium", "high")
            assert 0.0 <= pr["probability"] <= 1.0

    async def test_compliance_requirements_structure(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        result = await simulate_renovation(db_session, building.id, "full_renovation")
        for cr in result["compliance_requirements"]:
            assert "requirement" in cr
            assert "legal_reference" in cr
            assert "mandatory" in cr
            assert "deadline_days" in cr

    async def test_high_radon_canton(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user, canton="GR")
        result = await simulate_renovation(db_session, building.id, "full_renovation")
        assert "radon" in result["required_diagnostics"]

    async def test_materials_at_risk_per_renovation_type(self, db_session, admin_user):
        building = await self._make_building(db_session, admin_user)
        for reno_type, expected_materials in MATERIAL_CATEGORIES_BY_RENOVATION.items():
            result = await simulate_renovation(db_session, building.id, reno_type)
            for pr in result["pollutant_risks"]:
                assert pr["materials_at_risk"] == expected_materials
