"""BatiConnect — Owner Ops tests (service-layer + route-level)."""

import uuid
from datetime import date, timedelta

import pytest

from app.api.owner_ops import router as owner_ops_router
from app.main import app
from app.models.organization import Organization
from app.services.owner_ops_service import (
    create_recurring_service,
    create_warranty,
    get_annual_cost_summary,
    get_expiring_warranties,
    get_owner_dashboard,
    get_recurring_service,
    get_upcoming_services,
    get_warranty,
    list_recurring_services,
    list_warranties,
    record_service_performed,
    update_recurring_service,
    update_warranty,
)

app.include_router(owner_ops_router, prefix="/api/v1")


@pytest.fixture
async def sample_org(db_session, admin_user):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Property Mgmt",
        type="property_management",
    )
    db_session.add(org)
    # Attach user to org
    admin_user.organization_id = org.id
    await db_session.commit()
    await db_session.refresh(org)
    await db_session.refresh(admin_user)
    return org


# ---- Helper factories ----


def _service_data(**overrides):
    defaults = {
        "service_type": "elevator",
        "provider_name": "Schindler SA",
        "frequency": "quarterly",
        "start_date": date.today() - timedelta(days=365),
        "renewal_type": "auto",
        "annual_cost_chf": 4800.0,
        "next_service_date": date.today() + timedelta(days=15),
    }
    defaults.update(overrides)
    return defaults


def _warranty_data(**overrides):
    defaults = {
        "warranty_type": "works",
        "subject": "Renovation toiture",
        "provider_name": "Batipro SA",
        "start_date": date.today() - timedelta(days=180),
        "end_date": date.today() + timedelta(days=180),
        "duration_months": 12,
    }
    defaults.update(overrides)
    return defaults


# ---- Service-layer: Recurring Services ----


@pytest.mark.asyncio
async def test_create_recurring_service(db_session, sample_building, sample_org):
    svc = await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    assert svc.id is not None
    assert svc.service_type == "elevator"
    assert svc.status == "active"
    assert svc.provider_name == "Schindler SA"


@pytest.mark.asyncio
async def test_list_recurring_services(db_session, sample_building, sample_org):
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(service_type="heating", provider_name="Calida AG"),
    )
    all_svcs = await list_recurring_services(db_session, sample_building.id)
    assert len(all_svcs) == 2

    elev_only = await list_recurring_services(db_session, sample_building.id, service_type="elevator")
    assert len(elev_only) == 1


@pytest.mark.asyncio
async def test_list_recurring_services_status_filter(db_session, sample_building, sample_org):
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data(status="terminated"))
    active = await list_recurring_services(db_session, sample_building.id, status_filter="active")
    assert len(active) == 1


@pytest.mark.asyncio
async def test_get_recurring_service(db_session, sample_building, sample_org):
    svc = await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    found = await get_recurring_service(db_session, svc.id)
    assert found is not None
    assert found.id == svc.id


@pytest.mark.asyncio
async def test_get_recurring_service_not_found(db_session):
    found = await get_recurring_service(db_session, uuid.uuid4())
    assert found is None


@pytest.mark.asyncio
async def test_update_recurring_service(db_session, sample_building, sample_org):
    svc = await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    updated = await update_recurring_service(db_session, svc, {"annual_cost_chf": 5200.0, "status": "paused"})
    assert updated.annual_cost_chf == 5200.0
    assert updated.status == "paused"


@pytest.mark.asyncio
async def test_record_service_performed(db_session, sample_building, sample_org):
    svc = await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(frequency="monthly"),
    )
    today = date.today()
    updated = await record_service_performed(db_session, svc, today, notes="RAS")
    assert updated.last_service_date == today
    assert updated.next_service_date == today + timedelta(days=30)
    assert updated.notes == "RAS"


@pytest.mark.asyncio
async def test_record_service_performed_on_demand(db_session, sample_building, sample_org):
    svc = await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(frequency="on_demand", next_service_date=None),
    )
    today = date.today()
    updated = await record_service_performed(db_session, svc, today)
    assert updated.last_service_date == today
    # on_demand has no auto-calculated next date
    assert updated.next_service_date is None


