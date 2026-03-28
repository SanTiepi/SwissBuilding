"""BatiConnect — Mise en concurrence encadree: RFQ intelligence service.

Generates pre-filled tenders from building dossier data, manages invitations,
handles quote submission with PDF extraction placeholder, produces neutral
comparisons, and records attribution.
"""

import logging
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.rfq import (
    TenderComparison,
    TenderInvitation,
    TenderQuote,
    TenderRequest,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Work type to pollutant mapping
# ---------------------------------------------------------------------------
_WORK_TYPE_POLLUTANTS: dict[str, list[str]] = {
    "asbestos_removal": ["asbestos"],
    "pcb_removal": ["pcb"],
    "lead_removal": ["lead"],
    "hap_removal": ["hap"],
    "radon_mitigation": ["radon"],
    "pfas_remediation": ["pfas"],
    "multi_pollutant": ["asbestos", "pcb", "lead", "hap", "radon", "pfas"],
}


# ---------------------------------------------------------------------------
# Generate RFQ draft
# ---------------------------------------------------------------------------


async def generate_rfq_draft(
    db: AsyncSession,
    building_id: UUID,
    work_type: str,
    created_by_id: UUID,
    org_id: UUID | None = None,
    title: str | None = None,
    description: str | None = None,
    deadline_submission: datetime | None = None,
    planned_start_date=None,
    planned_end_date=None,
    attachments_manual: list | None = None,
) -> TenderRequest:
    """Generate a pre-filled RFQ from building dossier data.

    - Pulls building summary from passport_service
    - Pulls relevant diagnostics for the work_type
    - Auto-attaches relevant documents and diagnostic reports
    - Generates scope_summary from building data
    """
    # 1. Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")

    # 2. Get passport summary for scope context
    passport_summary = None
    try:
        from app.services.passport_service import get_passport_summary

        passport_summary = await get_passport_summary(db, building_id)
    except Exception as e:
        logger.warning("Failed to load passport for building %s: %s", building_id, e)

    # 3. Find relevant diagnostics for the work type
    pollutants = _WORK_TYPE_POLLUTANTS.get(work_type, [])
    diagnostics_result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building_id).order_by(Diagnostic.date.desc())
    )
    all_diagnostics = list(diagnostics_result.scalars().all())
    relevant_diagnostic_ids = [str(d.id) for d in all_diagnostics]

    # 4. Find relevant documents
    docs_result = await db.execute(
        select(Document).where(Document.building_id == building_id).order_by(Document.created_at.desc())
    )
    all_docs = list(docs_result.scalars().all())
    relevant_doc_ids = [str(d.id) for d in all_docs]

    # 5. Build scope summary
    scope_parts = []
    building_name = building.name or building.address or str(building_id)
    scope_parts.append(f"Building: {building_name}")

    if pollutants:
        scope_parts.append(f"Pollutants: {', '.join(pollutants)}")

    if passport_summary:
        grade = passport_summary.get("passport_grade", "N/A")
        scope_parts.append(f"Passport grade: {grade}")

        completeness = passport_summary.get("completeness", {})
        if isinstance(completeness, dict):
            overall = completeness.get("overall_score")
            if overall is not None:
                scope_parts.append(f"Completeness: {overall:.0%}")

        readiness = passport_summary.get("readiness", {})
        if isinstance(readiness, dict):
            tender_readiness = readiness.get("tender", {})
            if isinstance(tender_readiness, dict):
                tender_status = tender_readiness.get("status", "unknown")
                scope_parts.append(f"Tender readiness: {tender_status}")

        pollutant_coverage = passport_summary.get("pollutant_coverage", {})
        if isinstance(pollutant_coverage, dict) and pollutants:
            covered = [p for p in pollutants if pollutant_coverage.get(p)]
            if covered:
                scope_parts.append(f"Diagnosed pollutants: {', '.join(covered)}")

    scope_parts.append(f"Diagnostics attached: {len(relevant_diagnostic_ids)}")
    scope_parts.append(f"Documents attached: {len(relevant_doc_ids)}")

    scope_summary = "\n".join(scope_parts)

    # 6. Auto-generate title if not provided
    if not title:
        work_label = work_type.replace("_", " ").title()
        title = f"{work_label} — {building_name}"

    # 7. Create the tender request
    tender = TenderRequest(
        building_id=building_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        title=title,
        description=description,
        scope_summary=scope_summary,
        work_type=work_type,
        deadline_submission=deadline_submission,
        planned_start_date=planned_start_date,
        planned_end_date=planned_end_date,
        status="draft",
        attachments_auto={"diagnostic_ids": relevant_diagnostic_ids, "document_ids": relevant_doc_ids},
        attachments_manual=attachments_manual or [],
    )
    db.add(tender)
    await db.flush()

    # Auto-create BuildingCase for this tender (V3 doctrine: BuildingCase = operating root)
    case = BuildingCase(
        building_id=building_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        case_type="tender",
        title=title,
        description=description,
        state="draft",
        tender_id=tender.id,
        priority="medium",
    )
    db.add(case)
    await db.flush()

    await db.refresh(tender)
    return tender


