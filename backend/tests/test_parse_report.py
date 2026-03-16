"""Tests for the parse-report + apply-report flow (PDF diagnostic reports)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

import pytest

# --- Helpers ---

MOCK_PARSED_RESULT = {
    "samples": [
        {
            "sample_number": "E-01",
            "location": "Sous-sol",
            "material": "colle",
            "pollutant_type": "asbestos",
            "pollutant_subtype": "chrysotile",
            "result": "positive",
            "concentration": 5.0,
            "unit": "%",
        },
        {
            "sample_number": "E-02",
            "location": "Cuisine",
            "material": "dalle",
            "pollutant_type": "pcb",
            "pollutant_subtype": None,
            "result": "negative",
            "concentration": 12.0,
            "unit": "mg/kg",
        },
    ],
    "laboratory": "Labo Suisse SA",
    "report_number": "R-2024-001",
    "date": "2024-06-15",
    "conclusion": "Presence confirmed in basement.",
}

MOCK_EXTRACTED_TEXT = "A" * 300  # Long enough to pass the 200-char threshold


async def _create_diagnostic(client, diag_headers, building_id):
    """Helper: create a diagnostic and return its id."""
    resp = await client.post(
        f"/api/v1/buildings/{building_id}/diagnostics",
        json={"diagnostic_type": "asbestos", "date_inspection": "2024-01-15"},
        headers=diag_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _fake_pdf_upload():
    """Create a fake PDF file for upload (UploadFile-compatible tuple)."""
    return [("file", ("report.pdf", BytesIO(b"%PDF-1.4 fake content"), "application/pdf"))]


# --- parse-report tests ---


@pytest.mark.asyncio
async def test_parse_report_returns_samples(client, diag_headers, sample_building):
    """parse-report should return ParseReportResponse with samples extracted from PDF."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    with (
        patch("app.ml.pdf_parser.extract_text_from_pdf", return_value=MOCK_EXTRACTED_TEXT),
        patch("app.ml.pdf_parser.parse_diagnostic_report", return_value=MOCK_PARSED_RESULT),
    ):
        resp = await client.post(
            f"/api/v1/diagnostics/{diag_id}/parse-report",
            files=_fake_pdf_upload(),
            headers=diag_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnostic_id"] == diag_id
    assert len(data["samples"]) == 2
    assert data["samples"][0]["sample_number"] == "E-01"
    assert data["samples"][0]["pollutant_type"] == "asbestos"
    assert data["samples"][1]["sample_number"] == "E-02"
    assert data["metadata"]["laboratory"] == "Labo Suisse SA"
    assert data["text_length"] == len(MOCK_EXTRACTED_TEXT)
    assert data["warnings"] == []


@pytest.mark.asyncio
async def test_parse_report_does_not_persist(client, diag_headers, sample_building):
    """parse-report should NOT create any Sample objects in DB."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    with (
        patch("app.ml.pdf_parser.extract_text_from_pdf", return_value=MOCK_EXTRACTED_TEXT),
        patch("app.ml.pdf_parser.parse_diagnostic_report", return_value=MOCK_PARSED_RESULT),
    ):
        resp = await client.post(
            f"/api/v1/diagnostics/{diag_id}/parse-report",
            files=_fake_pdf_upload(),
            headers=diag_headers,
        )

    assert resp.status_code == 200
    assert len(resp.json()["samples"]) == 2

    # Verify no samples were persisted
    diag_resp = await client.get(f"/api/v1/diagnostics/{diag_id}", headers=diag_headers)
    assert diag_resp.status_code == 200
    assert len(diag_resp.json()["samples"]) == 0


@pytest.mark.asyncio
async def test_parse_report_non_pdf_returns_400(client, diag_headers, sample_building):
    """parse-report should reject non-PDF files with 400."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    resp = await client.post(
        f"/api/v1/diagnostics/{diag_id}/parse-report",
        files=[("file", ("report.txt", BytesIO(b"not a pdf"), "text/plain"))],
        headers=diag_headers,
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_parse_report_empty_pdf_returns_warnings(client, diag_headers, sample_building):
    """parse-report with empty/unreadable PDF should return warnings."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    with (
        patch("app.ml.pdf_parser.extract_text_from_pdf", return_value=""),
        patch("app.ml.pdf_parser.extract_text_with_ocr", return_value=""),
    ):
        resp = await client.post(
            f"/api/v1/diagnostics/{diag_id}/parse-report",
            files=_fake_pdf_upload(),
            headers=diag_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["text_length"] == 0
    assert len(data["warnings"]) > 0
    assert "Could not extract text" in data["warnings"][0]
    assert data["samples"] == []


@pytest.mark.asyncio
async def test_parse_report_not_found(client, diag_headers):
    """parse-report for non-existent diagnostic returns 404."""
    fake_id = str(uuid4())
    resp = await client.post(
        f"/api/v1/diagnostics/{fake_id}/parse-report",
        files=_fake_pdf_upload(),
        headers=diag_headers,
    )
    assert resp.status_code == 404


# --- apply-report tests ---


@pytest.mark.asyncio
async def test_apply_report_creates_samples(client, diag_headers, sample_building):
    """apply-report should create Sample objects in DB."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    payload = {
        "samples": [
            {
                "sample_number": "E-01",
                "location": "Sous-sol",
                "material": "colle",
                "pollutant_type": "asbestos",
                "pollutant_subtype": "chrysotile",
                "concentration": 5.0,
                "unit": "%",
            },
        ],
    }
    resp = await client.post(
        f"/api/v1/diagnostics/{diag_id}/apply-report",
        json=payload,
        headers=diag_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["sample_number"] == "E-01"
    assert data[0]["pollutant_type"] == "asbestos"
    assert data[0]["diagnostic_id"] == diag_id

    # Verify sample is actually persisted
    diag_resp = await client.get(f"/api/v1/diagnostics/{diag_id}", headers=diag_headers)
    assert len(diag_resp.json()["samples"]) == 1


@pytest.mark.asyncio
async def test_apply_report_updates_metadata(client, diag_headers, sample_building):
    """apply-report should update diagnostic metadata fields."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    payload = {
        "samples": [],
        "laboratory": "Labo Suisse SA",
        "laboratory_report_number": "R-2024-001",
        "date_report": "2024-06-15",
        "summary": "Test summary",
        "conclusion": "Presence confirmed.",
    }
    resp = await client.post(
        f"/api/v1/diagnostics/{diag_id}/apply-report",
        json=payload,
        headers=diag_headers,
    )
    assert resp.status_code == 200

    # Verify metadata was updated on diagnostic
    diag_resp = await client.get(f"/api/v1/diagnostics/{diag_id}", headers=diag_headers)
    diag_data = diag_resp.json()
    assert diag_data["laboratory"] == "Labo Suisse SA"
    assert diag_data["laboratory_report_number"] == "R-2024-001"
    assert diag_data["date_report"] == "2024-06-15"
    assert diag_data["summary"] == "Test summary"
    assert diag_data["conclusion"] == "Presence confirmed."


@pytest.mark.asyncio
async def test_apply_report_empty_samples(client, diag_headers, sample_building):
    """apply-report with empty samples list should succeed (metadata-only update)."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    resp = await client.post(
        f"/api/v1/diagnostics/{diag_id}/apply-report",
        json={"samples": []},
        headers=diag_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_apply_report_not_found(client, diag_headers):
    """apply-report for non-existent diagnostic returns 404."""
    fake_id = str(uuid4())
    resp = await client.post(
        f"/api/v1/diagnostics/{fake_id}/apply-report",
        json={"samples": []},
        headers=diag_headers,
    )
    assert resp.status_code == 404


# --- Full flow test ---


@pytest.mark.asyncio
async def test_full_parse_then_apply_flow(client, diag_headers, sample_building):
    """End-to-end: parse a PDF, then apply the extracted data."""
    diag_id = await _create_diagnostic(client, diag_headers, sample_building.id)

    # Step 1: Parse
    with (
        patch("app.ml.pdf_parser.extract_text_from_pdf", return_value=MOCK_EXTRACTED_TEXT),
        patch("app.ml.pdf_parser.parse_diagnostic_report", return_value=MOCK_PARSED_RESULT),
    ):
        parse_resp = await client.post(
            f"/api/v1/diagnostics/{diag_id}/parse-report",
            files=_fake_pdf_upload(),
            headers=diag_headers,
        )

    assert parse_resp.status_code == 200
    parsed = parse_resp.json()
    assert len(parsed["samples"]) == 2

    # Step 2: Apply (user could modify data here; we pass as-is)
    apply_payload = {
        "samples": parsed["samples"],
        "laboratory": parsed["metadata"].get("laboratory"),
        "laboratory_report_number": parsed["metadata"].get("report_number"),
        "conclusion": parsed["metadata"].get("conclusion"),
    }
    apply_resp = await client.post(
        f"/api/v1/diagnostics/{diag_id}/apply-report",
        json=apply_payload,
        headers=diag_headers,
    )
    assert apply_resp.status_code == 200
    created = apply_resp.json()
    assert len(created) == 2

    # Verify everything is persisted
    diag_resp = await client.get(f"/api/v1/diagnostics/{diag_id}", headers=diag_headers)
    diag_data = diag_resp.json()
    assert len(diag_data["samples"]) == 2
    assert diag_data["laboratory"] == "Labo Suisse SA"
    assert diag_data["conclusion"] == "Presence confirmed in basement."
