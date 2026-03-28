"""Tests for authority document extraction service (rule-based v1).

Covers: document type detection, metadata extraction, decision extraction,
complement request extraction, conditions extraction, full pipeline
(extract_from_document), apply flow, correction flywheel, rejection.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_claim import BuildingClaim, BuildingDecision
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.organization import Organization
from app.models.user import User
from app.services.authority_extraction_service import (
    AuthorityExtractionService,
    apply_authority_extraction,
    detect_document_type,
    extract_authority_metadata,
    extract_complement_request,
    extract_conditions,
    extract_decision,
    extract_from_document,
    record_correction,
    reject_extraction,
)

# ---------------------------------------------------------------------------
# Sample texts for testing
# ---------------------------------------------------------------------------

PERMIT_GRANTED_FR = """
Service de l'urbanisme
Commune de Lausanne
Canton de Vaud

Date: 15.03.2026
N° de dossier: URB-2026-0451

Objet: Permis de construire
Parcelle n°: 1234
Requérant: M. Jean Dupont
Adresse: Rue de la Gare 12, 1000 Lausanne

Décision

Le Service de l'urbanisme autorise les travaux de rénovation
conformément à l'art. 103 LATC.

Conditions:
1. Avant le début des travaux, le requérant devra obtenir l'accord du service de l'environnement.
2. Pendant les travaux, les mesures de sécurité SUVA doivent être respectées.
3. Après les travaux, un contrôle final sera effectué par le service compétent.

Validité: 2 ans

Voie de recours:
Un recours peut être déposé auprès du Tribunal cantonal dans un délai de 30 jours.
"""

PERMIT_DENIED_FR = """
Direction du développement territorial
Canton de Genève

Date: 10.02.2026
Référence: DDT-2026-0789

Le permis de construire est refusé pour les motifs suivants:
Le projet n'est pas conforme aux dispositions de la LCI.

Base légale: art. 15 LCI

Voie de recours:
Recours auprès du Tribunal administratif dans un délai de 30 jours.
"""

COMPLEMENT_REQUEST_FR = """
Service des constructions
Commune de Morges
Canton de Vaud

Date: 20.01.2026
Réf.: SC-2026-0123

Demande de complément

En référence à votre demande du 05.01.2026,
nous vous prions de nous fournir les documents suivants:

Pièces manquantes:
- Plan de situation à l'échelle 1:500
- Rapport d'impact sur l'environnement
- Attestation de conformité énergétique

Délai: 30 jours

Merci de nous transmettre ces documents par voie postale ou électronique.
"""

PERMIT_CONDITIONAL_DE = """
Bauamt der Stadt Zürich
Kanton Zürich

Datum: 12.03.2026
Geschäftsnummer: BA-2026-0567

Baubewilligung mit Auflagen

Das Baugesuch wird bewilligt mit folgenden Auflagen:

Bedingungen:
1. Vor Baubeginn ist eine Sicherheitsanalyse durchzuführen.
2. Während der Arbeiten sind die Lärmschutzvorschriften einzuhalten.
3. Nach Fertigstellung ist eine Abnahme durch das Bauamt erforderlich.

Gültigkeit: 3 Jahre

Rechtsmittel:
Gegen diese Verfügung kann innert 30 Tagen Rekurs beim Verwaltungsgericht erhoben werden.
"""

AUTHORITY_NOTIFICATION_FR = """
Service de l'environnement
Canton de Vaud

Notification

Avis de mise à l'enquête publique concernant le projet de construction
situé sur la parcelle 5678, commune de Nyon.

