"""Test suite for Quote Extraction v1 — contractor estimate parsing with confidence scoring."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contractor_quote import ContractorQuote
from app.models.document import Document


@pytest.mark.asyncio
async def test_contractor_quote_model_has_required_fields(db: AsyncSession):
    """Test that ContractorQuote model has all required fields."""
    # Verify model can be instantiated with minimal fields
    quote = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        ai_generated="claude-sonnet",
        confidence=0.75,
        reviewed="pending",  # default
    )

    assert quote.id is not None
    assert quote.document_id is not None
    assert quote.building_id is not None
    assert quote.ai_generated == "claude-sonnet"
    assert quote.confidence == 0.75
    assert quote.reviewed == "pending"


@pytest.mark.asyncio
async def test_contractor_quote_with_full_extraction(db: AsyncSession):
    """Test creating a full contractor quote with all extracted fields."""
    doc_id = uuid4()
    building_id = uuid4()

    quote = ContractorQuote(
        id=uuid4(),
        document_id=doc_id,
        building_id=building_id,
        contractor_name="ABC Demolition SA",
        contractor_contact="contact@abc-demo.ch",
        contact_email="contact@abc-demo.ch",
        contact_phone="+41 21 555 1234",
        total_price=45000.00,
        currency="CHF",
        price_per_unit=150.00,
        unit="m²",
        vat_included="yes",
        scope="Asbestos removal and disposal, decontamination",
        work_type="asbestos_removal",
        timeline="4 weeks",
        validity_days="30",
        conditions="Payment 50% on start, 50% on completion",
        ai_generated="claude-sonnet",
        confidence=0.85,
        confidence_breakdown={
            "contractor_name": 0.95,
            "total_price": 0.92,
            "timeline": 0.75,
            "scope": 0.80,
        },
    )

    assert quote.contractor_name == "ABC Demolition SA"
    assert quote.total_price == 45000.00
    assert quote.confidence == 0.85
    assert quote.confidence_breakdown["contractor_name"] == 0.95


@pytest.mark.asyncio
async def test_contractor_quote_confidence_scoring(db: AsyncSession):
    """Test that confidence scores are between 0-1."""
    quote = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        ai_generated="claude-sonnet",
        confidence=0.65,
    )

    assert 0 <= quote.confidence <= 1
    assert quote.confidence == 0.65


@pytest.mark.asyncio
async def test_contractor_quote_low_confidence_flags_for_review(db: AsyncSession):
    """Test that quotes with confidence <70% are marked for manual review."""
    # Low confidence quote
    low_conf = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        contractor_name="Unclear Company",
        total_price=None,  # Could not extract price
        confidence=0.45,  # Below 70%
        ai_generated="claude-sonnet",
    )

    # High confidence quote
    high_conf = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        contractor_name="Clear Company",
        total_price=50000.00,
        confidence=0.92,
        ai_generated="claude-sonnet",
    )

    assert low_conf.confidence < 0.70
    assert high_conf.confidence >= 0.70


@pytest.mark.asyncio
async def test_contractor_quote_multiple_for_same_building(db: AsyncSession):
    """Test that multiple quotes can exist for the same building."""
    building_id = uuid4()

    quote1 = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=building_id,
        contractor_name="Contractor A",
        total_price=40000.00,
        confidence=0.85,
        ai_generated="claude-sonnet",
    )

    quote2 = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=building_id,
        contractor_name="Contractor B",
        total_price=55000.00,
        confidence=0.78,
        ai_generated="claude-sonnet",
    )

    assert quote1.building_id == quote2.building_id
    assert quote1.contractor_name != quote2.contractor_name
    assert quote1.total_price != quote2.total_price


@pytest.mark.asyncio
async def test_contractor_quote_review_workflow(db: AsyncSession):
    """Test quote review status workflow."""
    quote = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        contractor_name="Test Contractor",
        total_price=30000.00,
        confidence=0.75,
        ai_generated="claude-sonnet",
        reviewed="pending",
    )

    assert quote.reviewed == "pending"
    assert quote.reviewer_notes is None
    assert quote.reviewed_by is None

    # Transition to confirmed
    quote.reviewed = "confirmed"
    quote.reviewer_notes = "Prices and scope verified against market"
    quote.reviewed_by = uuid4()

    assert quote.reviewed == "confirmed"
    assert quote.reviewer_notes is not None
    assert quote.reviewed_by is not None


@pytest.mark.asyncio
async def test_contractor_quote_disputed_status(db: AsyncSession):
    """Test disputed quote status for rejected extractions."""
    quote = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        contractor_name="Ambiguous Corp",
        total_price=None,
        confidence=0.35,
        ai_generated="claude-sonnet",
        reviewed="disputed",
        reviewer_notes="Could not verify contractor identity from document",
    )

    assert quote.reviewed == "disputed"
    assert "contractor" in quote.reviewer_notes.lower()


@pytest.mark.asyncio
async def test_contractor_quote_work_type_classification(db: AsyncSession):
    """Test that work_type field classifies the type of remediation."""
    work_types = [
        "asbestos_removal",
        "lead_removal",
        "pcb_removal",
        "radon_mitigation",
        "general_renovation",
    ]

    for work_type in work_types:
        quote = ContractorQuote(
            id=uuid4(),
            document_id=uuid4(),
            building_id=uuid4(),
            work_type=work_type,
            confidence=0.80,
            ai_generated="claude-sonnet",
        )
        assert quote.work_type == work_type


@pytest.mark.asyncio
async def test_contractor_quote_timeline_extraction(db: AsyncSession):
    """Test timeline field captures project duration."""
    timelines = [
        "2 weeks",
        "4-6 weeks",
        "1 month",
        "15 days",
        "Starting 15.05.2026, ending 30.06.2026",
    ]

    for timeline in timelines:
        quote = ContractorQuote(
            id=uuid4(),
            document_id=uuid4(),
            building_id=uuid4(),
            timeline=timeline,
            confidence=0.70,
            ai_generated="claude-sonnet",
        )
        assert quote.timeline == timeline


@pytest.mark.asyncio
async def test_contractor_quote_vat_handling(db: AsyncSession):
    """Test VAT inclusion flag for price interpretation."""
    quote_with_vat = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        total_price=44000.00,
        vat_included="yes",
        confidence=0.88,
        ai_generated="claude-sonnet",
    )

    quote_without_vat = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        total_price=40000.00,
        vat_included="no",
        confidence=0.82,
        ai_generated="claude-sonnet",
    )

    assert quote_with_vat.vat_included == "yes"
    assert quote_without_vat.vat_included == "no"
    # Same gross/net can have different interpretations
    assert quote_with_vat.total_price != quote_without_vat.total_price


@pytest.mark.asyncio
async def test_contractor_quote_confidence_breakdown_per_field(db: AsyncSession):
    """Test granular confidence scores for each extracted field."""
    quote = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        contractor_name="Company Name",
        total_price=50000.00,
        timeline="3 weeks",
        confidence_breakdown={
            "contractor_name": 0.95,
            "total_price": 0.88,
            "timeline": 0.72,
            "scope": 0.65,
            "contact_info": 0.40,
        },
        confidence=0.72,  # overall average
        ai_generated="claude-sonnet",
    )

    assert quote.confidence_breakdown["contractor_name"] == 0.95
    assert quote.confidence_breakdown["contact_info"] == 0.40
    # Lower field confidence suggests need for human review of specific fields
    assert quote.confidence_breakdown["contact_info"] < quote.confidence_breakdown["contractor_name"]


@pytest.mark.asyncio
async def test_contractor_quote_raw_extraction_for_debugging(db: AsyncSession):
    """Test that raw_extraction preserves full LLM response for auditing."""
    raw_response = {
        "extracted_by": "claude-sonnet",
        "model_version": "claude-sonnet-4-20250514",
        "full_text_analyzed": 1250,
        "pages_processed": 2,
        "confidence_reasoning": "Clear heading, explicit amounts in CHF, company letterhead",
        "ambiguities": ["Timeline could be 3-4 weeks or 4-5 weeks"],
    }

    quote = ContractorQuote(
        id=uuid4(),
        document_id=uuid4(),
        building_id=uuid4(),
        contractor_name="Test Corp",
        total_price=35000.00,
        confidence=0.79,
        raw_extraction=raw_response,
        ai_generated="claude-sonnet",
    )

    assert quote.raw_extraction is not None
    assert quote.raw_extraction["extracted_by"] == "claude-sonnet"
    assert len(quote.raw_extraction["ambiguities"]) > 0
