"""Tests for document classification service and API."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.services.document_classification_service import (
    classify_building_documents,
    classify_document,
    get_classification_summary,
    suggest_missing_documents,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_doc(
    building_id: uuid.UUID,
    file_name: str = "file.pdf",
    mime_type: str = "application/pdf",
    document_type: str | None = None,
    uploaded_by: uuid.UUID | None = None,
) -> Document:
    return Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path=f"/docs/{file_name}",
        file_name=file_name,
        mime_type=mime_type,
        document_type=document_type,
        uploaded_by=uploaded_by,
    )


def _make_diagnostic(building_id: uuid.UUID, diagnostic_type: str) -> Diagnostic:
    return Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=diagnostic_type,
        status="completed",
    )


# ── Single document classification ──────────────────────────────────────


@pytest.mark.asyncio
async def test_classify_explicit_document_type(db_session: AsyncSession, sample_building):
    """document_type field takes priority and gives high confidence."""
    doc = _make_doc(sample_building.id, "random.pdf", document_type="lab_result")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "lab_result"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_classify_diagnostic_report_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'rapport' maps to diagnostic_report."""
    doc = _make_doc(sample_building.id, "rapport_amiante_2024.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "diagnostic_report"
    assert result.confidence == 0.7


@pytest.mark.asyncio
async def test_classify_lab_result_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'analyse' maps to lab_result."""
    doc = _make_doc(sample_building.id, "analyse_labo_pcb.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "lab_result"
    assert result.confidence == 0.7


@pytest.mark.asyncio
async def test_classify_remediation_plan_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'assainissement' maps to remediation_plan."""
    doc = _make_doc(sample_building.id, "plan_assainissement_plomb.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    # 'plan' pattern comes after 'assainissement' in priority, but
    # 'assainissement' pattern is checked first → remediation_plan
    assert result.document_category == "remediation_plan"
    assert result.confidence == 0.7


@pytest.mark.asyncio
async def test_classify_insurance_doc_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'assurance' maps to insurance_doc."""
    doc = _make_doc(sample_building.id, "assurance_batiment.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "insurance_doc"


@pytest.mark.asyncio
async def test_classify_invoice_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'facture' maps to invoice."""
    doc = _make_doc(sample_building.id, "facture_travaux.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "invoice"


@pytest.mark.asyncio
async def test_classify_photo_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'photo' maps to photo."""
    doc = _make_doc(sample_building.id, "photo_facade.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "photo"


@pytest.mark.asyncio
async def test_classify_technical_plan_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'plan' (without remediation keywords) maps to technical_plan."""
    doc = _make_doc(sample_building.id, "plan_etage_2.dwg", mime_type="application/dwg")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "technical_plan"


@pytest.mark.asyncio
async def test_classify_report_en_filename(db_session: AsyncSession, sample_building):
    """English filename 'report' maps to diagnostic_report."""
    doc = _make_doc(sample_building.id, "asbestos_report_final.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "diagnostic_report"


@pytest.mark.asyncio
async def test_classify_by_mime_type_fallback(db_session: AsyncSession, sample_building):
    """When no filename or document_type match, fall back to mime_type."""
    doc = _make_doc(sample_building.id, "untitled.jpg", mime_type="image/jpeg")
    # 'untitled' doesn't match any filename pattern, so mime_type fallback applies
    # Actually let's use a truly non-matching name
    doc.file_name = "data_12345.jpg"
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "photo"
    assert result.confidence == 0.5


@pytest.mark.asyncio
async def test_classify_unknown_file(db_session: AsyncSession, sample_building):
    """Unknown file type falls back to 'other' with low confidence."""
    doc = _make_doc(sample_building.id, "data.xyz", mime_type="application/octet-stream")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "other"
    assert result.confidence == 0.5


# ── Pollutant tag extraction ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pollutant_tags_from_filename(db_session: AsyncSession, sample_building):
    """Pollutant keywords in filename are extracted as tags."""
    doc = _make_doc(sample_building.id, "rapport_amiante_pcb.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert "asbestos" in result.pollutant_tags
    assert "pcb" in result.pollutant_tags


@pytest.mark.asyncio
async def test_pollutant_tags_from_diagnostic(db_session: AsyncSession, sample_building):
    """Pollutant types from linked diagnostics are included in tags."""
    diag = _make_diagnostic(sample_building.id, "asbestos")
    doc = _make_doc(sample_building.id, "generic_document.pdf")
    db_session.add_all([diag, doc])
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert "asbestos" in result.pollutant_tags


@pytest.mark.asyncio
async def test_pollutant_tags_lead_french(db_session: AsyncSession, sample_building):
    """French pollutant keyword 'plomb' extracts lead tag."""
    doc = _make_doc(sample_building.id, "analyse_plomb_cuisine.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert "lead" in result.pollutant_tags


@pytest.mark.asyncio
async def test_pollutant_tags_radon(db_session: AsyncSession, sample_building):
    """Radon keyword in filename is detected."""
    doc = _make_doc(sample_building.id, "mesure_radon_sous-sol.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert "radon" in result.pollutant_tags


# ── Building-wide classification ────────────────────────────────────────


@pytest.mark.asyncio
async def test_classify_building_documents_multiple(db_session: AsyncSession, sample_building):
    """Classify multiple documents for a building."""
    docs = [
        _make_doc(sample_building.id, "rapport_amiante.pdf"),
        _make_doc(sample_building.id, "photo_facade.jpg", mime_type="image/jpeg"),
        _make_doc(sample_building.id, "facture.pdf"),
    ]
    db_session.add_all(docs)
    await db_session.commit()

    results = await classify_building_documents(db_session, sample_building.id)
    assert len(results) == 3
    categories = {r.document_category for r in results}
    assert "diagnostic_report" in categories
    assert "photo" in categories
    assert "invoice" in categories


@pytest.mark.asyncio
async def test_classify_building_no_documents(db_session: AsyncSession, sample_building):
    """Building with no documents returns empty list."""
    results = await classify_building_documents(db_session, sample_building.id)
    assert results == []


# ── Summary aggregation ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_category_counts(db_session: AsyncSession, sample_building):
    """Summary shows correct category counts."""
    docs = [
        _make_doc(sample_building.id, "rapport1.pdf"),
        _make_doc(sample_building.id, "rapport2.pdf"),
        _make_doc(sample_building.id, "photo.jpg", mime_type="image/jpeg"),
    ]
    db_session.add_all(docs)
    await db_session.commit()

    summary = await get_classification_summary(db_session, sample_building.id)
    assert summary.total_documents == 3
    assert summary.category_counts.get("diagnostic_report") == 2
    assert summary.category_counts.get("photo") == 1


@pytest.mark.asyncio
async def test_summary_coverage_gaps(db_session: AsyncSession, sample_building):
    """Summary identifies missing essential categories."""
    # Only add a diagnostic_report — lab_result, remediation_plan, compliance_certificate are gaps
    doc = _make_doc(sample_building.id, "rapport.pdf")
    db_session.add(doc)
    await db_session.commit()

    summary = await get_classification_summary(db_session, sample_building.id)
    assert "lab_result" in summary.coverage_gaps
    assert "remediation_plan" in summary.coverage_gaps
    assert "compliance_certificate" in summary.coverage_gaps
    assert "diagnostic_report" not in summary.coverage_gaps


@pytest.mark.asyncio
async def test_summary_pollutant_coverage(db_session: AsyncSession, sample_building):
    """Summary shows pollutant coverage based on diagnostics."""
    diag = _make_diagnostic(sample_building.id, "asbestos")
    doc = _make_doc(sample_building.id, "rapport_amiante.pdf")
    db_session.add_all([diag, doc])
    await db_session.commit()

    summary = await get_classification_summary(db_session, sample_building.id)
    assert summary.pollutant_coverage.get("asbestos") is True


# ── Missing document suggestions ────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_missing_remediation_plan(db_session: AsyncSession, sample_building):
    """Building with asbestos diagnostic but no remediation plan triggers suggestion."""
    diag = _make_diagnostic(sample_building.id, "asbestos")
    doc = _make_doc(sample_building.id, "rapport_amiante.pdf")
    db_session.add_all([diag, doc])
    await db_session.commit()

    suggestions = await suggest_missing_documents(db_session, sample_building.id)
    remediation_suggestions = [s for s in suggestions if s.category == "remediation_plan"]
    assert len(remediation_suggestions) >= 1
    assert remediation_suggestions[0].pollutant == "asbestos"


@pytest.mark.asyncio
async def test_suggest_missing_no_diagnostics(db_session: AsyncSession, sample_building):
    """Building with no diagnostics gets no pollutant-specific suggestions."""
    suggestions = await suggest_missing_documents(db_session, sample_building.id)
    # No diagnostics → no building_pollutants → no suggestions
    assert len(suggestions) == 0


@pytest.mark.asyncio
async def test_suggest_missing_insurance(db_session: AsyncSession, sample_building):
    """Building with pollutant diagnostics but no insurance doc gets suggestion."""
    diag = _make_diagnostic(sample_building.id, "pcb")
    db_session.add(diag)
    await db_session.commit()

    suggestions = await suggest_missing_documents(db_session, sample_building.id)
    insurance = [s for s in suggestions if s.category == "insurance_doc"]
    assert len(insurance) == 1


# ── Edge cases ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classify_empty_filename(db_session: AsyncSession, sample_building):
    """Document with empty filename falls back to mime_type."""
    doc = _make_doc(sample_building.id, "", mime_type="image/png")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "photo"
    assert result.confidence == 0.5


@pytest.mark.asyncio
async def test_classify_nonexistent_document(db_session: AsyncSession, sample_building):
    """Classifying a non-existent document raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await classify_document(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_classify_compliance_certificate_by_filename(db_session: AsyncSession, sample_building):
    """Filename containing 'certificat' maps to compliance_certificate."""
    doc = _make_doc(sample_building.id, "certificat_conformite_2024.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_document(db_session, doc.id)
    assert result.document_category == "compliance_certificate"
    assert result.confidence == 0.7


# ── API endpoint tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_classify_endpoint(client, db_session, sample_building, auth_headers):
    """GET /buildings/{id}/documents/classify returns classifications."""
    doc = _make_doc(sample_building.id, "rapport_amiante.pdf")
    db_session.add(doc)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/documents/classify",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["document_category"] == "diagnostic_report"


@pytest.mark.asyncio
async def test_api_classification_summary_endpoint(client, db_session, sample_building, auth_headers):
    """GET /buildings/{id}/documents/classification-summary returns summary."""
    doc = _make_doc(sample_building.id, "rapport.pdf")
    db_session.add(doc)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/documents/classification-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 1
    assert "category_counts" in data


@pytest.mark.asyncio
async def test_api_missing_documents_endpoint(client, db_session, sample_building, auth_headers):
    """GET /buildings/{id}/documents/missing-documents returns suggestions."""
    diag = _make_diagnostic(sample_building.id, "asbestos")
    db_session.add(diag)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/documents/missing-documents",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_api_classify_nonexistent_building(client, auth_headers):
    """Classify endpoint returns 404 for non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/documents/classify",
        headers=auth_headers,
    )
    assert resp.status_code == 404