Date: 01.03.2026
"""

GENERIC_TEXT = """
This is a generic document that does not match any authority document patterns.
It contains no relevant keywords or structures.
"""


# ---------------------------------------------------------------------------
# Unit tests: detection
# ---------------------------------------------------------------------------


class TestDetectDocumentType:
    def test_permit_granted(self):
        assert detect_document_type(PERMIT_GRANTED_FR) == "permit_granted"

    def test_permit_denied(self):
        assert detect_document_type(PERMIT_DENIED_FR) == "permit_denied"

    def test_complement_request(self):
        assert detect_document_type(COMPLEMENT_REQUEST_FR) == "complement_request"

    def test_conditional_permit_de(self):
        assert detect_document_type(PERMIT_CONDITIONAL_DE) == "permit_conditional"

    def test_authority_notification(self):
        assert detect_document_type(AUTHORITY_NOTIFICATION_FR) == "authority_notification"

    def test_other(self):
        assert detect_document_type(GENERIC_TEXT) == "other"

    def test_empty_text(self):
        assert detect_document_type("") == "other"

    def test_decision_keyword(self):
        text = "Cette décision est rendue par le département."
        result = detect_document_type(text)
        assert result == "decision"


# ---------------------------------------------------------------------------
# Unit tests: metadata extraction
# ---------------------------------------------------------------------------


class TestExtractAuthorityMetadata:
    def test_french_permit_metadata(self):
        meta = extract_authority_metadata(PERMIT_GRANTED_FR)
        assert meta["reference"] == "URB-2026-0451"
        assert meta["date"] == date(2026, 3, 15)
        assert meta["canton"] == "VD"
        assert meta["building_reference"] == "1234"
        assert meta["applicant"] is not None
        assert "Dupont" in meta["applicant"]

    def test_german_permit_metadata(self):
        meta = extract_authority_metadata(PERMIT_CONDITIONAL_DE)
        assert meta["reference"] == "BA-2026-0567"
        assert meta["date"] == date(2026, 3, 12)

    def test_complement_metadata(self):
        meta = extract_authority_metadata(COMPLEMENT_REQUEST_FR)
        assert meta["reference"] == "SC-2026-0123"
        assert meta["date"] == date(2026, 1, 20)

    def test_confidence_increases_with_fields(self):
        meta = extract_authority_metadata(PERMIT_GRANTED_FR)
        assert meta["confidence"] > 0.3  # should be higher than base

    def test_generic_text_low_confidence(self):
        meta = extract_authority_metadata(GENERIC_TEXT)
        assert meta["confidence"] <= 0.4


# ---------------------------------------------------------------------------
# Unit tests: decision extraction
# ---------------------------------------------------------------------------


class TestExtractDecision:
    def test_granted_decision(self):
        dec = extract_decision(PERMIT_GRANTED_FR)
        assert dec["outcome"] == "granted"
        assert dec["confidence"] >= 0.7

    def test_denied_decision(self):
        dec = extract_decision(PERMIT_DENIED_FR)
        assert dec["outcome"] == "denied"
        assert dec["confidence"] >= 0.7

    def test_legal_basis_extracted(self):
        dec = extract_decision(PERMIT_GRANTED_FR)
        # Should extract LATC reference
        assert dec["legal_basis"] is not None

    def test_appeal_deadline(self):
        dec = extract_decision(PERMIT_GRANTED_FR)
        assert dec["appeal_deadline_days"] == 30

    def test_german_appeal_deadline(self):
        dec = extract_decision(PERMIT_CONDITIONAL_DE)
        assert dec["appeal_deadline_days"] == 30


# ---------------------------------------------------------------------------
# Unit tests: complement request extraction
# ---------------------------------------------------------------------------


class TestExtractComplementRequest:
    def test_missing_items_extracted(self):
        comp = extract_complement_request(COMPLEMENT_REQUEST_FR)
        assert len(comp["missing_items"]) >= 2
        # Should find plan de situation, rapport d'impact, attestation
        items_text = " ".join(comp["missing_items"]).lower()
        assert "plan" in items_text or "rapport" in items_text

    def test_deadline_extracted(self):
        comp = extract_complement_request(COMPLEMENT_REQUEST_FR)
        assert comp["deadline"] is not None
        assert "30" in str(comp["deadline"])

    def test_reference_to_original(self):
        comp = extract_complement_request(COMPLEMENT_REQUEST_FR)
        assert comp["reference_to_original"] is not None

    def test_non_complement_returns_empty(self):
        comp = extract_complement_request(PERMIT_GRANTED_FR)
        assert comp["missing_items"] == []
        assert comp["confidence"] == 0.3


# ---------------------------------------------------------------------------
# Unit tests: conditions extraction
# ---------------------------------------------------------------------------


class TestExtractConditions:
    def test_french_conditions_extracted(self):
        conds = extract_conditions(PERMIT_GRANTED_FR)
        assert len(conds) >= 2

    def test_german_conditions_extracted(self):
        conds = extract_conditions(PERMIT_CONDITIONAL_DE)
        assert len(conds) >= 2

    def test_condition_categories(self):
        conds = extract_conditions(PERMIT_GRANTED_FR)
        categories = [c["category"] for c in conds]
        # Should detect before_works, during_works, after_works
        assert "before_works" in categories or "during_works" in categories or "safety" in categories

    def test_conditions_are_mandatory(self):
        conds = extract_conditions(PERMIT_GRANTED_FR)
        for c in conds:
            assert c["mandatory"] is True

    def test_no_conditions_in_denial(self):
        conds = extract_conditions(PERMIT_DENIED_FR)
        # Denied permits typically have no conditions section
        assert len(conds) == 0


# ---------------------------------------------------------------------------
# Integration tests: extract_from_document
# ---------------------------------------------------------------------------


@pytest.fixture
async def authority_org(db_session: AsyncSession):
    """Create an organization for authority tests."""
    org = Organization(
        id=uuid.uuid4(),
        name="Test Property Management",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def authority_building(db_session: AsyncSession, admin_user: User, authority_org: Organization):
    """Create a building with organization for authority tests."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue de Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        organization_id=authority_org.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def authority_document(db_session: AsyncSession, authority_building: Building, admin_user: User):
    """Create a document for authority extraction tests."""
    doc = Document(
        id=uuid.uuid4(),
        building_id=authority_building.id,
        file_path="/test/permit.pdf",
        file_name="permit.pdf",
        document_type="authority_document",
        uploaded_by=admin_user.id,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_extract_from_document_permit(
    db_session: AsyncSession,
    authority_document: Document,
    authority_building: Building,
):
    """Full pipeline: extract permit data from document."""
    result = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    assert result["status"] == "draft"
    assert result["confidence"] > 0.0
    assert result["extraction_id"] is not None

    extracted = result["extracted"]
    assert extracted["document_type"] in ("permit_granted", "permit_conditional")
    assert extracted["reference"] is not None
    assert extracted["date"] is not None
    assert len(extracted["conditions"]) >= 2
    assert len(extracted["obligations_created"]) >= 2
    assert result["provenance"]["extraction_method"] == "rule_based_v1"
    assert result["provenance"]["requires_human_review"] is True


@pytest.mark.asyncio
async def test_extract_from_document_complement(
    db_session: AsyncSession,
    authority_document: Document,
    authority_building: Building,
):
    """Full pipeline: extract complement request data."""
    result = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=COMPLEMENT_REQUEST_FR,
    )

    assert result["status"] == "draft"
    extracted = result["extracted"]
    assert extracted["document_type"] == "complement_request"
    assert len(extracted["complement"]["missing_items"]) >= 2


