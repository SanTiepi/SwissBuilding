"""BatiConnect -- Partner Submission Service.

Orchestrates the governed path for partners to submit data through their
exchange contracts. Every submission:
1. Validates partner access via exchange contract
2. Validates submission data against conformance profile
3. Creates the appropriate object (extraction, quote, acknowledgment)
4. Records exchange event for audit trail
5. Creates a ReviewTask for human review
6. Records a TruthRitual if applicable
7. Returns a typed receipt
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic_extraction import DiagnosticExtraction
from app.models.document import Document
from app.models.exchange_contract import PartnerExchangeContract

logger = logging.getLogger(__name__)


async def _ensure_document_id(
    db: AsyncSession,
    document_id: UUID | None,
    building_id: UUID,
    submitted_by_id: UUID,
    report_reference: str,
) -> UUID:
    """Ensure we have a valid document_id for the extraction.

    DiagnosticExtraction.document_id is NOT NULL.
    If the partner didn't provide a document, create a placeholder
    that represents the pending report submission.
    """
    if document_id is not None:
        return document_id

    doc = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path=f"partner-submissions/{report_reference}",
        file_name=f"{report_reference}.pending",
        document_type="diagnostic_report",
        description=f"Partner submission placeholder: {report_reference}",
        uploaded_by=submitted_by_id,
    )
    db.add(doc)
    await db.flush()
    return doc.id


async def submit_diagnostic(
    db: AsyncSession,
    partner_org_id: UUID,
    building_id: UUID,
    diagnostic_type: str,
    report_reference: str,
    report_date: date,
    submitted_by_id: UUID,
    document_id: UUID | None = None,
    text_content: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Process a partner diagnostic report submission.

    Flow:
    1. validate_submission -> contract check + conformance
    2. Create DiagnosticExtraction (draft, requires review)
    3. Record exchange event (submission_received)
    4. Create ReviewTask
    5. Return receipt
    """
    from app.services.partner_gateway_service import record_exchange_event, validate_submission
    from app.services.review_queue_service import create_review_task

    # 1. Validate submission through contract
    submission_data = {
        "building_id": str(building_id),
        "diagnostic_type": diagnostic_type,
        "report_reference": report_reference,
    }
    validation = await validate_submission(
        db,
        partner_org_id=partner_org_id,
        submission_type="diagnostics",
        submission_data=submission_data,
    )

    contract_id = validation.get("contract_id")

    if not validation["valid"]:
        return {
            "submission_id": uuid.uuid4(),
            "status": "rejected",
            "contract_id": contract_id,
            "conformance_result": validation.get("conformance_result"),
            "timestamp": datetime.now(UTC),
            "next_steps": "Submission rejected: "
            + "; ".join(i.get("message", "") for i in validation.get("issues", [])),
            "issues": validation.get("issues", []),
        }

    # 2. Get building org for review task
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return {
            "submission_id": uuid.uuid4(),
            "status": "rejected",
            "contract_id": contract_id,
            "conformance_result": None,
            "timestamp": datetime.now(UTC),
            "next_steps": "Building not found",
            "issues": [{"check": "building", "message": "Building not found", "severity": "error"}],
        }

    org_id = building.organization_id

    # 3. Ensure we have a valid document_id (NOT NULL on DiagnosticExtraction)
    resolved_doc_id = await _ensure_document_id(db, document_id, building_id, submitted_by_id, report_reference)

    # 4. Create extraction (draft) or use text extraction if text provided
    extraction_id = uuid.uuid4()
    if text_content:
        # Run extraction pipeline from text
        try:
            from app.services.diagnostic_extraction_service import (
                extract_conclusions,
                extract_diagnostic_metadata,
                extract_samples,
            )

            meta = extract_diagnostic_metadata(text_content)
            report_type = meta.get("report_type", diagnostic_type)
            samples = extract_samples(text_content, report_type)
            conclusions = extract_conclusions(text_content)

            confidence = 0.5
            if meta.get("lab_name"):
                confidence += 0.1
            if meta.get("report_date"):
                confidence += 0.1
            if samples:
                confidence += 0.1

            extracted_data = {
                "report_type": report_type,
                "lab_name": meta.get("lab_name"),
                "lab_reference": report_reference,
                "report_date": report_date.isoformat(),
                "samples": samples,
                "conclusions": conclusions,
                "partner_submission": True,
                "partner_metadata": metadata or {},
            }

            extraction = DiagnosticExtraction(
                id=extraction_id,
                document_id=resolved_doc_id,
                building_id=building_id,
                created_by_id=submitted_by_id,
                status="draft",
                confidence=confidence,
                extracted_data=extracted_data,
                corrections=[],
            )
            db.add(extraction)
            await db.flush()
        except Exception:
            logger.exception("partner_submission: extraction pipeline failed")
            extraction = DiagnosticExtraction(
                id=extraction_id,
                document_id=resolved_doc_id,
                building_id=building_id,
                created_by_id=submitted_by_id,
                status="draft",
                confidence=0.3,
                extracted_data={
                    "report_type": diagnostic_type,
                    "lab_reference": report_reference,
                    "report_date": report_date.isoformat(),
                    "partner_submission": True,
                    "extraction_error": True,
                },
                corrections=[],
            )
            db.add(extraction)
            await db.flush()
    else:
        # No text content -- create stub extraction for manual review
        extraction = DiagnosticExtraction(
            id=extraction_id,
            document_id=resolved_doc_id,
            building_id=building_id,
            created_by_id=submitted_by_id,
            status="draft",
            confidence=0.3,
            extracted_data={
                "report_type": diagnostic_type,
                "lab_reference": report_reference,
                "report_date": report_date.isoformat(),
                "partner_submission": True,
                "partner_metadata": metadata or {},
            },
            corrections=[],
        )
        db.add(extraction)
        await db.flush()

    # 4. Record exchange event
    if contract_id:
        await record_exchange_event(
            db,
            contract_id,
            "submission_received",
            {
                "submission_type": "diagnostic",
                "building_id": str(building_id),
                "diagnostic_type": diagnostic_type,
                "report_reference": report_reference,
                "extraction_id": str(extraction_id),
            },
        )

    # 5. Create review task
    if org_id:
        await create_review_task(
            db,
            building_id=building_id,
            organization_id=org_id,
            task_type="partner_submission_review",
            target_type="extraction",
            target_id=extraction_id,
            title=f"Revoir soumission partenaire: diagnostic {diagnostic_type} ({report_reference})",
            priority="medium",
            description=(
                f"Rapport soumis par un partenaire via contrat d'echange. "
                f"Type: {diagnostic_type}, Reference: {report_reference}, Date: {report_date}"
            ),
        )

    return {
        "submission_id": extraction_id,
        "status": "pending_review",
        "contract_id": contract_id,
        "conformance_result": validation.get("conformance_result"),
        "timestamp": datetime.now(UTC),
        "next_steps": "Submission accepted for review. A reviewer will validate the extracted data.",
        "issues": validation.get("issues", []),
    }


