"""Tests for document checklist service (GED C)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.document import Document
from app.services.document_checklist_service import evaluate_document_checklist

# ── Helpers ──────────────────────────────────────────────────────────


def _make_building(
    construction_year: int | None = None,
    building_type: str = "residential",
    **kwargs,
) -> Building:
    return Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type=building_type,
        construction_year=construction_year,
        created_by=uuid.uuid4(),
        **kwargs,
    )


def _make_doc(building_id: uuid.UUID, document_type: str) -> Document:
    return Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path=f"/docs/{document_type}.pdf",
        file_name=f"{document_type}.pdf",
        document_type=document_type,
        uploaded_by=uuid.uuid4(),
    )


# ── Pre-1990 building requires asbestos report ──────────────────────


@pytest.mark.asyncio
async def test_pre1990_requires_asbestos(db_session: AsyncSession, sample_building):
    """Pre-1990 building should have asbestos_report as critical requirement."""
    # Update construction year
    sample_building.construction_year = 1975
    await db_session.commit()

    result = await evaluate_document_checklist(db_session, sample_building.id)

    asbestos_items = [i for i in result["items"] if i["document_type"] == "asbestos_report"]
    assert len(asbestos_items) == 1
    assert asbestos_items[0]["status"] == "missing"
    assert asbestos_items[0]["importance"] == "critical"
    assert "asbestos_report" in result["critical_missing"]


# ── Post-2006 building doesn't require lead report ──────────────────


@pytest.mark.asyncio
async def test_post2006_no_lead_requirement(db_session: AsyncSession, sample_building):
    """Post-2006 building should NOT require lead report."""
    sample_building.construction_year = 2010
    await db_session.commit()

    result = await evaluate_document_checklist(db_session, sample_building.id)

    lead_items = [i for i in result["items"] if i["document_type"] == "lead_report"]
    assert len(lead_items) == 1
    assert lead_items[0]["status"] == "not_applicable"


# ── Present document marks as complete ──────────────────────────────


@pytest.mark.asyncio
async def test_present_document_marks_complete(db_session: AsyncSession, sample_building):
    """When a required document is present, status should be 'present'."""
    sample_building.construction_year = 1980
    doc = _make_doc(sample_building.id, "asbestos_report")
    db_session.add(doc)
    await db_session.commit()

    result = await evaluate_document_checklist(db_session, sample_building.id)

    asbestos_items = [i for i in result["items"] if i["document_type"] == "asbestos_report"]
    assert len(asbestos_items) == 1
    assert asbestos_items[0]["status"] == "present"
    assert "asbestos_report" not in result["critical_missing"]


# ── Completion percentage calculation ──────────────────────────────


@pytest.mark.asyncio
async def test_completion_percentage(db_session: AsyncSession, sample_building):
    """Completion percentage should reflect present/required ratio."""
    sample_building.construction_year = 2020  # Fewer requirements
    sample_building.building_type = "industrial"  # No tenants
    await db_session.commit()

    result = await evaluate_document_checklist(db_session, sample_building.id)

    total_req = result["total_required"]
    total_pres = result["total_present"]
    assert total_req > 0
    expected_pct = round(total_pres / total_req * 100, 1)
    assert result["completion_pct"] == expected_pct


# ── Critical missing list ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_critical_missing_list(db_session: AsyncSession, sample_building):
    """Critical missing should only contain critical-importance missing docs."""
    sample_building.construction_year = 1965  # Triggers asbestos + pcb + lead + hap
    await db_session.commit()

    result = await evaluate_document_checklist(db_session, sample_building.id)

    # Both asbestos and pcb are critical and should be missing
    assert "asbestos_report" in result["critical_missing"]
    assert "pcb_report" in result["critical_missing"]

    # Non-critical items should NOT be in critical_missing
    for item in result["items"]:
        if item["importance"] != "critical" and item["status"] == "missing":
            assert item["document_type"] not in result["critical_missing"]


# ── PCB window ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pcb_only_1955_1975(db_session: AsyncSession, sample_building):
    """PCB requirement only applies to buildings 1955-1975."""
    # Outside window
    sample_building.construction_year = 1980
    await db_session.commit()

    result = await evaluate_document_checklist(db_session, sample_building.id)
    pcb_items = [i for i in result["items"] if i["document_type"] == "pcb_report"]
    assert pcb_items[0]["status"] == "not_applicable"


# ── Building ID in result ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_result_contains_building_id(db_session: AsyncSession, sample_building):
    """Result should contain the building ID."""
    result = await evaluate_document_checklist(db_session, sample_building.id)
    assert result["building_id"] == str(sample_building.id)
    assert "evaluated_at" in result