@pytest.mark.asyncio
async def test_extract_from_document_nonexistent(db_session: AsyncSession):
    """Raises ValueError for non-existent document."""
    with pytest.raises(ValueError, match="Document not found"):
        await extract_from_document(
            db_session,
            document_id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            text="irrelevant",
        )


# ---------------------------------------------------------------------------
# Integration tests: apply_authority_extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_permit_creates_decision(
    db_session: AsyncSession,
    authority_building: Building,
    admin_user: User,
    authority_document: Document,
):
    """Applying a permit extraction creates a BuildingDecision."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    result = await apply_authority_extraction(
        db_session,
        extraction_data=extraction,
        building_id=authority_building.id,
        applied_by_id=admin_user.id,
    )

    assert result["decision_id"] is not None
    assert len(result["claim_ids"]) >= 2  # conditions become claims
    assert len(result["evidence_link_ids"]) >= 1

    # Verify BuildingDecision was created
    dec_result = await db_session.execute(
        select(BuildingDecision).where(BuildingDecision.id == uuid.UUID(result["decision_id"]))
    )
    decision = dec_result.scalar_one_or_none()
    assert decision is not None
    assert decision.decision_type == "permit_decision"
    assert decision.authority_level == "authority"
    assert decision.status == "enacted"


@pytest.mark.asyncio
async def test_apply_permit_creates_evidence_link(
    db_session: AsyncSession,
    authority_building: Building,
    admin_user: User,
    authority_document: Document,
):
    """Applying a permit extraction creates EvidenceLink from document to decision."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    result = await apply_authority_extraction(
        db_session,
        extraction_data=extraction,
        building_id=authority_building.id,
        applied_by_id=admin_user.id,
    )

    assert len(result["evidence_link_ids"]) >= 1
    ev_result = await db_session.execute(
        select(EvidenceLink).where(EvidenceLink.id == uuid.UUID(result["evidence_link_ids"][0]))
    )
    ev = ev_result.scalar_one_or_none()
    assert ev is not None
    assert ev.source_type == "document"
    assert ev.target_type == "building_decision"
    assert ev.relationship == "extracted_from"


@pytest.mark.asyncio
async def test_apply_complement_creates_actions(
    db_session: AsyncSession,
    authority_building: Building,
    admin_user: User,
    authority_document: Document,
):
    """Applying a complement request creates ActionItems."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=COMPLEMENT_REQUEST_FR,
    )

    result = await apply_authority_extraction(
        db_session,
        extraction_data=extraction,
        building_id=authority_building.id,
        applied_by_id=admin_user.id,
    )

    assert len(result["action_item_ids"]) >= 1

    # Verify ActionItems were created
    for action_id in result["action_item_ids"]:
        action_result = await db_session.execute(select(ActionItem).where(ActionItem.id == uuid.UUID(action_id)))
        action = action_result.scalar_one_or_none()
        assert action is not None
        assert action.source_type == "authority_extraction"
        assert action.action_type == "complement_request"
        assert action.priority == "high"
        assert action.status == "open"


@pytest.mark.asyncio
async def test_apply_creates_claims_from_conditions(
    db_session: AsyncSession,
    authority_building: Building,
    admin_user: User,
    authority_document: Document,
):
    """Applying a permit with conditions creates BuildingClaims."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    result = await apply_authority_extraction(
        db_session,
        extraction_data=extraction,
        building_id=authority_building.id,
        applied_by_id=admin_user.id,
    )

    assert len(result["claim_ids"]) >= 2

    for claim_id in result["claim_ids"]:
        claim_result = await db_session.execute(select(BuildingClaim).where(BuildingClaim.id == uuid.UUID(claim_id)))
        claim = claim_result.scalar_one_or_none()
        assert claim is not None
        assert claim.basis_type == "ai_extraction"
        assert claim.status == "asserted"
        assert "Condition" in claim.subject


