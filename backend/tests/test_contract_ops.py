"""BatiConnect — Contract Ops tests (service-layer + route-level)."""

import uuid
from datetime import date

import pytest

from app.api.contracts import router as contracts_router
from app.main import app
from app.services.contract_service import create_contract, get_contract_summary, list_contracts, update_contract

# Register contracts router for HTTP tests
app.include_router(contracts_router, prefix="/api/v1")


# ---- Service-layer tests ----


@pytest.mark.asyncio
async def test_create_contract_service(db_session, sample_building, admin_user):
    data = {
        "contract_type": "maintenance",
        "reference_code": "CTR-SVC-001",
        "title": "Maintenance annuelle ascenseur",
        "counterparty_type": "contact",
        "counterparty_id": uuid.uuid4(),
        "date_start": date(2024, 1, 1),
        "annual_cost_chf": 4800.0,
        "status": "active",
    }
    contract = await create_contract(db_session, sample_building.id, data, created_by=admin_user.id)
    assert contract.id is not None
    assert contract.annual_cost_chf == 4800.0


@pytest.mark.asyncio
async def test_list_contracts_service(db_session, sample_building):
    for i in range(3):
        await create_contract(
            db_session,
            sample_building.id,
            {
                "contract_type": "maintenance",
                "reference_code": f"CTR-LIST-{i}",
                "title": f"Contract {i}",
                "counterparty_type": "contact",
                "counterparty_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "status": "active",
            },
        )
    _items, total = await list_contracts(db_session, sample_building.id)
    assert total == 3


@pytest.mark.asyncio
async def test_update_contract_service(db_session, sample_building):
    contract = await create_contract(
        db_session,
        sample_building.id,
        {
            "contract_type": "maintenance",
            "reference_code": "CTR-UPD-001",
            "title": "Old title",
            "counterparty_type": "contact",
            "counterparty_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "annual_cost_chf": 4800.0,
            "status": "active",
        },
    )
    updated = await update_contract(db_session, contract, {"annual_cost_chf": 5200.0})
    assert updated.annual_cost_chf == 5200.0