async def submit_quote(
    db: AsyncSession,
    partner_org_id: UUID,
    tender_id: UUID,
    total_amount_chf: float,
    scope_description: str,
    validity_date: date,
    submitted_by_id: UUID,
    document_id: UUID | None = None,
    metadata: dict | None = None,
) -> dict:
    """Process a partner quote submission for a tender.

    Flow:
    1. validate_submission -> contract check
    2. Verify tender exists
    3. Create TenderQuote
    4. Record exchange event
    5. Create ReviewTask
    6. Record partner trust signal
    7. Return receipt
    """
    from app.models.rfq import TenderQuote, TenderRequest
    from app.services.partner_gateway_service import record_exchange_event, validate_submission
    from app.services.review_queue_service import create_review_task

    # 1. Validate through contract
    validation = await validate_submission(
        db,
        partner_org_id=partner_org_id,
        submission_type="quotes",
        submission_data={"tender_id": str(tender_id)},
    )

    contract_id = validation.get("contract_id")

    if not validation["valid"]:
        return {
            "submission_id": uuid.uuid4(),
            "status": "rejected",
            "contract_id": contract_id,
            "conformance_result": validation.get("conformance_result"),
            "timestamp": datetime.now(UTC),
            "next_steps": "Quote rejected: " + "; ".join(i.get("message", "") for i in validation.get("issues", [])),
            "issues": validation.get("issues", []),
        }

    # 2. Verify tender exists
    tender_result = await db.execute(select(TenderRequest).where(TenderRequest.id == tender_id))
    tender = tender_result.scalar_one_or_none()
    if tender is None:
        return {
            "submission_id": uuid.uuid4(),
            "status": "rejected",
            "contract_id": contract_id,
            "conformance_result": None,
            "timestamp": datetime.now(UTC),
            "next_steps": "Tender not found",
            "issues": [{"check": "tender", "message": "Tender not found", "severity": "error"}],
        }

    # 3. Create TenderQuote
    quote = TenderQuote(
        tender_id=tender_id,
        contractor_org_id=partner_org_id,
        total_amount_chf=total_amount_chf,
        scope_description=scope_description,
        validity_date=validity_date,
        document_id=document_id,
        status="received",
        submitted_at=datetime.now(UTC),
        extracted_data=metadata or {},
    )
    db.add(quote)
    await db.flush()
    await db.refresh(quote)

    # 4. Record exchange event
    if contract_id:
        await record_exchange_event(
            db,
            contract_id,
            "submission_received",
            {
                "submission_type": "quote",
                "tender_id": str(tender_id),
                "quote_id": str(quote.id),
                "amount_chf": float(total_amount_chf),
            },
        )

    # 5. Create review task (use building from tender)
    building_id = tender.building_id
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    org_id = building.organization_id if building else None

    if org_id:
        await create_review_task(
            db,
            building_id=building_id,
            organization_id=org_id,
            task_type="partner_submission_review",
            target_type="quote",
            target_id=quote.id,
            title=f"Revoir offre partenaire: CHF {total_amount_chf:,.2f}",
            priority="medium",
            description=(
                f"Offre soumise par un partenaire via contrat d'echange. "
                f"Montant: CHF {total_amount_chf:,.2f}, Validite: {validity_date}"
            ),
        )

    # 6. Record partner trust signal
    try:
        from app.services.partner_trust_service import record_signal

        await record_signal(
            db,
            {
                "partner_org_id": partner_org_id,
                "signal_type": "response_fast",
                "signal_source": "partner_submission",
                "detail": {
                    "submission_type": "quote",
                    "tender_id": str(tender_id),
                    "quote_id": str(quote.id),
                },
            },
        )
    except Exception:
        logger.exception("partner_submission: trust signal failed for quote %s", quote.id)

    return {
        "submission_id": quote.id,
        "status": "pending_review",
        "contract_id": contract_id,
        "conformance_result": validation.get("conformance_result"),
        "timestamp": datetime.now(UTC),
        "next_steps": "Quote accepted for review. It will appear in the tender comparison.",
        "issues": validation.get("issues", []),
    }


