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
