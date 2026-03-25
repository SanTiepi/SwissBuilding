from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.sample import SampleRead


@pytest.mark.asyncio
async def test_create_diagnostic(client, diag_headers, sample_building):
    """Create a diagnostic for a building."""
    response = await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={
            "diagnostic_type": "asbestos",
            "diagnostic_context": "AvT",
            "date_inspection": "2024-01-15",
            "methodology": "FACH_2018",
        },
        headers=diag_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["diagnostic_type"] == "asbestos"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_diagnostics_by_building(client, diag_headers, sample_building):
    """List diagnostics for a specific building."""
    # Create a diagnostic first
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={"diagnostic_type": "full", "date_inspection": "2024-02-01"},
        headers=diag_headers,
    )
    response = await client.get(f"/api/v1/buildings/{sample_building.id}/diagnostics", headers=diag_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_diagnostic_with_samples(client, diag_headers, sample_building):
    """Get diagnostic detail should include samples."""
    # Create diagnostic
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={"diagnostic_type": "asbestos", "date_inspection": "2024-01-15"},
        headers=diag_headers,
    )
    diag_id = resp.json()["id"]
    # Get detail
    response = await client.get(f"/api/v1/diagnostics/{diag_id}", headers=diag_headers)
    assert response.status_code == 200
    assert "samples" in response.json()


@pytest.mark.asyncio
async def test_create_sample_auto_classification(client, diag_headers, sample_building):
    """Creating a sample should auto-classify threshold, risk, CFST category."""
    # Create diagnostic
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={"diagnostic_type": "asbestos", "date_inspection": "2024-01-15"},
        headers=diag_headers,
    )
    diag_id = resp.json()["id"]
    # Create sample with concentration above threshold
    response = await client.post(
        f"/api/v1/diagnostics/{diag_id}/samples",
        json={
            "sample_number": "E-001",
            "material_category": "flocage",
            "pollutant_type": "asbestos",
            "concentration": 15.0,
            "unit": "percent_weight",
            "material_state": "mauvais",
        },
        headers=diag_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["threshold_exceeded"] is True
    assert data["risk_level"] in ["high", "critical"]


@pytest.mark.asyncio
async def test_create_sample_normalizes_unit_alias(client, diag_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={"diagnostic_type": "pcb", "date_inspection": "2024-01-15"},
        headers=diag_headers,
    )
    diag_id = resp.json()["id"]

    response = await client.post(
        f"/api/v1/diagnostics/{diag_id}/samples",
        json={
            "sample_number": "PCB-001",
            "material_category": "sealant",
            "pollutant_type": "pcb",
            "concentration": 120.0,
            "unit": "mg/kg",
        },
        headers=diag_headers,
    )

    assert response.status_code == 201
    assert response.json()["unit"] == "mg_per_kg"


def test_sample_read_normalizes_legacy_unit_value() -> None:
    legacy_sample = SimpleNamespace(
        id=uuid4(),
        diagnostic_id=uuid4(),
        sample_number="RAD-001",
        location_floor=None,
        location_room=None,
        location_detail="Mesure air",
        material_category="indoor_air",
        material_description=None,
        material_state=None,
        pollutant_type="radon",
        pollutant_subtype=None,
        concentration=180.0,
        unit="Bq/m³",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="monitoring",
        waste_disposal_type="type_b",
        notes=None,
        created_at=datetime.now(UTC),
    )

    data = SampleRead.model_validate(legacy_sample)
    assert data.unit == "bq_per_m3"


@pytest.mark.asyncio
async def test_owner_cannot_create_diagnostic(client, owner_headers, sample_building):
    """Owner role should not be able to create diagnostics."""
    response = await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={"diagnostic_type": "asbestos", "date_inspection": "2024-01-15"},
        headers=owner_headers,
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_diagnostic_status_update(client, diag_headers, sample_building):
    """Update diagnostic status."""
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/diagnostics",
        json={"diagnostic_type": "full", "date_inspection": "2024-01-15"},
        headers=diag_headers,
    )
    diag_id = resp.json()["id"]
    response = await client.put(f"/api/v1/diagnostics/{diag_id}", json={"status": "in_progress"}, headers=diag_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
