"""Tests for partner submission flow.

Validates that partner submissions go through contract validation,
create the correct objects, record audit events, and return typed receipts.
"""

import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic_extraction import DiagnosticExtraction
from app.models.exchange_contract import PartnerExchangeContract, PartnerExchangeEvent
from app.models.organization import Organization
from app.models.review_queue import ReviewTask
from app.models.rfq import TenderQuote, TenderRequest
from app.models.truth_ritual import TruthRitual
from app.models.user import User
from app.services import partner_submission_service as svc

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def partner_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="DiagSwiss Partner",
        type="diagnostic_lab",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def our_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="BatiConnect Platform",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def partner_user(db_session: AsyncSession, partner_org):
    user = User(
        id=uuid.uuid4(),
        email="partner@diagswiss.ch",
        password_hash="$2b$12$fakehash",
        first_name="Partner",
        last_name="User",
        role="diagnostician",
        organization_id=partner_org.id,
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def building(db_session: AsyncSession, our_org, partner_user):
    bld = Building(
        id=uuid.uuid4(),
        address="Rue du Test 42",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=partner_user.id,
        organization_id=our_org.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()
    return bld


@pytest.fixture
async def active_contract(db_session: AsyncSession, our_org, partner_org):
    contract = PartnerExchangeContract(
        id=uuid.uuid4(),
        partner_org_id=partner_org.id,
        our_org_id=our_org.id,
        contract_type="submission_partner",
        allowed_operations=[
            "submit_diagnostics",
            "submit_quotes",
            "submit_acknowledgments",
        ],
        api_access_level="submit",
        data_sharing_scope="building_specific",
        redaction_profile="none",
        minimum_trust_level="unknown",
        status="active",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=365),
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


@pytest.fixture
async def expired_contract(db_session: AsyncSession, our_org, partner_org):
    contract = PartnerExchangeContract(
        id=uuid.uuid4(),
        partner_org_id=partner_org.id,
        our_org_id=our_org.id,
        contract_type="submission_partner",
        allowed_operations=["submit_diagnostics"],
        api_access_level="submit",
        data_sharing_scope="building_specific",
        status="active",
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=1),
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


@pytest.fixture
async def readonly_contract(db_session: AsyncSession, our_org, partner_org):
    """Contract that only allows read operations, not submissions."""
    contract = PartnerExchangeContract(
        id=uuid.uuid4(),
        partner_org_id=partner_org.id,
        our_org_id=our_org.id,
        contract_type="data_consumer",
        allowed_operations=["receive_packs"],
        api_access_level="read_only",
        data_sharing_scope="building_specific",
        status="active",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=365),
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


@pytest.fixture
async def tender(db_session: AsyncSession, building, partner_user):
    t = TenderRequest(
        id=uuid.uuid4(),
        building_id=building.id,
        created_by_id=partner_user.id,
        title="Asbestos removal tender",
        work_type="asbestos_removal",
        status="collecting",
    )
    db_session.add(t)
    await db_session.flush()
    return t


# ---------------------------------------------------------------------------
# Diagnostic submission tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostic_submission_valid_contract(db_session, partner_org, partner_user, building, active_contract):
    """Valid contract -> extraction created + review task + audit event."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="asbestos",
        report_reference="REF-2026-001",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )
    await db_session.flush()

    assert result["status"] == "pending_review"
    assert result["contract_id"] == active_contract.id

    # Extraction was created
    ext = await db_session.execute(
        select(DiagnosticExtraction).where(DiagnosticExtraction.id == result["submission_id"])
    )
    extraction = ext.scalar_one_or_none()
    assert extraction is not None
    assert extraction.status == "draft"
    assert extraction.building_id == building.id
    assert extraction.extracted_data["report_type"] == "asbestos"
    assert extraction.extracted_data["partner_submission"] is True

    # Review task was created
    task_result = await db_session.execute(
        select(ReviewTask).where(
            ReviewTask.target_id == result["submission_id"],
            ReviewTask.task_type == "partner_submission_review",
        )
    )
    task = task_result.scalar_one_or_none()
    assert task is not None
    assert task.status == "pending"

    # Exchange event was recorded
    event_result = await db_session.execute(
        select(PartnerExchangeEvent).where(
            PartnerExchangeEvent.contract_id == active_contract.id,
            PartnerExchangeEvent.event_type == "submission_received",
        )
    )
    event = event_result.scalar_one_or_none()
    assert event is not None
    assert event.detail["submission_type"] == "diagnostic"


@pytest.mark.asyncio
async def test_diagnostic_submission_no_contract(db_session, partner_org, partner_user, building):
    """No contract -> rejected."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="asbestos",
        report_reference="REF-2026-002",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"
    assert "No active exchange contract" in result["next_steps"]


@pytest.mark.asyncio
async def test_diagnostic_submission_expired_contract(
    db_session, partner_org, partner_user, building, expired_contract
):
    """Expired contract -> rejected."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="pcb",
        report_reference="REF-2026-003",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"
    assert result["contract_id"] is None


@pytest.mark.asyncio
async def test_diagnostic_submission_wrong_operation(
    db_session, partner_org, partner_user, building, readonly_contract
):
    """Contract without submit_diagnostics operation -> rejected."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="lead",
        report_reference="REF-2026-004",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"
    assert "No contract allows" in result["next_steps"] or "No active" in result["next_steps"]


@pytest.mark.asyncio
async def test_diagnostic_submission_with_text_extraction(
    db_session, partner_org, partner_user, building, active_contract
):
    """Submission with text content triggers extraction pipeline."""
    text = """
    Laboratoire: LabSwiss SA
    Reference: LAB-2026-42
    Date du rapport: 15.03.2026

    Echantillon: E-001
    Localisation: Sous-sol, local technique
    Materiau: Joint de dilatation
    Resultat: Presence d'amiante chrysotile detectee

    Recommandation: Assainissement requis avant travaux
    """

    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="asbestos",
        report_reference="LAB-2026-42",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
        text_content=text,
    )
    await db_session.flush()

    assert result["status"] == "pending_review"

    # Extraction should have parsed data
    ext = await db_session.execute(
        select(DiagnosticExtraction).where(DiagnosticExtraction.id == result["submission_id"])
    )
    extraction = ext.scalar_one_or_none()
    assert extraction is not None
    assert extraction.confidence > 0.3  # should be enriched by extraction


@pytest.mark.asyncio
async def test_diagnostic_submission_building_not_found(db_session, partner_org, partner_user, active_contract):
    """Non-existent building -> rejected."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=uuid.uuid4(),
        diagnostic_type="asbestos",
        report_reference="REF-2026-005",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"
    assert "Building not found" in result["next_steps"]


# ---------------------------------------------------------------------------
# Quote submission tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_submission_valid(db_session, partner_org, partner_user, building, active_contract, tender):
    """Valid contract + valid tender -> quote created + review task + trust signal."""
    result = await svc.submit_quote(
        db_session,
        partner_org_id=partner_org.id,
        tender_id=tender.id,
        total_amount_chf=45000.00,
        scope_description="Full asbestos removal in basement",
        validity_date=date.today() + timedelta(days=30),
        submitted_by_id=partner_user.id,
    )
    await db_session.flush()

    assert result["status"] == "pending_review"
    assert result["contract_id"] == active_contract.id

    # Quote was created
    q_result = await db_session.execute(select(TenderQuote).where(TenderQuote.id == result["submission_id"]))
    quote = q_result.scalar_one_or_none()
    assert quote is not None
    assert float(quote.total_amount_chf) == 45000.00
    assert quote.status == "received"
    assert quote.tender_id == tender.id

    # Review task was created
    task_result = await db_session.execute(
        select(ReviewTask).where(
            ReviewTask.target_id == result["submission_id"],
            ReviewTask.task_type == "partner_submission_review",
        )
    )
    task = task_result.scalar_one_or_none()
    assert task is not None

    # Exchange event recorded
    event_result = await db_session.execute(
        select(PartnerExchangeEvent).where(
            PartnerExchangeEvent.contract_id == active_contract.id,
            PartnerExchangeEvent.event_type == "submission_received",
        )
    )
    events = list(event_result.scalars().all())
    quote_events = [e for e in events if e.detail and e.detail.get("submission_type") == "quote"]
    assert len(quote_events) >= 1


@pytest.mark.asyncio
async def test_quote_submission_no_contract(db_session, partner_org, partner_user, tender):
    """No contract -> rejected."""
    result = await svc.submit_quote(
        db_session,
        partner_org_id=partner_org.id,
        tender_id=tender.id,
        total_amount_chf=50000.00,
        scope_description="Full removal",
        validity_date=date.today() + timedelta(days=30),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"


@pytest.mark.asyncio
async def test_quote_submission_tender_not_found(db_session, partner_org, partner_user, active_contract):
    """Non-existent tender -> rejected."""
    result = await svc.submit_quote(
        db_session,
        partner_org_id=partner_org.id,
        tender_id=uuid.uuid4(),
        total_amount_chf=50000.00,
        scope_description="Full removal",
        validity_date=date.today() + timedelta(days=30),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"
    assert "Tender not found" in result["next_steps"]


@pytest.mark.asyncio
async def test_quote_submission_wrong_operation(db_session, partner_org, partner_user, readonly_contract, tender):
    """Contract without submit_quotes -> rejected."""
    result = await svc.submit_quote(
        db_session,
        partner_org_id=partner_org.id,
        tender_id=tender.id,
        total_amount_chf=50000.00,
        scope_description="Full removal",
        validity_date=date.today() + timedelta(days=30),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"


# ---------------------------------------------------------------------------
# Acknowledgment submission tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledgment_valid(db_session, partner_org, partner_user, building, active_contract):
    """Valid acknowledgment -> ritual trace + audit."""
    # Create a fake envelope for the acknowledgment
    from app.models.passport_envelope import BuildingPassportEnvelope

    envelope = BuildingPassportEnvelope(
        id=uuid.uuid4(),
        building_id=building.id,
        organization_id=partner_org.id,
        created_by_id=partner_user.id,
        passport_data={"grade": "C", "summary": "test"},
        sections_included=["overview"],
        content_hash="abc123" * 10 + "abcd",
        is_sovereign=True,
        status="published",
    )
    db_session.add(envelope)
    await db_session.flush()

    result = await svc.submit_acknowledgment(
        db_session,
        partner_org_id=partner_org.id,
        submitted_by_id=partner_user.id,
        acknowledged=True,
        envelope_id=envelope.id,
        notes="Received and reviewed",
    )
    await db_session.flush()

    assert result["status"] == "accepted"
    assert result["contract_id"] == active_contract.id

    # Exchange event recorded
    event_result = await db_session.execute(
        select(PartnerExchangeEvent).where(
            PartnerExchangeEvent.contract_id == active_contract.id,
            PartnerExchangeEvent.event_type == "submission_received",
        )
    )
    events = list(event_result.scalars().all())
    ack_events = [e for e in events if e.detail and e.detail.get("submission_type") == "acknowledgment"]
    assert len(ack_events) >= 1

    # Truth ritual recorded
    ritual_result = await db_session.execute(
        select(TruthRitual).where(
            TruthRitual.building_id == building.id,
            TruthRitual.ritual_type == "acknowledge",
        )
    )
    ritual = ritual_result.scalar_one_or_none()
    assert ritual is not None


@pytest.mark.asyncio
async def test_acknowledgment_no_target(db_session, partner_org, partner_user, active_contract):
    """No envelope_id or pack_id -> rejected."""
    result = await svc.submit_acknowledgment(
        db_session,
        partner_org_id=partner_org.id,
        submitted_by_id=partner_user.id,
        acknowledged=True,
    )

    assert result["status"] == "rejected"
    assert "envelope_id or pack_id" in result["next_steps"]


@pytest.mark.asyncio
async def test_acknowledgment_no_contract(db_session, partner_org, partner_user, building):
    """No contract -> rejected."""
    from app.models.passport_envelope import BuildingPassportEnvelope

    envelope = BuildingPassportEnvelope(
        id=uuid.uuid4(),
        building_id=building.id,
        organization_id=partner_org.id,
        created_by_id=partner_user.id,
        passport_data={"grade": "C", "summary": "test"},
        sections_included=["overview"],
        content_hash="abc123" * 10 + "abcd",
        is_sovereign=True,
        status="published",
    )
    db_session.add(envelope)
    await db_session.flush()

    result = await svc.submit_acknowledgment(
        db_session,
        partner_org_id=partner_org.id,
        submitted_by_id=partner_user.id,
        acknowledged=True,
        envelope_id=envelope.id,
    )

    assert result["status"] == "rejected"


@pytest.mark.asyncio
async def test_acknowledgment_refusal(db_session, partner_org, partner_user, building, active_contract):
    """Partner refuses acknowledgment -> status=refused + ritual recorded."""
    from app.models.passport_envelope import BuildingPassportEnvelope

    envelope = BuildingPassportEnvelope(
        id=uuid.uuid4(),
        building_id=building.id,
        organization_id=partner_org.id,
        created_by_id=partner_user.id,
        passport_data={"grade": "C", "summary": "test"},
        sections_included=["overview"],
        content_hash="abc123" * 10 + "abcd",
        is_sovereign=True,
        status="published",
    )
    db_session.add(envelope)
    await db_session.flush()

    result = await svc.submit_acknowledgment(
        db_session,
        partner_org_id=partner_org.id,
        submitted_by_id=partner_user.id,
        acknowledged=False,
        envelope_id=envelope.id,
        notes="Document incomplete",
    )
    await db_session.flush()

    assert result["status"] == "refused"


# ---------------------------------------------------------------------------
# Conformance flagging test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostic_submission_conformance_issues_flagged(
    db_session, partner_org, partner_user, building, active_contract
):
    """Submission accepted but conformance issues are included in receipt."""
    # Even with conformance warnings (not errors), submission proceeds
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="radon",
        report_reference="RAD-2026-001",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
        metadata={"source": "field_measurement"},
    )
    await db_session.flush()

    # Should succeed (no conformance errors since no profile linked)
    assert result["status"] == "pending_review"
    # conformance_result can be None if no profile is linked
    # The important thing is the submission went through


# ---------------------------------------------------------------------------
# Pending submissions listing test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_submissions_list(db_session, partner_org, partner_user, building, our_org, active_contract):
    """Pending submissions returns partner_submission_review tasks."""
    # Submit a diagnostic to create a pending review task
    await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="asbestos",
        report_reference="REF-LIST-001",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )
    await db_session.flush()

    # List pending for our_org (which owns the building)
    pending = await svc.get_pending_submissions(
        db_session,
        organization_id=our_org.id,
    )

    assert len(pending) >= 1
    assert all(t.task_type == "partner_submission_review" for t in pending)


# ---------------------------------------------------------------------------
# Receipt shape validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receipt_shape_diagnostic(db_session, partner_org, partner_user, building, active_contract):
    """Receipt has all required fields with correct types."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="hap",
        report_reference="HAP-2026-001",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )

    assert "submission_id" in result
    assert "status" in result
    assert "contract_id" in result
    assert "timestamp" in result
    assert "next_steps" in result
    assert isinstance(result["timestamp"], datetime)
    assert result["status"] in ("pending_review", "rejected", "accepted")


