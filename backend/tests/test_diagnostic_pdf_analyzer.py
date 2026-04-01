"""Tests for the Diagnostic PDF Analyzer service."""

import pytest

from app.services.diagnostic_pdf_analyzer import analyze_diagnostic_pdf

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_bytes(text: str) -> bytes:
    """Convert text to UTF-8 bytes simulating extracted PDF text."""
    return text.encode("utf-8")


# ---------------------------------------------------------------------------
# Document type detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_diagnostic_report_fr():
    """French diagnostic report is detected correctly."""
    text = _text_bytes(
        "Rapport de diagnostic amiante\n"
        "Bâtiment: Rue du Lac 1, 1000 Lausanne\n"
        "Date d'inspection: 15.03.2024\n"
        "Prélèvement n°1: fibre-ciment toiture\n"
        "Prélèvement n°2: joint de dilatation\n"
        "Prélèvement n°3: colle de carrelage\n"
        "Résultat: positif (chrysotile détecté)\n"
        "Échantillon S-001: 1200 mg/kg\n"
        "Échantillon S-002: négatif\n"
        "Échantillon S-003: 800 mg/kg\n"
    )
    result = await analyze_diagnostic_pdf(text)
    assert result["document_type"] == "diagnostic_report"
    assert "asbestos" in result["detected_pollutants"]
    assert result["has_samples_table"] is True
    assert result["confidence"] >= 0.85
    assert result["language"] == "fr"
    assert "Diagnostic" in result["summary"]


@pytest.mark.asyncio
async def test_detect_lab_result():
    """Lab result document is detected."""
    text = _text_bytes(
        "Bulletin d'analyse\nRésultats de laboratoire\nAnalyse par microscopie MET\nPCB: 85 mg/kg\nPlomb: 3200 mg/kg\n"
    )
    result = await analyze_diagnostic_pdf(text)
    assert result["document_type"] == "lab_result"
    assert "pcb" in result["detected_pollutants"]
    assert "lead" in result["detected_pollutants"]
    assert result["confidence"] >= 0.7


@pytest.mark.asyncio
async def test_detect_quote():
    """Quote/devis document is detected."""
    text = _text_bytes(
        "Devis n° 2024-156\nOffre de prix pour travaux amiante\nRetrait de fibre-ciment en toiture\nCHF 45'000.-\n"
    )
    result = await analyze_diagnostic_pdf(text)
    assert result["document_type"] == "quote"
    assert "asbestos" in result["detected_pollutants"]
    assert "fibre-ciment" in result["detected_materials"]


@pytest.mark.asyncio
async def test_detect_unknown_document():
    """Unclassifiable document returns 'unknown'."""
    text = _text_bytes("This is a random document with no diagnostic keywords.")
    result = await analyze_diagnostic_pdf(text)
    assert result["document_type"] == "unknown"
    assert result["detected_pollutants"] == []
    assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Pollutant extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_multiple_pollutants():
    """Multiple pollutants are detected from a single document."""
    text = _text_bytes(
        "Rapport de diagnostic polluants du bâtiment\n"
        "Amiante: chrysotile détecté dans les joints\n"
        "PCB dans les joints de dilatation: 120 mg/kg\n"
        "Plomb dans peinture: 8500 mg/kg\n"
        "HAP dans étanchéité: benzo[a]pyrène détecté\n"
        "Radon: 450 Bq/m3\n"
        "PFAS: PFOS détecté dans sol\n"
    )
    result = await analyze_diagnostic_pdf(text)
    assert set(result["detected_pollutants"]) == {"asbestos", "pcb", "lead", "hap", "radon", "pfas"}


@pytest.mark.asyncio
async def test_detect_materials():
    """Building materials are detected from text."""
    text = _text_bytes(
        "Rapport de diagnostic\n"
        "Matériaux inspectés:\n"
        "- fibre-ciment en toiture (eternit)\n"
        "- joints d'étanchéité fenêtres\n"
        "- dalles vinyl au sol\n"
        "- isolation thermique cave\n"
        "- colle de carrelage cuisine\n"
        "- peinture murs (crépis)\n"
    )
    result = await analyze_diagnostic_pdf(text)
    assert "fibre-ciment" in result["detected_materials"]
    assert "joints" in result["detected_materials"]
    assert "peinture" in result["detected_materials"]
    assert "isolant" in result["detected_materials"]
    assert "colle" in result["detected_materials"]


# ---------------------------------------------------------------------------
# Language detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_german_language():
    """German text is detected as 'de'."""
    text = _text_bytes(
        "Diagnosebericht\n"
        "Gebäude: Bahnhofstrasse 10, 8001 Zürich\n"
        "Schadstoffgutachten\n"
        "Probe Nr. 1: Asbest nachgewiesen\n"
        "Ergebnis: positiv\n"
        "Analyse durch Labor\n"
    )
    result = await analyze_diagnostic_pdf(text)
    assert result["language"] == "de"
    assert result["document_type"] == "diagnostic_report"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_content():
    """Empty content returns safe defaults."""
    result = await analyze_diagnostic_pdf(b"")
    assert result["document_type"] == "unknown"
    assert result["detected_pollutants"] == []
    assert result["detected_materials"] == []
    assert result["page_count"] == 0
    assert result["has_samples_table"] is False
    assert result["has_floor_plan"] is False
    assert result["confidence"] == 0.0
    assert result["summary"] == ""