@pytest.mark.asyncio
async def test_get_upcoming_services(db_session, sample_building, sample_org):
    await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(next_service_date=date.today() + timedelta(days=10)),
    )
    await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(
            service_type="heating",
            next_service_date=date.today() + timedelta(days=60),
        ),
    )
    upcoming = await get_upcoming_services(db_session, sample_building.id, horizon_days=30)
    assert len(upcoming) == 1


# ---- Service-layer: Warranty Records ----


@pytest.mark.asyncio
async def test_create_warranty(db_session, sample_building, sample_org):
    warranty = await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    assert warranty.id is not None
    assert warranty.warranty_type == "works"
    assert warranty.status == "active"
    assert warranty.claim_filed is False


@pytest.mark.asyncio
async def test_list_warranties(db_session, sample_building, sample_org):
    await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    await create_warranty(
        db_session,
        sample_building.id,
        sample_org.id,
        _warranty_data(warranty_type="equipment", subject="Ascenseur"),
    )
    all_w = await list_warranties(db_session, sample_building.id)
    assert len(all_w) == 2

    works_only = await list_warranties(db_session, sample_building.id, warranty_type="works")
    assert len(works_only) == 1


@pytest.mark.asyncio
async def test_list_warranties_status_filter(db_session, sample_building, sample_org):
    await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    await create_warranty(
        db_session,
        sample_building.id,
        sample_org.id,
        _warranty_data(status="expired"),
    )
    active = await list_warranties(db_session, sample_building.id, status_filter="active")
    assert len(active) == 1


@pytest.mark.asyncio
async def test_get_warranty(db_session, sample_building, sample_org):
    warranty = await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    found = await get_warranty(db_session, warranty.id)
    assert found is not None
    assert found.id == warranty.id


@pytest.mark.asyncio
async def test_get_warranty_not_found(db_session):
    found = await get_warranty(db_session, uuid.uuid4())
    assert found is None


@pytest.mark.asyncio
async def test_update_warranty(db_session, sample_building, sample_org):
    warranty = await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    updated = await update_warranty(
        db_session, warranty, {"claim_filed": True, "claim_date": date.today(), "claim_description": "Infiltration"}
    )
    assert updated.claim_filed is True
    assert updated.claim_date == date.today()
    assert updated.claim_description == "Infiltration"


@pytest.mark.asyncio
async def test_get_expiring_warranties(db_session, sample_building, sample_org):
    # Expiring in 30 days
    await create_warranty(
        db_session,
        sample_building.id,
        sample_org.id,
        _warranty_data(end_date=date.today() + timedelta(days=30)),
    )
    # Expiring in 365 days — outside default horizon
    await create_warranty(
        db_session,
        sample_building.id,
        sample_org.id,
        _warranty_data(warranty_type="equipment", subject="Pompe", end_date=date.today() + timedelta(days=365)),
    )
    expiring = await get_expiring_warranties(db_session, sample_building.id, horizon_days=180)
    assert len(expiring) == 1


# ---- Dashboard / Aggregation ----


@pytest.mark.asyncio
async def test_get_owner_dashboard(db_session, sample_building, sample_org):
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())

    result = await get_owner_dashboard(db_session, sample_building.id)
    assert result is not None
    assert result["building_id"] == str(sample_building.id)
    assert "services" in result
    assert "warranties" in result
    assert "annual_costs" in result
    assert result["services"]["active_count"] >= 1
    assert result["warranties"]["active_count"] >= 1


@pytest.mark.asyncio
async def test_get_owner_dashboard_not_found(db_session):
    result = await get_owner_dashboard(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_annual_cost_summary(db_session, sample_building, sample_org):
    await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(annual_cost_chf=6000.0),
    )
    result = await get_annual_cost_summary(db_session, sample_building.id)
    assert result is not None
    assert result["breakdown"]["services"]["total_chf"] == 6000.0
    assert result["total_chf"] >= 6000.0


@pytest.mark.asyncio
async def test_get_annual_cost_summary_not_found(db_session):
    result = await get_annual_cost_summary(db_session, uuid.uuid4())
    assert result is None


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_list_recurring_services(client, auth_headers, db_session, sample_building, sample_org):
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/recurring-services", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["service_type"] == "elevator"


