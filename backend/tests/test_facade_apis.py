"""Tests for evidence, remediation, and compliance facade summary APIs."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_evidence_summary_valid_building(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/evidence/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "diagnostics_count" in data
    assert "samples_count" in data
    assert "coverage_ratio" in data


@pytest.mark.asyncio
async def test_evidence_summary_nonexistent_building(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/evidence/summary", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_remediation_summary_valid_building(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/remediation/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "actions" in data
    assert "interventions" in data
    assert "has_completed_remediation" in data


@pytest.mark.asyncio
async def test_remediation_summary_nonexistent_building(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/remediation/summary", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compliance_summary_valid_building(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/compliance/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "completeness_score" in data
    assert "artefacts" in data
    assert "readiness" in data


@pytest.mark.asyncio
async def test_compliance_summary_nonexistent_building(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/compliance/summary", headers=auth_headers)
    assert resp.status_code == 404
