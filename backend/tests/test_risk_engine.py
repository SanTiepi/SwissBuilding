from app.services.risk_engine import (
    apply_modifiers,
    calculate_asbestos_base_probability,
    calculate_confidence,
    calculate_hap_base_probability,
    calculate_lead_base_probability,
    calculate_overall_risk_level,
    calculate_pcb_base_probability,
    calculate_radon_base_probability,
)


def test_asbestos_peak_era():
    """Buildings from 1970-1980 should have highest asbestos probability."""
    prob = calculate_asbestos_base_probability(1975)
    assert prob == 0.90


def test_asbestos_post_ban():
    """Buildings after 1995 should have near-zero asbestos probability."""
    prob = calculate_asbestos_base_probability(2000)
    assert prob == 0.02


def test_asbestos_unknown_year():
    """Unknown construction year should return 0.5."""
    prob = calculate_asbestos_base_probability(None)
    assert prob == 0.5


def test_pcb_peak_era():
    """PCB peak was 1970-1980."""
    prob = calculate_pcb_base_probability(1975)
    assert prob == 0.70


def test_pcb_post_ban():
    """PCB banned in 1986 for closed systems."""
    prob = calculate_pcb_base_probability(1990)
    assert prob == 0.02


def test_lead_old_building():
    """Very old buildings have high lead probability."""
    prob = calculate_lead_base_probability(1900)
    assert prob == 0.85


def test_lead_modern():
    """Modern buildings have very low lead probability."""
    prob = calculate_lead_base_probability(2010)
    assert prob == 0.02


def test_hap_peak():
    """HAP peak was 1940-1970."""
    prob = calculate_hap_base_probability(1960)
    assert prob == 0.55


def test_radon_high_canton():
    """Alpine cantons have high radon probability."""
    prob = calculate_radon_base_probability("VS")
    assert prob == 0.60


def test_radon_low_canton():
    """Plateau cantons have low radon probability."""
    prob = calculate_radon_base_probability("ZH")
    assert prob == 0.10


def test_building_type_modifier():
    """Industrial buildings should increase asbestos probability."""
    base = 0.50
    modified = apply_modifiers(base, "industrial", "asbestos")
    assert modified > base
    assert modified <= 0.99


def test_overall_risk_critical():
    """Max probability >= 0.75 should be critical."""
    scores = {"asbestos": 0.85, "pcb": 0.30, "lead": 0.10, "hap": 0.05, "radon": 0.10}
    assert calculate_overall_risk_level(scores) == "critical"


def test_overall_risk_low():
    """All probabilities < 0.25 should be low."""
    scores = {"asbestos": 0.10, "pcb": 0.05, "lead": 0.02, "hap": 0.01, "radon": 0.05}
    assert calculate_overall_risk_level(scores) == "low"


def test_confidence_with_diagnostic():
    """Having diagnostics should significantly increase confidence."""
    c_with = calculate_confidence(has_diagnostics=True, neighbor_count=0, year_known=True)
    c_without = calculate_confidence(has_diagnostics=False, neighbor_count=0, year_known=True)
    assert c_with > c_without


def test_confidence_max():
    """Maximum confidence should not exceed 1.0."""
    c = calculate_confidence(has_diagnostics=True, neighbor_count=10, year_known=True)
    assert c <= 1.0