# ---------------------------------------------------------------------------
# Send tender invitations
# ---------------------------------------------------------------------------


async def send_tender(
    db: AsyncSession,
    tender_id: UUID,
    contractor_org_ids: list[UUID],
) -> list[TenderInvitation]:
    """Send tender invitations to selected contractor organizations.

    Creates a TenderInvitation for each contractor with a unique access token.
    Updates tender status to 'sent'.
    """
    result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    tender = result.scalar_one_or_none()
    if not tender:
        raise ValueError("Tender not found")
    if tender.status not in ("draft", "sent"):
        raise ValueError(f"Cannot send tender in status '{tender.status}'")

    now = datetime.now(UTC)
    invitations = []
    for org_id in contractor_org_ids:
        invitation = TenderInvitation(
            tender_id=tender_id,
            contractor_org_id=org_id,
            status="pending",
            sent_at=now,
            access_token=secrets.token_urlsafe(48),
        )
        db.add(invitation)
        invitations.append(invitation)

    tender.status = "sent"
    await db.flush()
    for inv in invitations:
        await db.refresh(inv)
    return invitations


# ---------------------------------------------------------------------------
# Submit quote
# ---------------------------------------------------------------------------


async def submit_quote(
    db: AsyncSession,
    tender_id: UUID,
    quote_data: dict,
    document_id: UUID | None = None,
) -> TenderQuote:
    """Submit a quote for a tender.

    If document_id is provided, marks extracted_data as pending extraction.
    Updates the associated invitation status if invitation_id is provided.
    """
    result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    tender = result.scalar_one_or_none()
    if not tender:
        raise ValueError("Tender not found")
    if tender.status not in ("sent", "collecting"):
        raise ValueError(f"Cannot submit quote for tender in status '{tender.status}'")

    # Move to collecting if first quote
    if tender.status == "sent":
        tender.status = "collecting"

    now = datetime.now(UTC)
    quote = TenderQuote(
        tender_id=tender_id,
        invitation_id=quote_data.get("invitation_id"),
        contractor_org_id=quote_data["contractor_org_id"],
        total_amount_chf=quote_data.get("total_amount_chf"),
        currency=quote_data.get("currency", "CHF"),
        scope_description=quote_data.get("scope_description"),
        exclusions=quote_data.get("exclusions"),
        inclusions=quote_data.get("inclusions"),
        estimated_duration_days=quote_data.get("estimated_duration_days"),
        validity_date=quote_data.get("validity_date"),
        document_id=document_id,
        status="received",
        submitted_at=now,
    )

    if document_id:
        quote.extracted_data = {"status": "pending_extraction"}

    db.add(quote)

    # Update invitation status if provided
    invitation_id = quote_data.get("invitation_id")
    if invitation_id:
        inv_result = await db.execute(select(TenderInvitation).where(TenderInvitation.id == invitation_id))
        invitation = inv_result.scalar_one_or_none()
        if invitation:
            invitation.status = "accepted"
            invitation.responded_at = now

    await db.flush()
    await db.refresh(quote)

    # Record partner trust signal: quote submitted = delivery_success observation
    await _record_trust_signal_for_tender(
        db,
        contractor_org_id=quote_data["contractor_org_id"],
        tender_id=tender_id,
        signal_type="delivery_success",
        notes="Quote submitted for tender",
    )

    return quote


