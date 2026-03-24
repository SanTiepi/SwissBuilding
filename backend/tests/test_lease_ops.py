"""BatiConnect — Lease Ops tests (service-layer + route-level)."""

import uuid
from datetime import date

import pytest

from app.api.contact_lookup import router as contact_lookup_router
from app.api.leases import router as leases_router
from app.main import app
from app.services.lease_service import create_lease, get_lease_summary, list_leases, update_lease

# Register leases router for HTTP tests (not yet in router.py hub file)
app.include_router(leases_router, prefix="/api/v1")
app.include_router(contact_lookup_router, prefix="/api/v1")


# ---- Service-layer tests (existing) ----


@pytest.mark.asyncio
async def test_create_lease_service(db_session, sample_building, admin_user):
    data = {
        "lease_type": "residential",
        "reference_code": "SVC-001",
        "tenant_type": "contact",
        "tenant_id": uuid.uuid4(),
        "date_start": date(2024, 1, 1),
        "rent_monthly_chf": 1500.0,
        "status": "active",
    }
    lease = await create_lease(db_session, sample_building.id, data, created_by=admin_user.id)
    assert lease.id is not None
    assert lease.rent_monthly_chf == 1500.0


@pytest.mark.asyncio
async def test_list_leases_service(db_session, sample_building):
    for i in range(3):
        await create_lease(
            db_session,
            sample_building.id,
            {
                "lease_type": "residential",
                "reference_code": f"LIST-{i}",
                "tenant_type": "contact",
                "tenant_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "status": "active",
            },
        )
    _items, total = await list_leases(db_session, sample_building.id)
    assert total == 3


@pytest.mark.asyncio
async def test_update_lease_service(db_session, sample_building):
    lease = await create_lease(
        db_session,
        sample_building.id,
        {
            "lease_type": "residential",
            "reference_code": "UPD-001",
            "tenant_type": "contact",
            "tenant_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "rent_monthly_chf": 1500.0,
            "status": "active",
        },
    )
    updated = await update_lease(db_session, lease, {"rent_monthly_chf": 1600.0})
    assert updated.rent_monthly_chf == 1600.0