@pytest.mark.asyncio
async def test_apply_nonexistent_building(db_session: AsyncSession, admin_user: User):
    """Raises ValueError for non-existent building."""
    extraction = {
        "extraction_id": str(uuid.uuid4()),
        "extracted": {"document_type": "permit_granted"},
        "provenance": {"source_document_id": str(uuid.uuid4())},
    }
    with pytest.raises(ValueError, match="Building not found"):
        await apply_authority_extraction(
            db_session,
            extraction_data=extraction,
            building_id=uuid.uuid4(),
            applied_by_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_apply_denied_permit_no_claims(
    db_session: AsyncSession,
    authority_building: Building,
    admin_user: User,
    authority_document: Document,
):
    """Denied permit creates decision but no claims (no conditions)."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_DENIED_FR,
    )

    result = await apply_authority_extraction(
        db_session,
        extraction_data=extraction,
        building_id=authority_building.id,
        applied_by_id=admin_user.id,
    )

    assert result["decision_id"] is not None
    assert len(result["claim_ids"]) == 0
    assert len(result["action_item_ids"]) == 0


# ---------------------------------------------------------------------------
# Integration tests: corrections and rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_correction_updates_data(
    db_session: AsyncSession,
    authority_document: Document,
    authority_building: Building,
    admin_user: User,
):
    """Recording a correction updates the extraction data and feeds ai_feedback."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    old_ref = extraction["extracted"]["reference"]
    updated = await record_correction(
        db_session,
        extraction_data=extraction,
        field_path="reference",
        old_value=old_ref,
        new_value="CORRECTED-REF-123",
        corrected_by_id=admin_user.id,
    )

    assert updated["extracted"]["reference"] == "CORRECTED-REF-123"
    assert len(updated["corrections"]) == 1
    assert updated["corrections"][0]["field_path"] == "reference"


@pytest.mark.asyncio
async def test_record_correction_nested_path(
    db_session: AsyncSession,
    authority_document: Document,
    authority_building: Building,
    admin_user: User,
):
    """Correction with dot-path works on nested fields."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    updated = await record_correction(
        db_session,
        extraction_data=extraction,
        field_path="authority.authority_name",
        old_value=extraction["extracted"]["authority"].get("authority_name"),
        new_value="Corrected Authority Name",
        corrected_by_id=admin_user.id,
    )

    assert updated["extracted"]["authority"]["authority_name"] == "Corrected Authority Name"


@pytest.mark.asyncio
async def test_reject_extraction_feeds_flywheel(
    db_session: AsyncSession,
    authority_document: Document,
    authority_building: Building,
    admin_user: User,
):
    """Rejecting an extraction records feedback and sets status."""
    extraction = await extract_from_document(
        db_session,
        document_id=authority_document.id,
        building_id=authority_building.id,
        text=PERMIT_GRANTED_FR,
    )

    result = await reject_extraction(
        db_session,
        extraction_data=extraction,
        rejected_by_id=admin_user.id,
        reason="Incorrect extraction",
    )

    assert result["status"] == "rejected"


# ---------------------------------------------------------------------------
# Class wrapper tests
# ---------------------------------------------------------------------------


class TestAuthorityExtractionService:
    def test_class_has_all_methods(self):
        """Verify the class wrapper exposes all public functions."""
        assert hasattr(AuthorityExtractionService, "extract_from_document")
        assert hasattr(AuthorityExtractionService, "apply_authority_extraction")
        assert hasattr(AuthorityExtractionService, "record_correction")
        assert hasattr(AuthorityExtractionService, "reject_extraction")
        assert hasattr(AuthorityExtractionService, "detect_document_type")
        assert hasattr(AuthorityExtractionService, "extract_authority_metadata")
        assert hasattr(AuthorityExtractionService, "extract_decision")
        assert hasattr(AuthorityExtractionService, "extract_complement_request")
        assert hasattr(AuthorityExtractionService, "extract_conditions")

    def test_detect_document_type_via_class(self):
        """Class wrapper delegates to module-level function."""
        result = AuthorityExtractionService.detect_document_type(COMPLEMENT_REQUEST_FR)
        assert result == "complement_request"