@pytest.mark.asyncio
async def test_get_contract_summary_service(db_session, sample_building):
    for i, (st, cost, auto) in enumerate(
        [
            ("active", 4800.0, True),
            ("active", 3600.0, False),
            ("terminated", 2400.0, False),
            ("suspended", 1200.0, False),
        ]
    ):
        await create_contract(
            db_session,
            sample_building.id,
            {
                "contract_type": "maintenance",
                "reference_code": f"CTR-SUM-{i}",
                "title": f"Summary contract {i}",
                "counterparty_type": "contact",
                "counterparty_id": uuid.uuid4(),
                "date_start": date(2023, 1, 1),
                "annual_cost_chf": cost,
                "auto_renewal": auto,
                "status": st,
            },
        )
    summary = await get_contract_summary(db_session, sample_building.id)
    assert summary["total_contracts"] == 4
    assert summary["active_contracts"] == 2
    assert summary["annual_cost_chf"] == 8400.0
    assert summary["auto_renewal_count"] == 1


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_list_contracts(client, auth_headers, db_session, sample_building, admin_user):
    for i in range(2):
        await create_contract(
            db_session,
            sample_building.id,
            {
                "contract_type": "maintenance",
                "reference_code": f"API-C-{i}",
                "title": f"API Contract {i}",
                "counterparty_type": "contact",
                "counterparty_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "status": "active",
                "annual_cost_chf": 3600.0,
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contracts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 2
    assert "size" in body


@pytest.mark.asyncio
async def test_api_list_contracts_pagination(client, auth_headers, db_session, sample_building, admin_user):
    for i in range(5):
        await create_contract(
            db_session,
            sample_building.id,
            {
                "contract_type": "maintenance",
                "reference_code": f"PAG-C-{i}",
                "title": f"Pagination contract {i}",
                "counterparty_type": "contact",
                "counterparty_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "status": "active",
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contracts?page=1&size=2", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["pages"] == 3


@pytest.mark.asyncio
async def test_api_list_contracts_filter_status(client, auth_headers, db_session, sample_building, admin_user):
    await create_contract(
        db_session,
        sample_building.id,
        {
            "contract_type": "maintenance",
            "reference_code": "FILT-C-A",
            "title": "Active contract",
            "counterparty_type": "contact",
            "counterparty_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await create_contract(
        db_session,
        sample_building.id,
        {
            "contract_type": "cleaning",
            "reference_code": "FILT-C-T",
            "title": "Terminated contract",
            "counterparty_type": "contact",
            "counterparty_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "status": "terminated",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contracts?status=active", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_api_create_contract(client, auth_headers, sample_building):
    payload = {
        "contract_type": "elevator",
        "reference_code": "API-CC-001",
        "title": "Elevator maintenance",
        "counterparty_type": "contact",
        "counterparty_id": str(uuid.uuid4()),
        "date_start": "2024-01-01",
        "annual_cost_chf": 6000.0,
    }
    resp = await client.post(f"/api/v1/buildings/{sample_building.id}/contracts", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["reference_code"] == "API-CC-001"
    assert body["annual_cost_chf"] == 6000.0
    assert body["id"] is not None
    assert "counterparty_display_name" in body


@pytest.mark.asyncio
async def test_api_get_contract(client, auth_headers, db_session, sample_building, admin_user):
    contract = await create_contract(
        db_session,
        sample_building.id,
        {
            "contract_type": "insurance",
            "reference_code": "API-GC-001",
            "title": "Building insurance",
            "counterparty_type": "contact",
            "counterparty_id": uuid.uuid4(),
            "date_start": date(2024, 6, 1),
            "annual_cost_chf": 12000.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/contracts/{contract.id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["reference_code"] == "API-GC-001"
    assert body["contract_type"] == "insurance"


@pytest.mark.asyncio
async def test_api_update_contract(client, auth_headers, db_session, sample_building, admin_user):
    contract = await create_contract(
        db_session,
        sample_building.id,
        {
            "contract_type": "maintenance",
            "reference_code": "API-UC-001",
            "title": "Maintenance contract",
            "counterparty_type": "contact",
            "counterparty_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "annual_cost_chf": 4800.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.put(
        f"/api/v1/contracts/{contract.id}",
        json={"annual_cost_chf": 5400.0, "status": "terminated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["annual_cost_chf"] == 5400.0
    assert body["status"] == "terminated"


@pytest.mark.asyncio
async def test_api_contract_summary(client, auth_headers, db_session, sample_building, admin_user):
    for i, (st, cost) in enumerate([("active", 6000.0), ("active", 3600.0), ("suspended", 2400.0)]):
        await create_contract(
            db_session,
            sample_building.id,
            {
                "contract_type": "maintenance",
                "reference_code": f"SUM-C-API-{i}",
                "title": f"Summary API contract {i}",
                "counterparty_type": "contact",
                "counterparty_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "annual_cost_chf": cost,
                "status": st,
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contract-summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contracts"] == 3
    assert body["active_contracts"] == 2
    assert body["annual_cost_chf"] == 9600.0


@pytest.mark.asyncio
async def test_api_contract_building_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/contracts", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_contract_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/contracts/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_contract_rbac_diagnostician_read_only(client, diag_headers, db_session, sample_building, admin_user):
    contract = await create_contract(
        db_session,
        sample_building.id,
        {
            "contract_type": "maintenance",
            "reference_code": "RBAC-C-001",
            "title": "RBAC contract",
            "counterparty_type": "contact",
            "counterparty_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    # Can list
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contracts", headers=diag_headers)
    assert resp.status_code == 200

    # Can read
    resp = await client.get(f"/api/v1/contracts/{contract.id}", headers=diag_headers)
    assert resp.status_code == 200

    # Cannot create
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/contracts",
        json={
            "contract_type": "maintenance",
            "reference_code": "RBAC-C-FAIL",
            "title": "Should fail",
            "counterparty_type": "contact",
            "counterparty_id": str(uuid.uuid4()),
            "date_start": "2024-01-01",
        },
        headers=diag_headers,
    )
    assert resp.status_code in (401, 403)

    # Cannot update
    resp = await client.put(f"/api/v1/contracts/{contract.id}", json={"status": "terminated"}, headers=diag_headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_api_contract_unauthorized(client):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/contracts")
    assert resp.status_code in (401, 403)
