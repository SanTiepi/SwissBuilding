"""Tests for the Bulk Operations Service and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.services.bulk_operations_service import (
    bulk_calculate_trust,
    bulk_evaluate_readiness,
    bulk_generate_actions,
    bulk_generate_unknowns,
    bulk_run_dossier_agent,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": datetime.now(UTC).date(),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


# ── Service tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_generate_actions_correct_counts(db_session, admin_user):
    """Bulk generate actions for 3 buildings returns correct counts."""
    buildings = [await _create_building(db_session, admin_user) for _ in range(3)]
    for b in buildings:
        await _create_diagnostic(db_session, b.id)
    await db_session.commit()

    bids = [b.id for b in buildings]

    with patch(
        "app.services.bulk_operations_service.action_generator.generate_actions_from_diagnostic",
        new_callable=AsyncMock,
        return_value=[SimpleNamespace(id=uuid.uuid4())],
    ):
        result = await bulk_generate_actions(db_session, bids, admin_user.id)

    assert result.total_buildings == 3
    assert result.succeeded == 3
    assert result.failed == 0
    assert result.skipped == 0
    assert result.operation_type == "generate_actions"
    assert all(r.status == "success" for r in result.results)


@pytest.mark.asyncio
async def test_bulk_generate_unknowns(db_session, admin_user):
    """Bulk generate unknowns creates unknowns for each building."""
    buildings = [await _create_building(db_session, admin_user) for _ in range(3)]
    await db_session.commit()
    bids = [b.id for b in buildings]

    with patch(
        "app.services.bulk_operations_service.unknown_generator.generate_unknowns",
        new_callable=AsyncMock,
        return_value=[SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())],
    ):
        result = await bulk_generate_unknowns(db_session, bids)

    assert result.succeeded == 3
    assert result.operation_type == "generate_unknowns"
    assert all(r.items_created == 2 for r in result.results)


@pytest.mark.asyncio
async def test_bulk_evaluate_readiness(db_session, admin_user):
    """Bulk evaluate readiness returns readiness results for each building."""
    buildings = [await _create_building(db_session, admin_user) for _ in range(2)]
    await db_session.commit()
    bids = [b.id for b in buildings]

    mock_assessment = SimpleNamespace(status="ready")
    with patch(
        "app.services.bulk_operations_service.readiness_reasoner.evaluate_readiness",
        new_callable=AsyncMock,
        return_value=mock_assessment,
    ):
        result = await bulk_evaluate_readiness(db_session, bids)

    assert result.succeeded == 2
    assert result.operation_type == "evaluate_readiness"
    assert all("ready" in r.message for r in result.results)


@pytest.mark.asyncio
async def test_bulk_calculate_trust(db_session, admin_user):
    """Bulk calculate trust scores for each building."""
    buildings = [await _create_building(db_session, admin_user) for _ in range(2)]
    await db_session.commit()
    bids = [b.id for b in buildings]

    mock_trust = SimpleNamespace(overall_score=0.85)
    with patch(
        "app.services.bulk_operations_service.trust_score_calculator.calculate_trust_score",
        new_callable=AsyncMock,
        return_value=mock_trust,
    ):
        result = await bulk_calculate_trust(db_session, bids)

    assert result.succeeded == 2
    assert result.operation_type == "calculate_trust"
    assert all("0.85" in r.message for r in result.results)


@pytest.mark.asyncio
async def test_bulk_run_dossier_agent(db_session, admin_user):
    """Bulk run dossier agent returns reports for each building."""
    buildings = [await _create_building(db_session, admin_user) for _ in range(2)]
    await db_session.commit()
    bids = [b.id for b in buildings]

    mock_report = SimpleNamespace(overall_status="incomplete")
    with patch(
        "app.services.bulk_operations_service.run_dossier_completion",
        new_callable=AsyncMock,
        return_value=mock_report,
    ):
        result = await bulk_run_dossier_agent(db_session, bids)

    assert result.succeeded == 2
    assert result.operation_type == "run_dossier_agent"
    assert all("incomplete" in r.message for r in result.results)


@pytest.mark.asyncio
async def test_max_50_limit_schema_validation():
    """More than 50 building IDs should fail Pydantic validation."""
    from pydantic import ValidationError

    from app.schemas.bulk_operations import BulkOperationRequest

    ids_51 = [str(uuid.uuid4()) for _ in range(51)]
    with pytest.raises(ValidationError):
        BulkOperationRequest(building_ids=ids_51, operation_type="generate_actions")


@pytest.mark.asyncio
async def test_nonexistent_building_ids_skipped(db_session, admin_user):
    """Non-existent building IDs are skipped with warning."""
    real = await _create_building(db_session, admin_user)
    await db_session.commit()
    fake_id = uuid.uuid4()
    bids = [real.id, fake_id]

    with patch(
        "app.services.bulk_operations_service.unknown_generator.generate_unknowns",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await bulk_generate_unknowns(db_session, bids)

    assert result.succeeded == 1
    assert result.skipped == 1
    skipped_r = [r for r in result.results if r.status == "skipped"]
    assert len(skipped_r) == 1
    assert skipped_r[0].building_id == str(fake_id)


@pytest.mark.asyncio
async def test_empty_building_list_schema_validation():
    """Empty building list should fail Pydantic validation."""
    from pydantic import ValidationError

    from app.schemas.bulk_operations import BulkOperationRequest

    with pytest.raises(ValidationError):
        BulkOperationRequest(building_ids=[], operation_type="generate_actions")


@pytest.mark.asyncio
async def test_mixed_success_failure(db_session, admin_user):
    """Mixed success/failure produces correct counts."""
    b1 = await _create_building(db_session, admin_user)
    b2 = await _create_building(db_session, admin_user)
    await db_session.commit()
    bids = [b1.id, b2.id]

    call_count = 0

    async def _mock_generate(db, building_id):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Simulated failure")
        return []

    with patch(
        "app.services.bulk_operations_service.unknown_generator.generate_unknowns",
        side_effect=_mock_generate,
    ):
        result = await bulk_generate_unknowns(db_session, bids)

    assert result.succeeded == 1
    assert result.failed == 1
    assert result.skipped == 0


@pytest.mark.asyncio
async def test_api_endpoint_returns_200(client, admin_user, auth_headers, db_session):
    """POST /api/v1/bulk-operations/execute returns 200 with result."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Bulk 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    with patch(
        "app.services.bulk_operations_service.unknown_generator.generate_unknowns",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.post(
            "/api/v1/bulk-operations/execute",
            json={
                "building_ids": [str(b.id)],
                "operation_type": "generate_unknowns",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_type"] == "generate_unknowns"
    assert data["total_buildings"] == 1
    assert data["succeeded"] == 1


@pytest.mark.asyncio
async def test_api_endpoint_validates_operation_type(client, admin_user, auth_headers):
    """POST /api/v1/bulk-operations/execute rejects invalid operation_type."""
    resp = await client.post(
        "/api/v1/bulk-operations/execute",
        json={
            "building_ids": [str(uuid.uuid4())],
            "operation_type": "invalid_op",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_per_building_error_isolation(db_session, admin_user):
    """One building failure does not stop processing of others."""
    b1 = await _create_building(db_session, admin_user)
    b2 = await _create_building(db_session, admin_user)
    b3 = await _create_building(db_session, admin_user)
    await db_session.commit()
    bids = [b1.id, b2.id, b3.id]

    call_idx = 0

    async def _mock_trust(db, building_id, assessed_by=None):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 2:
            raise RuntimeError("Trust calc error")
        return SimpleNamespace(overall_score=0.75)

    with patch(
        "app.services.bulk_operations_service.trust_score_calculator.calculate_trust_score",
        side_effect=_mock_trust,
    ):
        result = await bulk_calculate_trust(db_session, bids)

    assert result.total_buildings == 3
    assert result.succeeded == 2
    assert result.failed == 1
    # Verify the other buildings still got processed
    success_results = [r for r in result.results if r.status == "success"]
    assert len(success_results) == 2