# ---------------------------------------------------------------------------
# Extract quote data (placeholder)
# ---------------------------------------------------------------------------


async def extract_quote_data(
    db: AsyncSession,
    quote_id: UUID,
    text: str | None = None,
) -> dict:
    """Extract structured data from a quote PDF.

    If ``text`` is provided (OCR'd PDF content), runs the rule-based extraction
    pipeline and returns a draft extraction dict (parse -> review -> apply).
    If ``text`` is None, returns a structured template from existing quote fields.

    The caller must explicitly call ``apply_to_tender_quote`` after human review.
    """
    result = await db.execute(select(TenderQuote).where(TenderQuote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise ValueError("Quote not found")

    # If OCR text is provided, run the extraction pipeline
    if text:
        from app.services.quote_extraction_service import extract_from_document

        extraction = await extract_from_document(
            db,
            document_id=quote.document_id,
            text=text,
            tender_id=quote.tender_id,
        )
        # Store pending extraction on the quote (draft, not applied)
        quote.extracted_data = {
            "status": "pending_review",
            "extraction": extraction,
        }
        await db.flush()
        await db.refresh(quote)

        # Record evidence_clean signal: extraction succeeded without error
        await _record_trust_signal_for_tender(
            db,
            contractor_org_id=quote.contractor_org_id,
            tender_id=quote.tender_id,
            signal_type="evidence_clean",
            notes="Quote PDF extracted cleanly",
        )

        return extraction

    # Fallback: return structured template from existing fields
    extraction = {
        "extraction_id": None,
        "status": "draft",
        "confidence": 1.0,  # 1.0 since we use existing structured fields
        "extracted": {
            "contractor": {"name": None, "address": None, "contact": None},
            "quote_type": "unknown",
            "quote_reference": None,
            "quote_date": None,
            "validity_date": quote.validity_date.isoformat() if quote.validity_date else None,
            "total_amount_chf": float(quote.total_amount_chf) if quote.total_amount_chf else None,
            "total_with_vat": None,
            "vat_rate": None,
            "discount": None,
            "currency": quote.currency,
            "positions": [],
            "scope": {
                "description": quote.scope_description,
                "zones_mentioned": [],
                "work_types": [],
                "duration_days": quote.estimated_duration_days,
            },
            "exclusions": [quote.exclusions] if quote.exclusions else [],
            "inclusions": [quote.inclusions] if quote.inclusions else [],
            "conditions": {
                "payment_terms": None,
                "guarantee_months": None,
                "start_conditions": None,
            },
            "regulatory": {
                "suva_mentioned": False,
                "waste_plan_mentioned": False,
                "safety_measures_mentioned": False,
            },
        },
        "provenance": {
            "source_document_id": str(quote.document_id) if quote.document_id else None,
            "tender_id": str(quote.tender_id) if quote.tender_id else None,
            "extraction_method": "structured_input",
            "extraction_date": datetime.now(UTC).isoformat(),
            "requires_human_review": False,
        },
        "corrections": [],
    }
    return extraction


# ---------------------------------------------------------------------------
# Generate comparison
# ---------------------------------------------------------------------------


async def generate_comparison(
    db: AsyncSession,
    tender_id: UUID,
    created_by_id: UUID,
) -> TenderComparison:
    """Generate a normalized, neutral comparison of all quotes for a tender.

    Compares: amount, duration, scope coverage, exclusions, validity.
    No ranking, no recommendation — just facts sorted by submission date.
    """
    result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    tender = result.scalar_one_or_none()
    if not tender:
        raise ValueError("Tender not found")

    # Fetch all quotes for this tender
    quotes_result = await db.execute(
        select(TenderQuote).where(TenderQuote.tender_id == tender_id).order_by(TenderQuote.submitted_at)
    )
    quotes = list(quotes_result.scalars().all())

    if not quotes:
        raise ValueError("No quotes available for comparison")

    # Build neutral comparison matrix
    entries = []
    amounts = []
    durations = []

    for q in quotes:
        amount_val = float(q.total_amount_chf) if q.total_amount_chf else None
        if amount_val is not None:
            amounts.append(amount_val)
        if q.estimated_duration_days is not None:
            durations.append(q.estimated_duration_days)

        entries.append(
            {
                "quote_id": str(q.id),
                "contractor_org_id": str(q.contractor_org_id),
                "total_amount_chf": amount_val,
                "currency": q.currency,
                "estimated_duration_days": q.estimated_duration_days,
                "scope_description": q.scope_description,
                "inclusions": q.inclusions,
                "exclusions": q.exclusions,
                "validity_date": q.validity_date.isoformat() if q.validity_date else None,
                "submitted_at": q.submitted_at.isoformat() if q.submitted_at else None,
                "status": q.status,
            }
        )

    # Compute neutral statistics (no ranking)
    stats = {
        "total_quotes": len(quotes),
        "quotes_with_amount": len(amounts),
        "amount_range_chf": {
            "min": min(amounts) if amounts else None,
            "max": max(amounts) if amounts else None,
        },
        "duration_range_days": {
            "min": min(durations) if durations else None,
            "max": max(durations) if durations else None,
        },
    }

    comparison_data = {
        "entries": entries,
        "statistics": stats,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    comparison = TenderComparison(
        tender_id=tender_id,
        created_by_id=created_by_id,
        comparison_data=comparison_data,
    )
    db.add(comparison)
    await db.flush()
    await db.refresh(comparison)
    return comparison


# ---------------------------------------------------------------------------
# Attribute tender
# ---------------------------------------------------------------------------


async def attribute_tender(
    db: AsyncSession,
    tender_id: UUID,
    quote_id: UUID,
    reason: str | None = None,
) -> TenderComparison:
    """Record the client's choice of quote for a tender.

    Marks the selected quote and records the reason.
    Updates tender status to 'attributed'.
    """
    result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    tender = result.scalar_one_or_none()
    if not tender:
        raise ValueError("Tender not found")
    if tender.status in ("attributed", "cancelled"):
        raise ValueError(f"Cannot attribute tender in status '{tender.status}'")

    # Verify quote belongs to this tender
    quote_result = await db.execute(
        select(TenderQuote).where(TenderQuote.id == quote_id, TenderQuote.tender_id == tender_id)
    )
    quote = quote_result.scalar_one_or_none()
    if not quote:
        raise ValueError("Quote not found for this tender")

    now = datetime.now(UTC)

    # Mark quote as selected
    quote.status = "selected"
    quote.reviewed_at = now

    # Reject other quotes
    other_quotes_result = await db.execute(
        select(TenderQuote).where(
            TenderQuote.tender_id == tender_id,
            TenderQuote.id != quote_id,
        )
    )
    for other_quote in other_quotes_result.scalars().all():
        if other_quote.status not in ("rejected",):
            other_quote.status = "rejected"
            other_quote.reviewed_at = now

    # Update tender status
    tender.status = "attributed"

    # Find or create comparison with attribution
    comp_result = await db.execute(
        select(TenderComparison)
        .where(TenderComparison.tender_id == tender_id)
        .order_by(TenderComparison.created_at.desc())
        .limit(1)
    )
    comparison = comp_result.scalar_one_or_none()

    if comparison:
        comparison.selected_quote_id = quote_id
        comparison.selection_reason = reason
        comparison.attributed_at = now
    else:
        comparison = TenderComparison(
            tender_id=tender_id,
            created_by_id=tender.created_by_id,
            selected_quote_id=quote_id,
            selection_reason=reason,
            attributed_at=now,
        )
        db.add(comparison)

    await db.flush()
    await db.refresh(comparison)

    # Record trust signal for attribution winner
    await _record_trust_signal_for_tender(
        db,
        contractor_org_id=quote.contractor_org_id,
        tender_id=tender_id,
        signal_type="delivery_success",
        notes="Tender attributed to this contractor",
    )

    # If reason cites quality, boost evidence_quality_score via signal
    if reason and any(kw in reason.lower() for kw in ("quality", "qualite", "qualité", "evidence", "preuve")):
        await _record_trust_signal_for_tender(
            db,
            contractor_org_id=quote.contractor_org_id,
            tender_id=tender_id,
            signal_type="evidence_clean",
            notes=f"Attribution reason cites quality: {reason[:200]}",
        )

    return comparison


# ---------------------------------------------------------------------------
# Trust signal helper
# ---------------------------------------------------------------------------


async def _record_trust_signal_for_tender(
    db: AsyncSession,
    contractor_org_id: UUID,
    tender_id: UUID,
    signal_type: str,
    notes: str | None = None,
) -> None:
    """Record a partner trust signal linked to a tender's BuildingCase.

    Finds the BuildingCase linked to this tender and records the signal
    through the case linkage (V3 doctrine: building-rooted via case).
    Falls back to tender-level signal if no case exists.
    """
    from app.services.partner_trust_service import record_signal, record_signal_from_case

    # Find the BuildingCase linked to this tender
    case_result = await db.execute(select(BuildingCase).where(BuildingCase.tender_id == tender_id).limit(1))
    case = case_result.scalar_one_or_none()

    if case is not None:
        await record_signal_from_case(
            db,
            partner_org_id=contractor_org_id,
            case_id=case.id,
            signal_type=signal_type,
            notes=notes,
        )
    else:
        # Fallback: record signal with tender as source entity
        await record_signal(
            db,
            {
                "partner_org_id": contractor_org_id,
                "signal_type": signal_type,
                "source_entity_type": "tender_request",
                "source_entity_id": tender_id,
                "notes": notes,
            },
        )


# ---------------------------------------------------------------------------
# Listing / Detail helpers
# ---------------------------------------------------------------------------


async def get_tender(db: AsyncSession, tender_id: UUID) -> TenderRequest | None:
    """Get a single tender request by ID."""
    result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    return result.scalar_one_or_none()


async def list_tenders_for_building(db: AsyncSession, building_id: UUID) -> list[TenderRequest]:
    """List all tender requests for a building."""
    result = await db.execute(
        select(TenderRequest).where(TenderRequest.building_id == building_id).order_by(TenderRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def list_quotes_for_tender(db: AsyncSession, tender_id: UUID) -> list[TenderQuote]:
    """List all quotes for a tender, ordered by submission date."""
    result = await db.execute(
        select(TenderQuote).where(TenderQuote.tender_id == tender_id).order_by(TenderQuote.submitted_at)
    )
    return list(result.scalars().all())


async def update_tender(db: AsyncSession, tender_id: UUID, updates: dict) -> TenderRequest:
    """Update a tender request (only in draft status)."""
    result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    tender = result.scalar_one_or_none()
    if not tender:
        raise ValueError("Tender not found")
    if tender.status != "draft":
        raise ValueError(f"Cannot update tender in status '{tender.status}'")

    for key, value in updates.items():
        if value is not None and hasattr(tender, key):
            setattr(tender, key, value)

    await db.flush()
    await db.refresh(tender)
    return tender
