"""Tests for the hybrid document classifier pipeline."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.document_classifier_service import (
    DOCUMENT_TYPES,
    batch_classify,
    classify_and_update,
    classify_document,
)

# ── Pure function tests (no DB) ────────────────────────────────────────


class TestFilenameClassification:
    """Test Step 1: filename-based classification."""

    def test_asbestos_report_fr(self):
        result = classify_document("rapport_amiante_2024.pdf")
        assert result["document_type"] == "asbestos_report"
        assert result["confidence"] >= 0.3
        assert result["ai_generated"] is True

    def test_asbestos_report_de(self):
        result = classify_document("asbest_bericht_final.pdf")
        assert result["document_type"] == "asbestos_report"

    def test_lead_report_fr(self):
        result = classify_document("rapport_plomb_cuisine.pdf")
        assert result["document_type"] == "lead_report"

    def test_pcb_report(self):
        result = classify_document("rapport_PCB_joints.pdf")
        assert result["document_type"] == "pcb_report"

    def test_cfc_estimate(self):
        result = classify_document("devis_CFC_272.pdf")
        assert result["document_type"] == "cfc_estimate"

    def test_contractor_invoice_fr(self):
        result = classify_document("facture_entreprise_2024.pdf")
        assert result["document_type"] == "contractor_invoice"

    def test_contractor_invoice_de(self):
        result = classify_document("Rechnung_Nr_12345.pdf")
        assert result["document_type"] == "contractor_invoice"

    def test_cecb_certificate(self):
        result = classify_document("CECB_certificat_B.pdf")
        assert result["document_type"] == "cecb_certificate"

    def test_building_permit_fr(self):
        result = classify_document("permis_de_construire_2023.pdf")
        assert result["document_type"] == "building_permit"

    def test_site_report(self):
        result = classify_document("PV_chantier_mars_2024.pdf")
        assert result["document_type"] == "site_report"

    def test_insurance_policy(self):
        result = classify_document("police_assurance_ECA.pdf")
        assert result["document_type"] == "insurance_policy"

    def test_management_report(self):
        result = classify_document("rapport_gerance_2024.pdf")
        assert result["document_type"] == "management_report"


class TestContentClassification:
    """Test Step 2: content-based classification with OCR text."""

    def test_asbestos_content(self):
        text = "Ce rapport amiante concerne le diagnostic amiante du bâtiment situé à Lausanne."
        result = classify_document("document.pdf", content_text=text)
        assert result["document_type"] == "asbestos_report"
        assert result["method"] == "content"

    def test_pcb_content(self):
        text = "Analyse PCB des joints de fenêtres. Résultat: PCB > 50 mg/kg. PCB détecté."
        result = classify_document("scan_001.pdf", content_text=text)
        assert result["document_type"] == "pcb_report"

    def test_invoice_content(self):
        text = "Rechnung Nr. 2024-001. Gesamtbetrag: CHF 15'200.00. Rechnung zahlbar innert 30 Tagen."
        result = classify_document("doc.pdf", content_text=text)
        assert result["document_type"] == "contractor_invoice"

    def test_cecb_content(self):
        text = "Certificat CECB classe B. Le bâtiment atteint la classe GEAK B selon les critères."
        result = classify_document("cert.pdf", content_text=text)
        assert result["document_type"] == "cecb_certificate"


class TestHybridClassification:
    """Test Step 1+2: hybrid filename + content scoring."""

    def test_hybrid_boosts_confidence(self):
        result = classify_document(
            "rapport_amiante.pdf",
            content_text="Diagnostic amiante réalisé conformément à la norme FACH.",
        )
        assert result["document_type"] == "asbestos_report"
        assert result["method"] == "hybrid"
        assert result["confidence"] >= 0.7

    def test_hybrid_content_overrides_ambiguous_filename(self):
        # Generic filename, but content clearly PCB (multiple keyword hits)
        result = classify_document(
            "analyse_labo.pdf",
            content_text="Rapport PCB: analyse PCB des joints de fenêtres. PCB détecté dans les fugenmasse. Concentration PCB > 50 mg/kg.",
        )
        assert result["document_type"] == "pcb_report"


class TestLowConfidence:
    """Test Step 4: unclassified when confidence < 0.6."""

    def test_generic_filename_no_content(self):
        result = classify_document("file_12345.pdf")
        assert result["document_type"] == "unclassified"
        assert result["confidence"] < 0.6

    def test_unknown_extension(self):
        result = classify_document("data.xyz")
        assert result["document_type"] == "unclassified"

    def test_provides_candidates(self):
        result = classify_document("file_12345.pdf")
        assert isinstance(result["candidates"], list)


class TestResultStructure:
    """Test output dict structure."""

    def test_all_keys_present(self):
        result = classify_document("rapport_amiante.pdf")
        assert "document_type" in result
        assert "confidence" in result
        assert "method" in result
        assert "candidates" in result
        assert "ai_generated" in result
        assert "keywords_found" in result

    def test_candidates_structure(self):
        result = classify_document(
            "rapport_plomb.pdf",
            content_text="Analyse plomb réalisée sur peintures.",
        )
        for candidate in result["candidates"]:
            assert "type" in candidate
            assert "confidence" in candidate


class TestAllDocumentTypeKeywords:
    """Test that each of the 10 types is reachable via at least one keyword."""

    @pytest.mark.parametrize("dtype", list(DOCUMENT_TYPES.keys()))
    def test_type_reachable_via_keyword(self, dtype):
        """Each type should be classifiable from its first keyword."""
        first_keyword = DOCUMENT_TYPES[dtype]["keywords"][0]
        result = classify_document(f"document_{first_keyword}.pdf")
        # Should either match this type or at least appear in candidates
        matched = result["document_type"] == dtype
        in_candidates = any(c["type"] == dtype for c in result["candidates"])
        assert matched or in_candidates, f"Type {dtype} not reachable via keyword '{first_keyword}'"


# ── DB tests ───────────────────────────────────────────────────────────


def _make_doc(
    building_id: uuid.UUID,
    file_name: str = "file.pdf",
    document_type: str | None = None,
) -> Document:
    return Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path=f"/docs/{file_name}",
        file_name=file_name,
        mime_type="application/pdf",
        document_type=document_type,
    )


@pytest.mark.asyncio
async def test_classify_and_update_high_confidence(db_session: AsyncSession, sample_building):
    """classify_and_update updates document_type when confidence > 0.7."""
    doc = _make_doc(sample_building.id, "rapport_amiante_diagnostic.pdf")
    db_session.add(doc)
    await db_session.commit()

    result = await classify_and_update(db_session, doc.id)
    assert result["document_type"] == "asbestos_report"
    assert result["ai_generated"] is True

    # Verify the document was updated in DB
    await db_session.refresh(doc)
    # document_type should be set if confidence was high enough
    if result["confidence"] >= 0.7:
        assert doc.document_type == "asbestos_report"


@pytest.mark.asyncio
async def test_classify_and_update_not_found(db_session: AsyncSession):
    """classify_and_update raises ValueError for missing document."""
    with pytest.raises(ValueError, match="not found"):
        await classify_and_update(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_batch_classify_processes_unclassified(db_session: AsyncSession, sample_building):
    """batch_classify processes only unclassified (None/empty/other) documents."""
    # Already classified — should be skipped
    doc1 = _make_doc(sample_building.id, "rapport_amiante.pdf", document_type="asbestos_report")
    # Unclassified — should be processed
    doc2 = _make_doc(sample_building.id, "rapport_plomb_2024.pdf")
    doc3 = _make_doc(sample_building.id, "devis_CFC_272.pdf", document_type="other")
    db_session.add_all([doc1, doc2, doc3])
    await db_session.commit()

    results = await batch_classify(db_session, sample_building.id)
    # doc1 is already classified, so only doc2 and doc3 should be processed
    assert len(results) == 2


@pytest.mark.asyncio
async def test_batch_classify_empty_building(db_session: AsyncSession, sample_building):
    """batch_classify returns empty list for building with no unclassified docs."""
    results = await batch_classify(db_session, sample_building.id)
    assert results == []


# ── API endpoint tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_classify_single(client, db_session, sample_building, auth_headers):
    """POST /documents/{id}/classify returns classification."""
    doc = _make_doc(sample_building.id, "rapport_amiante.pdf")
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/documents/{doc.id}/classify",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_type"] == "asbestos_report"
    assert data["ai_generated"] is True


@pytest.mark.asyncio
async def test_api_classify_single_not_found(client, auth_headers):
    """POST /documents/{id}/classify returns 404 for missing document."""
    resp = await client.post(
        f"/api/v1/documents/{uuid.uuid4()}/classify",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_batch_classify(client, db_session, sample_building, auth_headers):
    """POST /buildings/{id}/documents/classify-all returns batch result."""
    doc = _make_doc(sample_building.id, "rapport_plomb.pdf")
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/documents/classify-all",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_processed" in data
    assert "classified_count" in data
    assert "results" in data


@pytest.mark.asyncio
async def test_api_batch_classify_nonexistent_building(client, auth_headers):
    """POST /buildings/{id}/documents/classify-all returns 404 for missing building."""
    resp = await client.post(
        f"/api/v1/buildings/{uuid.uuid4()}/documents/classify-all",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_list_document_types(client, auth_headers):
    """GET /documents/types returns all 10 document types."""
    resp = await client.get(
        "/api/v1/documents/types",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    assert all("type_key" in item for item in data)
    assert all("label_fr" in item for item in data)
    type_keys = {item["type_key"] for item in data}
    assert "asbestos_report" in type_keys
    assert "management_report" in type_keys