@pytest.mark.asyncio
async def test_get_lease_summary_service(db_session, sample_building):
    for i, (st, rent) in enumerate(
        [("active", 1800.0), ("active", 1200.0), ("terminated", 1500.0), ("disputed", 1000.0)]
    ):
        await create_lease(
            db_session,
            sample_building.id,
            {
                "lease_type": "residential",
                "reference_code": f"SUM-{i}",
                "tenant_type": "contact",
                "tenant_id": uuid.uuid4(),
                "date_start": date(2023, 1, 1),
                "rent_monthly_chf": rent,
                "charges_monthly_chf": 200.0,
                "status": st,
            },
        )
    summary = await get_lease_summary(db_session, sample_building.id)
    assert summary["total_leases"] == 4
    assert summary["active_leases"] == 2
    assert summary["monthly_rent_chf"] == 3000.0
    assert summary["disputed_count"] == 1


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_api_list_leases(client, auth_headers, db_session, sample_building, admin_user):
    # Seed 2 leases
    for i in range(2):
        await create_lease(
            db_session,
            sample_building.id,
            {
                "lease_type": "residential",
                "reference_code": f"API-L-{i}",
                "tenant_type": "contact",
                "tenant_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "status": "active",
                "rent_monthly_chf": 1500.0,
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/leases", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 2
    # Check PaginatedResponse structure
    assert "size" in body


@pytest.mark.asyncio
async def test_api_list_leases_pagination(client, auth_headers, db_session, sample_building, admin_user):
    for i in range(5):
        await create_lease(
            db_session,
            sample_building.id,
            {
                "lease_type": "residential",
                "reference_code": f"PAG-{i}",
                "tenant_type": "contact",
                "tenant_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "status": "active",
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/leases?page=1&size=2", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["pages"] == 3


@pytest.mark.asyncio
async def test_api_list_leases_filter_status(client, auth_headers, db_session, sample_building, admin_user):
    await create_lease(
        db_session,
        sample_building.id,
        {
            "lease_type": "residential",
            "reference_code": "FILT-A",
            "tenant_type": "contact",
            "tenant_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await create_lease(
        db_session,
        sample_building.id,
        {
            "lease_type": "commercial",
            "reference_code": "FILT-T",
            "tenant_type": "contact",
            "tenant_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "status": "terminated",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/leases?status=active", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_api_create_lease(client, auth_headers, sample_building):
    # NOTE: no building_id in body — matches real UI behavior (path param only)
    payload = {
        "lease_type": "residential",
        "reference_code": "API-C-001",
        "tenant_type": "contact",
        "tenant_id": str(uuid.uuid4()),
        "date_start": "2024-01-01",
        "rent_monthly_chf": 1800.0,
        "charges_monthly_chf": 250.0,
    }
    resp = await client.post(f"/api/v1/buildings/{sample_building.id}/leases", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["reference_code"] == "API-C-001"
    assert body["rent_monthly_chf"] == 1800.0
    assert body["id"] is not None
    # Display fields should be present (None when contact doesn't exist)
    assert "tenant_display_name" in body


@pytest.mark.asyncio
async def test_api_get_lease(client, auth_headers, db_session, sample_building, admin_user):
    lease = await create_lease(
        db_session,
        sample_building.id,
        {
            "lease_type": "commercial",
            "reference_code": "API-G-001",
            "tenant_type": "contact",
            "tenant_id": uuid.uuid4(),
            "date_start": date(2024, 6, 1),
            "rent_monthly_chf": 3200.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/leases/{lease.id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["reference_code"] == "API-G-001"
    assert body["lease_type"] == "commercial"


@pytest.mark.asyncio
async def test_api_update_lease(client, auth_headers, db_session, sample_building, admin_user):
    lease = await create_lease(
        db_session,
        sample_building.id,
        {
            "lease_type": "residential",
            "reference_code": "API-U-001",
            "tenant_type": "contact",
            "tenant_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "rent_monthly_chf": 1500.0,
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    resp = await client.put(
        f"/api/v1/leases/{lease.id}",
        json={"rent_monthly_chf": 1650.0, "status": "terminated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rent_monthly_chf"] == 1650.0
    assert body["status"] == "terminated"


@pytest.mark.asyncio
async def test_api_lease_summary(client, auth_headers, db_session, sample_building, admin_user):
    for i, (st, rent) in enumerate([("active", 2000.0), ("active", 1500.0), ("disputed", 800.0)]):
        await create_lease(
            db_session,
            sample_building.id,
            {
                "lease_type": "residential",
                "reference_code": f"SUM-API-{i}",
                "tenant_type": "contact",
                "tenant_id": uuid.uuid4(),
                "date_start": date(2024, 1, 1),
                "rent_monthly_chf": rent,
                "charges_monthly_chf": 200.0,
                "status": st,
            },
            created_by=admin_user.id,
        )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/lease-summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_leases"] == 3
    assert body["active_leases"] == 2
    assert body["monthly_rent_chf"] == 3500.0
    assert body["disputed_count"] == 1


@pytest.mark.asyncio
async def test_api_lease_building_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/leases", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_lease_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/leases/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_lease_rbac_diagnostician_read_only(client, diag_headers, db_session, sample_building, admin_user):
    lease = await create_lease(
        db_session,
        sample_building.id,
        {
            "lease_type": "residential",
            "reference_code": "RBAC-001",
            "tenant_type": "contact",
            "tenant_id": uuid.uuid4(),
            "date_start": date(2024, 1, 1),
            "status": "active",
        },
        created_by=admin_user.id,
    )
    await db_session.commit()

    # Can list
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/leases", headers=diag_headers)
    assert resp.status_code == 200

    # Can read
    resp = await client.get(f"/api/v1/leases/{lease.id}", headers=diag_headers)
    assert resp.status_code == 200

    # Cannot create
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/leases",
        json={
            "building_id": str(sample_building.id),
            "lease_type": "residential",
            "reference_code": "RBAC-FAIL",
            "tenant_type": "contact",
            "tenant_id": str(uuid.uuid4()),
            "date_start": "2024-01-01",
        },
        headers=diag_headers,
    )
    assert resp.status_code == 403

    # Cannot update
    resp = await client.put(f"/api/v1/leases/{lease.id}", json={"status": "terminated"}, headers=diag_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_lease_unauthorized(client):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/leases")
    assert resp.status_code in (401, 403)  # HTTPBearer(auto_error=False) → 401


@pytest.mark.asyncio
async def test_api_contact_lookup_scoped(client, auth_headers, db_session, sample_building):
    """Contact lookup is scoped to the building's organization."""
    from app.models.contact import Contact
    from app.models.organization import Organization

    # Create org + assign to building
    org = Organization(id=uuid.uuid4(), name="Lookup Org", type="property_management")
    db_session.add(org)
    await db_session.flush()
    sample_building.organization_id = org.id
    await db_session.flush()

    # Contact IN org — should be returned
    contact_in = Contact(
        id=uuid.uuid4(),
        organization_id=org.id,
        contact_type="person",
        name="Jean Dupont",
        email="jean@test.ch",
        is_active=True,
    )
    # Contact OUTSIDE org — should NOT be returned
    contact_out = Contact(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        contact_type="person",
        name="Jean Hors-Org",
        email="hors@test.ch",
        is_active=True,
    )
    db_session.add_all([contact_in, contact_out])
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contacts/lookup?q=Jean", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    names = [c["name"] for c in body]
    assert "Jean Dupont" in names
    assert "Jean Hors-Org" not in names


@pytest.mark.asyncio
async def test_api_contact_lookup_empty(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/contacts/lookup?q=nonexistent", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 0


@pytest.mark.asyncio
async def test_api_contact_lookup_building_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/contacts/lookup", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_contact_lookup_legacy_building_no_org(client, auth_headers, db_session, sample_building):
    """Building without organization_id returns empty list, not global annuaire."""
    from app.models.contact import Contact

    # Ensure building has no org (legacy state)
    sample_building.organization_id = None
    await db_session.flush()

    # Create a contact (not scoped to any org)
    db_session.add(
        Contact(
            id=uuid.uuid4(),
            contact_type="person",
            name="Ghost Contact",
            email="ghost@test.ch",
            is_active=True,
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/contacts/lookup", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 0  # must be empty, not the global annuaire
