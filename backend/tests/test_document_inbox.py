"""GED Inbox — Document inbox tests (service-layer + route-level)."""

import uuid

import pytest

from app.api.document_inbox import router as document_inbox_router
from app.main import app
from app.services.document_inbox_service import (
    classify_item,
    create_inbox_item,
    get_inbox_item,
    link_to_building,
    list_inbox,
    reject_item,
)

# Register router for HTTP tests (not yet in router.py hub file)
app.include_router(document_inbox_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_inbox_item(db_session):
    data = {
        "filename": "rapport-amiante.pdf",
        "file_url": "inbox/2026/03/rapport-amiante.pdf",
        "file_size": 102400,
        "content_type": "application/pdf",
        "source": "upload",
    }
    item = await create_inbox_item(db_session, data)
    assert item.id is not None
    assert item.status == "pending"
    assert item.filename == "rapport-amiante.pdf"


@pytest.mark.asyncio
async def test_create_inbox_item_with_user(db_session, admin_user):
    data = {
        "filename": "photo-facade.jpg",
        "file_url": "inbox/2026/03/photo-facade.jpg",
        "source": "email",
    }
    item = await create_inbox_item(db_session, data, uploaded_by=admin_user.id)
    assert item.uploaded_by_user_id == admin_user.id


@pytest.mark.asyncio
async def test_list_inbox_empty(db_session):
    items, total = await list_inbox(db_session)
    assert total == 0
    assert items == []


@pytest.mark.asyncio
async def test_list_inbox_with_items(db_session):
    for i in range(5):
        await create_inbox_item(
            db_session,
            {
                "filename": f"doc-{i}.pdf",
                "file_url": f"inbox/doc-{i}.pdf",
                "source": "upload",
            },
        )
    items, total = await list_inbox(db_session)
    assert total == 5
    assert len(items) == 5


@pytest.mark.asyncio
async def test_list_inbox_status_filter(db_session):
    item1 = await create_inbox_item(
        db_session,
        {
            "filename": "a.pdf",
            "file_url": "inbox/a.pdf",
            "source": "upload",
        },
    )
    await create_inbox_item(
        db_session,
        {
            "filename": "b.pdf",
            "file_url": "inbox/b.pdf",
            "source": "upload",
        },
    )
    # Reject item1
    await reject_item(db_session, item1, "spam")

    _pending, total_pending = await list_inbox(db_session, status_filter="pending")
    assert total_pending == 1
    _rejected, total_rejected = await list_inbox(db_session, status_filter="rejected")
    assert total_rejected == 1


@pytest.mark.asyncio
async def test_list_inbox_source_filter(db_session):
    await create_inbox_item(
        db_session,
        {
            "filename": "a.pdf",
            "file_url": "inbox/a.pdf",
            "source": "upload",
        },
    )
    await create_inbox_item(
        db_session,
        {
            "filename": "b.pdf",
            "file_url": "inbox/b.pdf",
            "source": "email",
        },
    )
    _upload_items, total = await list_inbox(db_session, source_filter="upload")
    assert total == 1


@pytest.mark.asyncio
async def test_list_inbox_pagination(db_session):
    for i in range(15):
        await create_inbox_item(
            db_session,
            {
                "filename": f"doc-{i}.pdf",
                "file_url": f"inbox/doc-{i}.pdf",
                "source": "upload",
            },
        )
    page1, total = await list_inbox(db_session, page=1, size=10)
    assert total == 15
    assert len(page1) == 10
    page2, _ = await list_inbox(db_session, page=2, size=10)
    assert len(page2) == 5


@pytest.mark.asyncio
async def test_get_inbox_item(db_session):
    item = await create_inbox_item(
        db_session,
        {
            "filename": "test.pdf",
            "file_url": "inbox/test.pdf",
            "source": "upload",
        },
    )
    fetched = await get_inbox_item(db_session, item.id)
    assert fetched is not None
    assert fetched.id == item.id


@pytest.mark.asyncio
async def test_get_inbox_item_not_found(db_session):
    result = await get_inbox_item(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_classify_item(db_session):
    item = await create_inbox_item(
        db_session,
        {
            "filename": "rapport.pdf",
            "file_url": "inbox/rapport.pdf",
            "source": "upload",
        },
    )
    classification = {"document_type": "diagnostic_report", "confidence": 0.92, "tags": ["amiante"]}
    result = await classify_item(db_session, item, classification)
    assert result.status == "classified"
    assert result.classification["document_type"] == "diagnostic_report"


@pytest.mark.asyncio
async def test_classify_does_not_downgrade_status(db_session):
    """Classifying a classified item keeps it classified, not back to pending."""
    item = await create_inbox_item(
        db_session,
        {
            "filename": "rapport.pdf",
            "file_url": "inbox/rapport.pdf",
            "source": "upload",
        },
    )
    await classify_item(db_session, item, {"document_type": "photo"})
    assert item.status == "classified"
    await classify_item(db_session, item, {"document_type": "report"})
    assert item.status == "classified"


@pytest.mark.asyncio
async def test_link_to_building(db_session, sample_building):
    item = await create_inbox_item(
        db_session,
        {
            "filename": "plan.pdf",
            "file_url": "inbox/plan.pdf",
            "file_size": 50000,
            "content_type": "application/pdf",
            "source": "api",
        },
    )
    result = await link_to_building(db_session, item, sample_building.id, document_type="plan")
    assert result.status == "linked"
    assert result.linked_building_id == sample_building.id
    assert result.linked_document_id is not None


@pytest.mark.asyncio
async def test_reject_item(db_session):
    item = await create_inbox_item(
        db_session,
        {
            "filename": "spam.exe",
            "file_url": "inbox/spam.exe",
            "source": "email",
        },
    )
    result = await reject_item(db_session, item, reason="Not a valid document")
    assert result.status == "rejected"
    assert result.notes == "Not a valid document"


@pytest.mark.asyncio
async def test_reject_item_no_reason(db_session):
    item = await create_inbox_item(
        db_session,
        {
            "filename": "unknown.bin",
            "file_url": "inbox/unknown.bin",
            "source": "upload",
        },
    )
    result = await reject_item(db_session, item)
    assert result.status == "rejected"
    assert result.notes is None


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route_create_inbox_item(client, auth_headers):
    resp = await client.post(
        "/api/v1/document-inbox",
        json={
            "filename": "route-test.pdf",
            "file_url": "inbox/route-test.pdf",
            "file_size": 1024,
            "content_type": "application/pdf",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["filename"] == "route-test.pdf"


@pytest.mark.asyncio
async def test_route_list_inbox(client, auth_headers):
    # Create a couple of items first
    for name in ["a.pdf", "b.pdf"]:
        await client.post(
            "/api/v1/document-inbox",
            json={"filename": name, "file_url": f"inbox/{name}"},
            headers=auth_headers,
        )
    resp = await client.get(
        "/api/v1/document-inbox",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_route_classify_item(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/document-inbox",
        json={"filename": "classify-me.pdf", "file_url": "inbox/classify-me.pdf"},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/document-inbox/{item_id}/classify",
        json={"document_type": "report", "confidence": 0.85},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "classified"


@pytest.mark.asyncio
async def test_route_reject_item(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/document-inbox",
        json={"filename": "reject-me.pdf", "file_url": "inbox/reject-me.pdf"},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/document-inbox/{item_id}/reject",
        json={"reason": "duplicate"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_route_link_item(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/document-inbox",
        json={
            "filename": "link-me.pdf",
            "file_url": "inbox/link-me.pdf",
            "content_type": "application/pdf",
        },
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/document-inbox/{item_id}/link",
        json={"building_id": str(sample_building.id), "document_type": "diagnostic_report"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "linked"
    assert data["linked_building_id"] == str(sample_building.id)
    assert data["linked_document_id"] is not None


@pytest.mark.asyncio
async def test_route_link_already_linked(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/document-inbox",
        json={"filename": "dup.pdf", "file_url": "inbox/dup.pdf"},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]
    # Link once
    await client.post(
        f"/api/v1/document-inbox/{item_id}/link",
        json={"building_id": str(sample_building.id)},
        headers=auth_headers,
    )
    # Try again
    resp = await client.post(
        f"/api/v1/document-inbox/{item_id}/link",
        json={"building_id": str(sample_building.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_route_get_inbox_item(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/document-inbox",
        json={"filename": "get-me.pdf", "file_url": "inbox/get-me.pdf"},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]
    resp = await client.get(
        f"/api/v1/document-inbox/{item_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id


@pytest.mark.asyncio
async def test_route_get_inbox_item_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/document-inbox/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404