@pytest.mark.asyncio
async def test_api_create_recurring_service(client, auth_headers, sample_building, sample_org):
    payload = {
        "service_type": "cleaning",
        "provider_name": "CleanCorp SA",
        "frequency": "weekly",
        "start_date": str(date.today()),
        "renewal_type": "auto",
        "annual_cost_chf": 12000.0,
    }
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/recurring-services", json=payload, headers=auth_headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["service_type"] == "cleaning"
    assert body["provider_name"] == "CleanCorp SA"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_api_update_recurring_service(client, auth_headers, db_session, sample_building, sample_org):
    svc = await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await db_session.commit()

    resp = await client.put(
        f"/api/v1/recurring-services/{svc.id}", json={"annual_cost_chf": 5500.0}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["annual_cost_chf"] == 5500.0


@pytest.mark.asyncio
async def test_api_service_performed(client, auth_headers, db_session, sample_building, sample_org):
    svc = await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/recurring-services/{svc.id}/performed",
        json={"performed_date": str(date.today()), "notes": "OK"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_service_date"] == str(date.today())


@pytest.mark.asyncio
async def test_api_upcoming_services(client, auth_headers, db_session, sample_building, sample_org):
    await create_recurring_service(
        db_session,
        sample_building.id,
        sample_org.id,
        _service_data(next_service_date=date.today() + timedelta(days=10)),
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/recurring-services/upcoming?days=30", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_api_list_warranties(client, auth_headers, db_session, sample_building, sample_org):
    await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/warranties", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["warranty_type"] == "works"


@pytest.mark.asyncio
async def test_api_create_warranty(client, auth_headers, sample_building, sample_org):
    payload = {
        "warranty_type": "equipment",
        "subject": "Chaudiere",
        "provider_name": "Viessmann SA",
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=730)),
    }
    resp = await client.post(f"/api/v1/buildings/{sample_building.id}/warranties", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["warranty_type"] == "equipment"
    assert body["subject"] == "Chaudiere"
    assert body["claim_filed"] is False


@pytest.mark.asyncio
async def test_api_update_warranty(client, auth_headers, db_session, sample_building, sample_org):
    warranty = await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    await db_session.commit()

    resp = await client.put(
        f"/api/v1/warranties/{warranty.id}",
        json={"claim_filed": True, "claim_description": "Fuite toiture"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["claim_filed"] is True


@pytest.mark.asyncio
async def test_api_expiring_warranties(client, auth_headers, db_session, sample_building, sample_org):
    await create_warranty(
        db_session,
        sample_building.id,
        sample_org.id,
        _warranty_data(end_date=date.today() + timedelta(days=60)),
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/warranties/expiring?days=90", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_api_owner_dashboard(client, auth_headers, db_session, sample_building, sample_org):
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data())
    await create_warranty(db_session, sample_building.id, sample_org.id, _warranty_data())
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/owner-dashboard", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "services" in body
    assert "warranties" in body
    assert "annual_costs" in body


@pytest.mark.asyncio
async def test_api_annual_costs(client, auth_headers, db_session, sample_building, sample_org):
    await create_recurring_service(db_session, sample_building.id, sample_org.id, _service_data(annual_cost_chf=4800.0))
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/annual-costs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["breakdown"]["services"]["total_chf"] == 4800.0


@pytest.mark.asyncio
async def test_api_building_not_found_services(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/recurring-services", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_building_not_found_warranties(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/warranties", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_service_not_found(client, auth_headers):
    resp = await client.put(
        f"/api/v1/recurring-services/{uuid.uuid4()}", json={"status": "paused"}, headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_warranty_not_found(client, auth_headers):
    resp = await client.put(f"/api/v1/warranties/{uuid.uuid4()}", json={"status": "voided"}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_service_performed_not_found(client, auth_headers):
    resp = await client.post(
        f"/api/v1/recurring-services/{uuid.uuid4()}/performed",
        json={"performed_date": str(date.today())},
        headers=auth_headers,
    )
    assert resp.status_code == 404
