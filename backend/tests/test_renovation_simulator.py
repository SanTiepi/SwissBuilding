import uuid

from app.models.building import Building
from app.services.renovation_simulator import (
    estimate_remediation_cost,
    estimate_timeline_weeks,
    get_required_diagnostics,
)


def test_remediation_cost_high_risk():
    """Major risk asbestos remediation should have significant cost."""
    cost = estimate_remediation_cost("asbestos", "major", 100.0)
    assert cost > 0
    assert isinstance(cost, float)


def test_remediation_cost_low_risk():
    """Minor risk should have lower cost than major risk."""
    cost_low = estimate_remediation_cost("asbestos", "minor", 100.0)
    cost_high = estimate_remediation_cost("asbestos", "major", 100.0)
    assert cost_low < cost_high


def test_timeline_estimation():
    """Timeline should be positive and reasonable."""
    pollutant_risks = [
        {"pollutant": "asbestos", "risk_level": "high"},
        {"pollutant": "pcb", "risk_level": "medium"},
    ]
    weeks = estimate_timeline_weeks(pollutant_risks, "full_renovation")
    assert weeks > 0
    assert weeks <= 52  # Reasonable max


def test_required_diagnostics_old_building():
    """Old buildings should require diagnostics before renovation."""
    building = Building(
        id=uuid.uuid4(),
        address="Test",
        postal_code="1000",
        city="Test",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=uuid.uuid4(),
        status="active",
    )
    diagnostics = get_required_diagnostics(building, "full_renovation")
    assert len(diagnostics) > 0
    assert "asbestos" in diagnostics or any("amiante" in d.lower() for d in diagnostics)


def test_required_diagnostics_new_building():
    """New buildings (post-1995) should require fewer diagnostics."""
    building = Building(
        id=uuid.uuid4(),
        address="Test",
        postal_code="1000",
        city="Test",
        canton="VD",
        construction_year=2005,
        building_type="residential",
        created_by=uuid.uuid4(),
        status="active",
    )
    diag_new = get_required_diagnostics(building, "full_renovation")

    building_old = Building(
        id=uuid.uuid4(),
        address="Test",
        postal_code="1000",
        city="Test",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=uuid.uuid4(),
        status="active",
    )
    diag_old = get_required_diagnostics(building_old, "full_renovation")

    assert len(diag_new) <= len(diag_old)


def test_cost_scales_with_surface():
    """Remediation cost should scale with surface area."""
    cost_small = estimate_remediation_cost("asbestos", "medium", 50.0)
    cost_large = estimate_remediation_cost("asbestos", "medium", 500.0)
    assert cost_large > cost_small