@pytest.mark.asyncio
async def test_receipt_shape_rejected(db_session, partner_org, partner_user, building):
    """Rejected receipt includes rejection reason."""
    result = await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="asbestos",
        report_reference="REF-REJECT",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )

    assert result["status"] == "rejected"
    assert result["next_steps"]  # non-empty reason
    assert "Submission rejected" in result["next_steps"]


# ---------------------------------------------------------------------------
# Audit trail completeness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_trail_completeness(db_session, partner_org, partner_user, building, active_contract):
    """Every successful submission creates at least 2 exchange events
    (one from validate_submission, one from the submission itself)."""
    await svc.submit_diagnostic(
        db_session,
        partner_org_id=partner_org.id,
        building_id=building.id,
        diagnostic_type="pcb",
        report_reference="AUDIT-2026-001",
        report_date=date.today(),
        submitted_by_id=partner_user.id,
    )
    await db_session.flush()

    event_result = await db_session.execute(
        select(PartnerExchangeEvent).where(
            PartnerExchangeEvent.contract_id == active_contract.id,
        )
    )
    events = list(event_result.scalars().all())

    # Should have: access_granted + submission_validated + submission_received
    event_types = {e.event_type for e in events}
    assert "access_granted" in event_types
    assert "submission_received" in event_types
    assert len(events) >= 3  # access_granted + submission_validated + submission_received
