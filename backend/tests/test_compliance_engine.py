from app.services.compliance_engine import (
    auto_classify_sample,
    check_suva_notification_required,
    check_threshold,
    determine_cfst_work_category,
    determine_risk_level,
    determine_waste_disposal,
    get_cantonal_requirements,
)


def test_asbestos_threshold_exceeded():
    result = check_threshold("asbestos", 5.0, "percent_weight")
    assert result["exceeded"] is True


def test_asbestos_threshold_not_exceeded():
    result = check_threshold("asbestos", 0.5, "percent_weight")
    assert result["exceeded"] is False


def test_pcb_above_threshold():
    result = check_threshold("pcb", 120.0, "mg_per_kg")
    assert result["exceeded"] is True


def test_pcb_below_threshold():
    result = check_threshold("pcb", 30.0, "mg_per_kg")
    assert result["exceeded"] is False


def test_radon_above_reference():
    result = check_threshold("radon", 500.0, "bq_per_m3")
    assert result["exceeded"] is True


def test_risk_level_critical():
    level = determine_risk_level("asbestos", 20.0, "percent_weight")
    assert level in ["high", "critical"]


def test_risk_level_low():
    level = determine_risk_level("pcb", 10.0, "mg_per_kg")
    assert level == "low"


def test_cfst_friable_major():
    cat = determine_cfst_work_category("flocage", "mauvais", None)
    assert cat == "major"


def test_cfst_intact_minor():
    cat = determine_cfst_work_category("fibrociment_toiture", "bon", 3.0)
    assert cat == "minor"


def test_waste_friable_special():
    """Friable asbestos (flocage) is always special waste per OLED."""
    disposal = determine_waste_disposal("asbestos", "flocage", "mauvais")
    assert disposal == "special"


def test_waste_intact_fibrociment_type_b():
    disposal = determine_waste_disposal("asbestos", "fibrociment_toiture", "bon")
    assert disposal == "type_b"


def test_suva_notification_asbestos():
    assert check_suva_notification_required("asbestos", True) is True


def test_suva_notification_pcb():
    assert check_suva_notification_required("pcb", True) is False


def test_cantonal_requirements_vd():
    req = get_cantonal_requirements("VD")
    assert req["authority_name"] == "DGE-DIRNA"


def test_cantonal_requirements_default():
    req = get_cantonal_requirements("AG")
    assert "authority_name" in req


def test_auto_classify_sample():
    result = auto_classify_sample(
        {
            "pollutant_type": "asbestos",
            "material_category": "flocage",
            "concentration": 15.0,
            "unit": "percent_weight",
            "material_state": "mauvais",
        }
    )
    assert result["threshold_exceeded"] is True
    assert result["risk_level"] in ["high", "critical"]
    assert result["cfst_work_category"] == "major"
    assert result["waste_disposal_type"] == "special"
    assert result["action_required"] in ["remove_urgent", "remove_planned"]


# ---------------------------------------------------------------------------
# PFAS integration tests
# ---------------------------------------------------------------------------


def test_pfas_water_threshold_exceeded():
    """PFAS water concentration at or above 0.1 µg/L exceeds threshold."""
    result = check_threshold("pfas", 0.15, "ug_per_l")
    assert result["exceeded"] is True
    assert result["threshold"] == 0.1
    assert result["unit"] == "ug_per_l"
    assert result["action"] in ("remove_planned", "remove_urgent")


def test_pfas_water_threshold_not_exceeded():
    """PFAS water concentration below 0.1 µg/L does not exceed threshold."""
    result = check_threshold("pfas", 0.05, "ug_per_l")
    assert result["exceeded"] is False
    assert result["threshold"] == 0.1
    assert result["action"] == "none"


def test_pfas_water_threshold_at_boundary():
    """PFAS water concentration exactly at 0.1 µg/L is considered exceeded (>=)."""
    result = check_threshold("pfas", 0.1, "ug_per_l")
    assert result["exceeded"] is True


def test_pfas_soil_threshold_exceeded():
    """PFAS soil concentration above 50 ng/kg exceeds threshold."""
    result = check_threshold("pfas", 120.0, "ng_per_kg")
    assert result["exceeded"] is True
    assert result["threshold"] == 50
    assert result["unit"] == "ng_per_kg"


def test_pfas_soil_threshold_not_exceeded():
    """PFAS soil concentration below 50 ng/kg does not exceed threshold."""
    result = check_threshold("pfas", 30.0, "ng_per_kg")
    assert result["exceeded"] is False
    assert result["threshold"] == 50
    assert result["action"] == "none"


