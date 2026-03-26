"""Tests for building enrichment layer 2: lifecycle, renovation, compliance, financial, narrative.

All functions are pure computation — no DB or API calls needed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.building_enrichment_service import (
    COMPONENT_LIFESPANS,
    COMPONENT_NAMES_FR,
    compute_component_lifecycle,
    compute_regulatory_compliance,
    estimate_financial_impact,
    generate_building_narrative,
    generate_renovation_plan,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CURRENT_YEAR = datetime.now(UTC).year


@pytest.fixture()
def old_building_data():
    """Pre-1970 building with fossil heating."""
    return {
        "construction_year": 1965,
        "renovation_year": None,
        "building_type": "residential",
        "surface_area_m2": 500,
        "floors_above": 5,
        "floors": 5,
        "dwellings": 10,
        "has_elevator": False,
        "heating_type": "mazout",
        "canton": "VD",
        "address": "Rue du Test 1",
        "city": "Lausanne",
    }


@pytest.fixture()
def modern_building_data():
    """Post-2015 building."""
    return {
        "construction_year": 2018,
        "renovation_year": None,
        "building_type": "residential",
        "surface_area_m2": 300,
        "floors_above": 3,
        "floors": 3,
        "dwellings": 6,
        "has_elevator": True,
        "heating_type": "heatpump",
        "canton": "GE",
        "address": "Chemin Moderne 5",
        "city": "Geneve",
    }


@pytest.fixture()
def renovated_building_data():
    """Old building renovated in 2010."""
    return {
        "construction_year": 1975,
        "renovation_year": 2010,
        "building_type": "mixed",
        "surface_area_m2": 400,
        "floors_above": 4,
        "dwellings": 8,
        "has_elevator": True,
        "heating_type": "gas",
        "canton": "VD",
        "address": "Avenue Renovee 3",
        "city": "Lausanne",
    }


@pytest.fixture()
def enrichment_with_risks():
    """Enrichment data with high pollutant risk + noise."""
    return {
        "pollutant_risk": {
            "asbestos_probability": 0.85,
            "pcb_probability": 0.60,
            "lead_probability": 0.70,
            "overall_risk_score": 0.65,
        },
        "noise": {"road_noise_day_db": 68},
        "railway_noise": {"railway_noise_day_db": 55},
        "radon": {"radon_level": "medium"},
        "natural_hazards": {"flood_risk": "low"},
        "heritage": {"isos_protected": False},
        "solar": {"suitability": "high"},
        "thermal_networks": {"has_district_heating": True},
        "water_protection": {"in_protection_zone": False},
        "groundwater_zones": {"in_protection_zone": False},
        "accessibility": {"compliance_status": "full_compliance_required"},
        "subsidies": {"total_estimated_chf": 20000},
        "neighborhood_score": 6.5,
    }


# ---------------------------------------------------------------------------
# 1. Component lifecycle prediction
# ---------------------------------------------------------------------------


class TestComponentLifecycle:
    def test_old_building_has_overdue_components(self, old_building_data):
        result = compute_component_lifecycle(old_building_data)
        assert "components" in result
        assert len(result["components"]) == len(COMPONENT_LIFESPANS)
        # 1965 building: many components should be overdue after 60+ years
        overdue = [c for c in result["components"] if c["status"] == "overdue"]
        assert len(overdue) > 0
        assert result["total_overdue_years"] > 0

    def test_modern_building_no_overdue(self, modern_building_data):
        result = compute_component_lifecycle(modern_building_data)
        statuses = {c["status"] for c in result["components"]}
        # 2018 building: 8 years old — no component should be end_of_life or overdue
        assert "overdue" not in statuses
        assert "end_of_life" not in statuses
        assert result["critical_count"] == 0
        assert result["urgent_count"] == 0
        assert result["total_overdue_years"] == 0

    def test_renovated_building_uses_renovation_year(self, renovated_building_data):
        result = compute_component_lifecycle(renovated_building_data)
        for comp in result["components"]:
            assert comp["installed_year"] == 2010  # renovation_year > construction_year

    def test_no_construction_year_returns_unknown(self):
        result = compute_component_lifecycle({"construction_year": None})
        for comp in result["components"]:
            assert comp["status"] == "unknown"
            assert comp["urgency"] == "none"

    def test_all_component_names_have_french(self):
        for name in COMPONENT_LIFESPANS:
            assert name in COMPONENT_NAMES_FR

    def test_lifespan_pct_calculation(self):
        data = {"construction_year": CURRENT_YEAR - 10}
        result = compute_component_lifecycle(data)
        for comp in result["components"]:
            lifespan = COMPONENT_LIFESPANS[comp["name"]]
            expected_pct = round(10 / lifespan, 2)
            assert comp["lifespan_pct"] == expected_pct

    def test_urgency_levels_correct(self):
        # Building exactly at end of shortest lifespan (20 years)
        data = {"construction_year": CURRENT_YEAR - 25}
        result = compute_component_lifecycle(data)
        urgencies = {c["urgency"] for c in result["components"]}
        # Should have a mix of urgencies for 25-year-old building
        assert len(urgencies) > 1


# ---------------------------------------------------------------------------
# 2. Renovation plan generator
# ---------------------------------------------------------------------------


class TestRenovationPlan:
    def test_old_building_generates_critical_items(self, old_building_data, enrichment_with_risks):
        # Add lifecycle data
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        result = generate_renovation_plan(old_building_data, enrichment_with_risks)

        assert "plan_items" in result
        assert len(result["plan_items"]) > 0
        assert result["total_estimated_chf"] > 0
        assert result["total_net_chf"] <= result["total_estimated_chf"]
        assert result["critical_items_count"] > 0
        assert "estimation" in result["summary_fr"].lower() or "critique" in result["summary_fr"].lower()

    def test_modern_building_fewer_items(self, modern_building_data):
        lifecycle = compute_component_lifecycle(modern_building_data)
        enrichment = {"component_lifecycle": lifecycle, "pollutant_risk": {}, "subsidies": {}}
        result = generate_renovation_plan(modern_building_data, enrichment)
        assert result["critical_items_count"] == 0

    def test_pollutant_remediation_included(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        result = generate_renovation_plan(old_building_data, enrichment_with_risks)
        components = [i["component"] for i in result["plan_items"]]
        assert "asbestos" in components  # high asbestos probability
        assert "pcb" in components  # high PCB probability

    def test_plan_items_have_required_fields(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        result = generate_renovation_plan(old_building_data, enrichment_with_risks)
        required_fields = {
            "year_recommended",
            "component",
            "work_description_fr",
            "estimated_cost_chf",
            "available_subsidy_chf",
            "net_cost_chf",
            "priority",
            "regulatory_trigger",
        }
        for item in result["plan_items"]:
            assert required_fields.issubset(item.keys())

    def test_costs_use_surface_area(self):
        data_small = {"construction_year": 1960, "surface_area_m2": 100}
        data_large = {"construction_year": 1960, "surface_area_m2": 1000}
        lifecycle = compute_component_lifecycle(data_small)
        enrichment = {
            "component_lifecycle": lifecycle,
            "pollutant_risk": {"asbestos_probability": 0.9},
            "subsidies": {},
        }

        result_small = generate_renovation_plan(data_small, enrichment)

        lifecycle_large = compute_component_lifecycle(data_large)
        enrichment_large = {
            "component_lifecycle": lifecycle_large,
            "pollutant_risk": {"asbestos_probability": 0.9},
            "subsidies": {},
        }
        result_large = generate_renovation_plan(data_large, enrichment_large)

        assert result_large["total_estimated_chf"] > result_small["total_estimated_chf"]


# ---------------------------------------------------------------------------
# 3. Regulatory compliance check
# ---------------------------------------------------------------------------


class TestRegulatoryCompliance:
    def test_old_fossil_building_has_non_compliant(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        result = compute_regulatory_compliance(old_building_data, enrichment_with_risks)

        assert "checks" in result
        assert len(result["checks"]) == 10  # 10 regulations
        assert result["non_compliant_count"] > 0
        assert result["overall_status"] == "action_required"

    def test_modern_building_mostly_compliant(self, modern_building_data):
        lifecycle = compute_component_lifecycle(modern_building_data)
        enrichment = {
            "component_lifecycle": lifecycle,
            "pollutant_risk": {},
            "noise": {},
            "railway_noise": {},
            "water_protection": {},
            "groundwater_zones": {},
            "accessibility": {},
        }
        result = compute_regulatory_compliance(modern_building_data, enrichment)
        assert result["non_compliant_count"] == 0

    def test_all_checks_have_required_fields(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        result = compute_regulatory_compliance(old_building_data, enrichment_with_risks)

        required_fields = {"code", "name", "applicable", "status", "reason_fr", "action_required_fr", "confidence"}
        for check in result["checks"]:
            assert required_fields.issubset(check.keys()), f"Missing fields in {check.get('code')}"

    def test_noise_check_high_noise(self, old_building_data):
        enrichment = {
            "component_lifecycle": {"components": []},
            "noise": {"road_noise_day_db": 70},
            "railway_noise": {},
            "pollutant_risk": {},
            "water_protection": {},
            "groundwater_zones": {},
            "accessibility": {},
        }
        result = compute_regulatory_compliance(old_building_data, enrichment)
        opb = next(c for c in result["checks"] if c["code"] == "OPB")
        assert opb["status"] == "likely_non_compliant"

    def test_water_protection_zone(self, old_building_data):
        enrichment = {
            "component_lifecycle": {"components": []},
            "noise": {},
            "railway_noise": {},
            "pollutant_risk": {},
            "water_protection": {"in_protection_zone": True},
            "groundwater_zones": {},
            "accessibility": {},
        }
        result = compute_regulatory_compliance(old_building_data, enrichment)
        leaux = next(c for c in result["checks"] if c["code"] == "LEaux")
        assert leaux["status"] == "review_needed"


# ---------------------------------------------------------------------------
# 4. Financial impact estimator
# ---------------------------------------------------------------------------


class TestFinancialImpact:
    def test_old_fossil_building_high_cost(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        reno = generate_renovation_plan(old_building_data, enrichment_with_risks)
        enrichment_with_risks["renovation_plan"] = reno
        result = estimate_financial_impact(old_building_data, enrichment_with_risks)

        assert result["cost_of_inaction_chf_per_year"] > 0
        assert result["energy_savings_chf"] > 0
        assert result["co2_reduction_tons"] > 0
        assert result["value_increase_pct"] > 0
        assert "estimation" in result["summary_fr"].lower() or "estime" in result["summary_fr"].lower()

    def test_modern_building_low_cost(self, modern_building_data):
        lifecycle = compute_component_lifecycle(modern_building_data)
        enrichment = {"component_lifecycle": lifecycle, "renovation_plan": {}}
        result = estimate_financial_impact(modern_building_data, enrichment)

        assert result["cost_of_inaction_chf_per_year"] == 0
        assert result["co2_reduction_tons"] == 0

    def test_roi_calculation(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        enrichment_with_risks["renovation_plan"] = {"total_net_chf": 100000}
        result = estimate_financial_impact(old_building_data, enrichment_with_risks)
        assert result["renovation_roi_years"] > 0

    def test_no_construction_year_uses_default(self):
        data = {"construction_year": None, "surface_area_m2": 200, "heating_type": ""}
        enrichment = {"component_lifecycle": {"components": []}, "renovation_plan": {}}
        result = estimate_financial_impact(data, enrichment)
        assert isinstance(result["cost_of_inaction_chf_per_year"], (int, float))


# ---------------------------------------------------------------------------
# 5. Building narrative generator
# ---------------------------------------------------------------------------


class TestBuildingNarrative:
    def test_generates_all_sections(self, old_building_data, enrichment_with_risks):
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle
        reno = generate_renovation_plan(old_building_data, enrichment_with_risks)
        enrichment_with_risks["renovation_plan"] = reno
        compliance = compute_regulatory_compliance(old_building_data, enrichment_with_risks)
        enrichment_with_risks["regulatory_compliance"] = compliance
        financial = estimate_financial_impact(old_building_data, enrichment_with_risks)
        enrichment_with_risks["financial_impact"] = financial

        result = generate_building_narrative(old_building_data, enrichment_with_risks)

        assert "narrative_fr" in result
        assert "sections" in result
        assert len(result["sections"]) == 9
        assert result["word_count"] > 50

    def test_narrative_contains_address(self, old_building_data):
        enrichment = {}
        result = generate_building_narrative(old_building_data, enrichment)
        assert "Rue du Test 1" in result["narrative_fr"]

    def test_narrative_contains_year(self, old_building_data):
        enrichment = {}
        result = generate_building_narrative(old_building_data, enrichment)
        assert "1965" in result["narrative_fr"]

    def test_section_titles_in_french(self, old_building_data):
        enrichment = {}
        result = generate_building_narrative(old_building_data, enrichment)
        titles = [s["title"] for s in result["sections"]]
        assert "Identification et contexte" in titles
        assert "Caracteristiques physiques" in titles
        assert "Contexte environnemental" in titles

    def test_no_construction_year(self):
        data = {"construction_year": None, "address": "Somewhere 1", "city": "Zurich"}
        result = generate_building_narrative(data, {})
        assert "narrative_fr" in result
        assert result["word_count"] > 0


# ---------------------------------------------------------------------------
# Integration: pipeline ordering
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Verify that the five new functions can be chained correctly."""

    def test_full_pipeline_chain(self, old_building_data, enrichment_with_risks):
        # Step 44
        lifecycle = compute_component_lifecycle(old_building_data)
        enrichment_with_risks["component_lifecycle"] = lifecycle

        # Step 45
        reno = generate_renovation_plan(old_building_data, enrichment_with_risks)
        enrichment_with_risks["renovation_plan"] = reno

        # Step 46
        compliance = compute_regulatory_compliance(old_building_data, enrichment_with_risks)
        enrichment_with_risks["regulatory_compliance"] = compliance

        # Step 47
        financial = estimate_financial_impact(old_building_data, enrichment_with_risks)
        enrichment_with_risks["financial_impact"] = financial

        # Step 48
        narrative = generate_building_narrative(old_building_data, enrichment_with_risks)
        enrichment_with_risks["building_narrative"] = narrative

        # All steps produced results
        assert lifecycle["components"]
        assert reno["plan_items"]
        assert compliance["checks"]
        assert financial["cost_of_inaction_chf_per_year"] > 0
        assert narrative["word_count"] > 100

    def test_empty_enrichment_data_doesnt_crash(self):
        data = {"construction_year": 2000, "surface_area_m2": 200, "address": "Test 1"}
        enrichment: dict = {}

        lifecycle = compute_component_lifecycle(data)
        enrichment["component_lifecycle"] = lifecycle

        reno = generate_renovation_plan(data, enrichment)
        enrichment["renovation_plan"] = reno

        compliance = compute_regulatory_compliance(data, enrichment)
        enrichment["regulatory_compliance"] = compliance

        financial = estimate_financial_impact(data, enrichment)
        enrichment["financial_impact"] = financial

        narrative = generate_building_narrative(data, enrichment)
        enrichment["building_narrative"] = narrative

        assert narrative["word_count"] > 0