async def submit_acknowledgment(
    db: AsyncSession,
    partner_org_id: UUID,
    submitted_by_id: UUID,
    acknowledged: bool = True,
    envelope_id: UUID | None = None,
    pack_id: UUID | None = None,
    notes: str | None = None,
) -> dict:
    """Process a partner acknowledgment of a transfer or pack.

    Flow:
    1. validate_submission -> contract check
    2. Record TruthRitual (acknowledge)
    3. Record exchange event
    4. Return receipt
    """
    from app.services import ritual_service
    from app.services.partner_gateway_service import record_exchange_event, validate_submission

    # Determine what's being acknowledged
    target_id = envelope_id or pack_id
    target_type = "passport" if envelope_id else "pack"

    if target_id is None:
        return {
            "submission_id": uuid.uuid4(),
            "status": "rejected",
            "contract_id": None,
            "conformance_result": None,
            "timestamp": datetime.now(UTC),
            "next_steps": "Must provide envelope_id or pack_id",
            "issues": [{"check": "target", "message": "No target specified", "severity": "error"}],
        }

    # 1. Validate through contract
    validation = await validate_submission(
        db,
        partner_org_id=partner_org_id,
        submission_type="acknowledgments",
        submission_data={
            "target_id": str(target_id),
            "target_type": target_type,
        },
    )

    contract_id = validation.get("contract_id")

    if not validation["valid"]:
        return {
            "submission_id": uuid.uuid4(),
            "status": "rejected",
            "contract_id": contract_id,
            "conformance_result": validation.get("conformance_result"),
            "timestamp": datetime.now(UTC),
            "next_steps": "Acknowledgment rejected: "
            + "; ".join(i.get("message", "") for i in validation.get("issues", [])),
            "issues": validation.get("issues", []),
        }

    # 2. Find building_id from envelope or pack
    building_id = await _resolve_building_id(db, envelope_id, pack_id)

    # Get org from contract
    org_id = None
    if contract_id:
        contract = await db.execute(select(PartnerExchangeContract).where(PartnerExchangeContract.id == contract_id))
        c = contract.scalar_one_or_none()
        if c:
            org_id = c.our_org_id

    # 3. Record TruthRitual if we have a building_id
    ritual = None
    if building_id and org_id:
        try:
            ritual = await ritual_service.acknowledge(
                db,
                building_id=building_id,
                target_type=target_type,
                target_id=target_id,
                acknowledged_by_id=submitted_by_id,
                org_id=org_id,
                reason=notes or ("Acknowledged" if acknowledged else "Refused"),
            )
        except Exception:
            logger.exception("partner_submission: ritual failed for acknowledgment")

    # 4. Record exchange event
    receipt_id = ritual.id if ritual else uuid.uuid4()
    if contract_id:
        await record_exchange_event(
            db,
            contract_id,
            "submission_received",
            {
                "submission_type": "acknowledgment",
                "target_type": target_type,
                "target_id": str(target_id),
                "acknowledged": acknowledged,
                "ritual_id": str(receipt_id),
            },
        )

    return {
        "submission_id": receipt_id,
        "status": "accepted" if acknowledged else "refused",
        "contract_id": contract_id,
        "conformance_result": validation.get("conformance_result"),
        "timestamp": datetime.now(UTC),
        "next_steps": "Acknowledgment recorded." if acknowledged else "Refusal recorded.",
        "issues": validation.get("issues", []),
    }


async def get_pending_submissions(
    db: AsyncSession,
    organization_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """List pending partner submissions waiting for review.

    Queries ReviewTask where task_type is 'partner_submission_review'.
    """
    from app.services.review_queue_service import get_queue

    return await get_queue(
        db,
        organization_id=organization_id,
        status="pending",
        task_type="partner_submission_review",
        limit=limit,
        offset=offset,
    )


async def _resolve_building_id(
    db: AsyncSession,
    envelope_id: UUID | None,
    pack_id: UUID | None,
) -> UUID | None:
    """Resolve building_id from an envelope or pack."""
    if envelope_id:
        try:
            from app.models.passport_envelope import BuildingPassportEnvelope

            result = await db.execute(
                select(BuildingPassportEnvelope).where(BuildingPassportEnvelope.id == envelope_id)
            )
            envelope = result.scalar_one_or_none()
            if envelope:
                return envelope.building_id
        except Exception:
            pass

    if pack_id:
        try:
            from app.models.evidence_pack import EvidencePack

            result = await db.execute(select(EvidencePack).where(EvidencePack.id == pack_id))
            pack = result.scalar_one_or_none()
            if pack:
                return pack.building_id
        except Exception:
            pass

    return None