def test_pfas_waste_classification_special():
    """PFAS waste is always classified as special."""
    disposal = determine_waste_disposal("pfas", "soil", "degraded")
    assert disposal == "special"


def test_pfas_waste_classification_special_any_state():
    """PFAS waste is special regardless of material state."""
    for state in ("bon", "mauvais", "good", "degraded"):
        disposal = determine_waste_disposal("pfas", "water", state)
        assert disposal == "special", f"Expected special for state={state}"


def test_pfas_legal_references():
    """PFAS thresholds carry correct provisional legal references."""
    from app.services.compliance_engine import SWISS_THRESHOLDS

    pfas = SWISS_THRESHOLDS["pfas"]
    assert "OSEC" in pfas["water_content"]["legal_ref"]
    assert "EU Directive 2020/2184" in pfas["water_content"]["legal_ref"]
    assert "OSol" in pfas["soil_content"]["legal_ref"]
    assert "OFEV" in pfas["soil_content"]["legal_ref"]
    assert "provisional" in pfas["water_content"]["legal_ref"].lower()
    assert "provisional" in pfas["soil_content"]["legal_ref"].lower()


def test_pfas_water_legal_ref_in_check_result():
    """check_threshold returns the correct legal_ref for PFAS water."""
    result = check_threshold("pfas", 0.2, "ug_per_l")
    assert result["legal_ref"] is not None
    assert "OSEC" in result["legal_ref"]


def test_pfas_soil_legal_ref_in_check_result():
    """check_threshold returns the correct legal_ref for PFAS soil."""
    result = check_threshold("pfas", 100.0, "ng_per_kg")
    assert result["legal_ref"] is not None
    assert "OSol" in result["legal_ref"]


def test_pfas_risk_level_high():
    """PFAS water at 0.2 µg/L (2x threshold) yields high risk."""
    level = determine_risk_level("pfas", 0.2, "ug_per_l")
    assert level == "high"


def test_pfas_risk_level_critical():
    """PFAS water at 0.5 µg/L (5x threshold) yields critical risk."""
    level = determine_risk_level("pfas", 0.5, "ug_per_l")
    assert level == "critical"


def test_pfas_risk_level_low():
    """PFAS water well below threshold yields low risk."""
    level = determine_risk_level("pfas", 0.02, "ug_per_l")
    assert level == "low"


def test_pfas_auto_classify_water_above():
    """auto_classify_sample handles PFAS water sample above threshold."""
    result = auto_classify_sample(
        {
            "pollutant_type": "pfas",
            "concentration": 0.4,
            "unit": "ug_per_l",
            "material_category": "water_sample",
            "material_state": "good",
        }
    )
    assert result["threshold_exceeded"] is True
    assert result["risk_level"] == "critical"
    assert result["cfst_work_category"] is None  # CFST is asbestos-only
    assert result["waste_disposal_type"] == "special"
    assert result["action_required"] == "remove_urgent"


def test_pfas_auto_classify_soil_below():
    """auto_classify_sample handles PFAS soil sample below threshold."""
    result = auto_classify_sample(
        {
            "pollutant_type": "pfas",
            "concentration": 20.0,
            "unit": "ng_per_kg",
            "material_category": "soil_sample",
            "material_state": "good",
        }
    )
    assert result["threshold_exceeded"] is False
    assert result["risk_level"] == "low"
    assert result["waste_disposal_type"] == "type_b"
    assert result["action_required"] == "none"


def test_pfas_no_regression_on_existing_pollutants():
    """Adding PFAS does not break existing pollutant threshold checks."""
    # Asbestos still works
    assert check_threshold("asbestos", 5.0, "percent_weight")["exceeded"] is True
    assert check_threshold("asbestos", 0.5, "percent_weight")["exceeded"] is False
    # PCB still works
    assert check_threshold("pcb", 120.0, "mg_per_kg")["exceeded"] is True
    assert check_threshold("pcb", 30.0, "mg_per_kg")["exceeded"] is False
    # Lead still works
    assert check_threshold("lead", 6000.0, "mg_per_kg")["exceeded"] is True
    # Radon still works
    assert check_threshold("radon", 500.0, "bq_per_m3")["exceeded"] is True
    assert check_threshold("radon", 100.0, "bq_per_m3")["exceeded"] is False
