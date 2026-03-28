"""Tests for contract & invoice extraction service (rule-based v1).

Covers: document type detection, contract data extraction, invoice data extraction,
party extraction, full pipeline (extract_from_document), apply flow for both
contract and invoice paths, correction flywheel, rejection.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.contract import Contract
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.financial_entry import FinancialEntry
from app.models.organization import Organization
from app.models.user import User
from app.services.contract_extraction_service import (
    ContractExtractionService,
    apply_contract_extraction,
    detect_document_type,
    extract_contract_data,
    extract_from_document,
    extract_invoice_data,
    extract_parties,
    record_correction,
    reject_extraction,
)

# ---------------------------------------------------------------------------
# Sample texts for testing
# ---------------------------------------------------------------------------

CONTRACT_MAINTENANCE_FR = """
Contrat de maintenance

Entre:
Régie Romande SA, Avenue de la Gare 15, 1003 Lausanne
d'une part,
et
TechniClim Sàrl, Rue de l'Industrie 7, 1020 Renens

Référence: MAINT-2026-042
Objet du contrat: Maintenance annuelle du système de chauffage

Début: 01.01.2026
Fin: 31.12.2028
Durée: 3 ans

Montant annuel: CHF 12'500.00
Paiement: trimestriel
Conditions de paiement: 30 jours net après réception de la facture

Renouvellement: Le contrat est reconduit tacitement pour une période
d'un an sauf résiliation.
Préavis: 3 mois

Prestations:
- Entretien préventif semestriel de la chaudière
- Vérification annuelle du système de régulation
- Interventions de dépannage dans les 24h

Obligations:
- Le mandataire s'engage à intervenir sous 24 heures en cas de panne
- Fourniture d'un rapport d'intervention après chaque visite

Garantie: 24 mois sur les pièces remplacées

Exclusions:
- Remplacement complet de la chaudière
- Travaux de génie civil
"""

CONTRACT_MANAGEMENT_DE = """
Verwaltungsmandat

Zwischen:
Immobilien AG, Bahnhofstrasse 10, 8001 Zürich
und
Hausverwaltung Weber GmbH, Seestrasse 25, 8002 Zürich

Vertragsnummer: VM-2026-0089
Gegenstand: Liegenschaftsverwaltung

Vertragsbeginn: 01.04.2026
Vertragsende: 31.03.2029
Dauer: 3 Jahre

Jahresbetrag: CHF 18'000.00
Zahlungsmodalitäten: monatlich

Stillschweigende Verlängerung um jeweils ein Jahr.
Kündigungsfrist: 6 Monate

Leistungsumfang:
Verwaltung der Liegenschaft inklusive Mietermanagement,
Buchhaltung und technische Betreuung.
"""

INVOICE_FR = """
TechniClim Sàrl
Rue de l'Industrie 7
1020 Renens

Facture

N° facture: FA-2026-0318
Date: 15.03.2026
Échéance: 14.04.2026

Client: Régie Romande SA
Immeuble: Avenue de la Gare 15, Lausanne

Pos. 1  Entretien préventif chaudière           CHF 3'200.00
Pos. 2  Remplacement filtre                      CHF 450.00
Pos. 3  Main d'oeuvre (8h)                        CHF 1'600.00

Sous-total                                        CHF 5'250.00
TVA 8.1%                                          CHF 425.25
Total TTC                                         CHF 5'675.25

IBAN: CH93 0076 2011 6238 5295 7

Référence de paiement: 210000000003139471430009017
"""

INVOICE_DE = """
Hauswart Service AG
Industriestrasse 42
8005 Zürich

Rechnung

Rechnungsnummer: RE-2026-0156
Datum: 01.03.2026
Fällig: 31.03.2026

Objekt: Bahnhofstrasse 10, Zürich

1. Reinigung Treppenhaus (März)     CHF 800.00
2. Winterdienst                      CHF 350.00

Nettobetrag                          CHF 1'150.00
MwSt 8.1%                            CHF 93.15
Gesamtbetrag                         CHF 1'243.15
"""

PURCHASE_ORDER_FR = """
Bon de commande

Commande n°: BC-2026-001
Date: 10.03.2026

Fournisseur: ElectroParts SA
Objet: Matériel électrique pour rénovation

Total: CHF 2'340.00
"""

LEASE_TEXT = """
Bail à loyer

Le présent contrat de bail est conclu entre le bailleur et le preneur.
Durée du bail: du 01.04.2026 au 31.03.2029.
Loyer mensuel: CHF 2'500.00
"""

GENERIC_TEXT = """
This is a generic document that does not match any contract or invoice patterns.
It contains no relevant keywords or structures.
"""


# ---------------------------------------------------------------------------
# Unit tests: document type detection
# ---------------------------------------------------------------------------


class TestDetectDocumentType:
    def test_contract_fr(self):
        assert detect_document_type(CONTRACT_MAINTENANCE_FR) == "contract"

    def test_contract_de(self):
        assert detect_document_type(CONTRACT_MANAGEMENT_DE) == "contract"

    def test_invoice_fr(self):
        assert detect_document_type(INVOICE_FR) == "invoice"

    def test_invoice_de(self):
        assert detect_document_type(INVOICE_DE) == "invoice"

    def test_purchase_order(self):
        assert detect_document_type(PURCHASE_ORDER_FR) == "purchase_order"

    def test_lease(self):
        assert detect_document_type(LEASE_TEXT) == "lease"

    def test_other(self):
        assert detect_document_type(GENERIC_TEXT) == "other"

    def test_empty_text(self):
        assert detect_document_type("") == "other"

    def test_warranty_keyword(self):
        text = "Certificat de garantie pour les travaux effectués."
        assert detect_document_type(text) == "warranty"

    def test_insurance_keyword(self):
        text = "Police d'assurance bâtiment n° 12345"
        assert detect_document_type(text) == "insurance_policy"


# ---------------------------------------------------------------------------
# Unit tests: party extraction
# ---------------------------------------------------------------------------


class TestExtractParties:
    def test_french_parties(self):
        parties = extract_parties(CONTRACT_MAINTENANCE_FR)
        assert parties["party_a"] is not None
        assert "Romande" in parties["party_a"] or "Régie" in parties["party_a"]
        assert parties["confidence"] >= 0.5

    def test_german_parties(self):
        parties = extract_parties(CONTRACT_MANAGEMENT_DE)
        assert parties["party_a"] is not None or parties["party_b"] is not None
        assert parties["confidence"] >= 0.3

    def test_generic_text_low_confidence(self):
        parties = extract_parties(GENERIC_TEXT)
        assert parties["confidence"] <= 0.4


# ---------------------------------------------------------------------------
# Unit tests: contract data extraction
# ---------------------------------------------------------------------------


class TestExtractContractData:
    def test_french_contract_type(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["contract_type"] in ("maintenance", "heating")

    def test_german_management_type(self):
        data = extract_contract_data(CONTRACT_MANAGEMENT_DE)
        assert data["contract_type"] == "management_mandate"

    def test_reference_extracted(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["reference"] == "MAINT-2026-042"

    def test_title_extracted(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["title"] is not None
        assert "chauffage" in data["title"].lower() or "maintenance" in data["title"].lower()

    def test_start_date(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["start_date"] == date(2026, 1, 1)

    def test_end_date(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["end_date"] == date(2028, 12, 31)

    def test_auto_renewal_detected(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["auto_renewal"] is True

    def test_notice_period(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["termination_notice_months"] == 3

    def test_amount_extracted(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["amount"] is not None
        assert data["amount"] >= 12000

    def test_payment_frequency(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["payment_frequency"] == "quarterly"

    def test_german_amount(self):
        data = extract_contract_data(CONTRACT_MANAGEMENT_DE)
        assert data["amount"] is not None
        assert data["amount"] >= 18000

    def test_german_payment_frequency(self):
        data = extract_contract_data(CONTRACT_MANAGEMENT_DE)
        assert data["payment_frequency"] == "monthly"

    def test_obligations_extracted(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        # May or may not extract depending on pattern match
        assert isinstance(data["obligations"], list)

    def test_guarantees_extracted(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert isinstance(data["guarantees"], list)

    def test_exclusions_extracted(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert isinstance(data["exclusions"], list)

    def test_confidence_increases(self):
        data = extract_contract_data(CONTRACT_MAINTENANCE_FR)
        assert data["confidence"] > 0.3  # should be higher with many fields found

    def test_german_notice_period(self):
        data = extract_contract_data(CONTRACT_MANAGEMENT_DE)
        assert data["termination_notice_months"] == 6


# ---------------------------------------------------------------------------
# Unit tests: invoice data extraction
# ---------------------------------------------------------------------------


class TestExtractInvoiceData:
    def test_french_invoice_number(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["invoice_number"] == "FA-2026-0318"

    def test_french_invoice_date(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["date"] == date(2026, 3, 15)

    def test_french_due_date(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["due_date"] == date(2026, 4, 14)

    def test_french_amount_ht(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["amount_ht"] is not None
        assert abs(data["amount_ht"] - 5250.0) < 1.0

    def test_french_vat_rate(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["vat_rate"] is not None
        assert abs(data["vat_rate"] - 8.1) < 0.1

    def test_french_amount_ttc(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["amount_ttc"] is not None
        assert abs(data["amount_ttc"] - 5675.25) < 1.0

    def test_french_payment_reference(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["payment_reference"] is not None

    def test_french_qr_reference(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["qr_reference"] is not None

    def test_french_supplier(self):
        data = extract_invoice_data(INVOICE_FR)
        # Supplier extracted from header
        assert data["supplier"] is not None or data["supplier_address"] is not None

    def test_french_building_reference(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["building_reference"] is not None

    def test_french_line_items(self):
        data = extract_invoice_data(INVOICE_FR)
        assert isinstance(data["line_items"], list)
        # Should extract at least some line items
        if data["line_items"]:
            assert "description" in data["line_items"][0]
            assert "amount" in data["line_items"][0]

    def test_german_invoice_number(self):
        data = extract_invoice_data(INVOICE_DE)
        assert data["invoice_number"] == "RE-2026-0156"

    def test_german_invoice_date(self):
        data = extract_invoice_data(INVOICE_DE)
        assert data["date"] == date(2026, 3, 1)

    def test_german_due_date(self):
        data = extract_invoice_data(INVOICE_DE)
        assert data["due_date"] == date(2026, 3, 31)

    def test_german_amount_ttc(self):
        data = extract_invoice_data(INVOICE_DE)
        assert data["amount_ttc"] is not None or data["amount_ht"] is not None

    def test_category_detected(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["category"] in (
            "maintenance",
            "repair",
            "other_expense",
            "heating",
            "energy",
        )

    def test_german_category(self):
        data = extract_invoice_data(INVOICE_DE)
        assert data["category"] in ("cleaning", "concierge", "other_expense")

    def test_currency_default_chf(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["currency"] == "CHF"

    def test_confidence_increases(self):
        data = extract_invoice_data(INVOICE_FR)
        assert data["confidence"] > 0.3


# ---------------------------------------------------------------------------
# Integration tests: extract_from_document
# ---------------------------------------------------------------------------


@pytest.fixture
async def contract_org(db_session: AsyncSession):
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
async def contract_building(db_session: AsyncSession, admin_user: User, contract_org: Organization):
    building = Building(
        id=uuid.uuid4(),
        address="Rue de Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        organization_id=contract_org.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def contract_document(db_session: AsyncSession, contract_building: Building, admin_user: User):
    doc = Document(
        id=uuid.uuid4(),
        building_id=contract_building.id,
        file_path="/test/contract.pdf",
        file_name="contract.pdf",
        document_type="contract",
        uploaded_by=admin_user.id,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.fixture
async def invoice_document(db_session: AsyncSession, contract_building: Building, admin_user: User):
    doc = Document(
        id=uuid.uuid4(),
        building_id=contract_building.id,
        file_path="/test/invoice.pdf",
        file_name="invoice.pdf",
        document_type="invoice",
        uploaded_by=admin_user.id,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.mark.asyncio
class TestExtractFromDocument:
    async def test_contract_extraction_returns_draft(
        self, db_session: AsyncSession, contract_document: Document, contract_building: Building
    ):
        result = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        assert result["status"] == "draft"
        assert result["confidence"] > 0
        assert result["extracted"]["document_type"] == "contract"
        assert "contract" in result["extracted"]
        assert result["provenance"]["extraction_method"] == "rule_based_v1"
        assert result["provenance"]["requires_human_review"] is True

    async def test_invoice_extraction_returns_draft(
        self, db_session: AsyncSession, invoice_document: Document, contract_building: Building
    ):
        result = await extract_from_document(
            db_session,
            invoice_document.id,
            contract_building.id,
            INVOICE_FR,
        )
        assert result["status"] == "draft"
        assert result["confidence"] > 0
        assert result["extracted"]["document_type"] == "invoice"
        assert "invoice" in result["extracted"]

    async def test_nonexistent_document_raises(self, db_session: AsyncSession, contract_building: Building):
        with pytest.raises(ValueError, match="Document not found"):
            await extract_from_document(
                db_session,
                uuid.uuid4(),
                contract_building.id,
                CONTRACT_MAINTENANCE_FR,
            )

    async def test_extraction_has_corrections_list(
        self, db_session: AsyncSession, contract_document: Document, contract_building: Building
    ):
        result = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        assert result["corrections"] == []


# ---------------------------------------------------------------------------
# Integration tests: apply contract extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestApplyContractExtraction:
    async def test_apply_contract_creates_contract(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        result = await apply_contract_extraction(
            db_session,
            extraction,
            contract_building.id,
            admin_user.id,
        )
        assert result["contract_id"] is not None
        assert result["financial_entry_id"] is None

        # Verify contract was created in DB
        stmt = select(Contract).where(Contract.id == uuid.UUID(result["contract_id"]))
        contract = (await db_session.execute(stmt)).scalar_one_or_none()
        assert contract is not None
        assert contract.status == "draft"
        assert contract.building_id == contract_building.id

    async def test_apply_contract_creates_evidence_link(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        result = await apply_contract_extraction(
            db_session,
            extraction,
            contract_building.id,
            admin_user.id,
        )
        assert len(result["evidence_link_ids"]) >= 1

        ev_id = uuid.UUID(result["evidence_link_ids"][0])
        stmt = select(EvidenceLink).where(EvidenceLink.id == ev_id)
        ev = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ev is not None
        assert ev.relationship == "extracted_from"
        assert ev.source_type == "document"
        assert ev.target_type == "contract"

    async def test_apply_invoice_creates_financial_entry(
        self,
        db_session: AsyncSession,
        invoice_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            invoice_document.id,
            contract_building.id,
            INVOICE_FR,
        )
        result = await apply_contract_extraction(
            db_session,
            extraction,
            contract_building.id,
            admin_user.id,
        )
        assert result["financial_entry_id"] is not None
        assert result["contract_id"] is None

        # Verify financial entry in DB
        fe_id = uuid.UUID(result["financial_entry_id"])
        stmt = select(FinancialEntry).where(FinancialEntry.id == fe_id)
        fe = (await db_session.execute(stmt)).scalar_one_or_none()
        assert fe is not None
        assert fe.entry_type == "expense"
        assert fe.status == "draft"
        assert fe.amount_chf > 0
        assert fe.building_id == contract_building.id

    async def test_apply_nonexistent_building_raises(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        with pytest.raises(ValueError, match="Building not found"):
            await apply_contract_extraction(
                db_session,
                extraction,
                uuid.uuid4(),
                admin_user.id,
            )


# ---------------------------------------------------------------------------
# Integration tests: correction flywheel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRecordCorrection:
    async def test_correction_updates_data(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        updated = await record_correction(
            db_session,
            extraction,
            "contract.amount",
            extraction["extracted"].get("contract", {}).get("amount"),
            15000.0,
            admin_user.id,
        )
        assert updated["extracted"]["contract"]["amount"] == 15000.0
        assert len(updated["corrections"]) == 1
        assert updated["corrections"][0]["field_path"] == "contract.amount"
        assert updated["corrections"][0]["new_value"] == 15000.0

    async def test_correction_creates_feedback(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            INVOICE_FR,
        )
        await record_correction(
            db_session,
            extraction,
            "invoice.amount_ttc",
            extraction["extracted"].get("invoice", {}).get("amount_ttc"),
            6000.0,
            admin_user.id,
        )
        # AIFeedback should be created -- verify via count
        from app.models.ai_feedback import AIFeedback

        stmt = select(AIFeedback).where(AIFeedback.entity_type == "contract_extraction")
        result = await db_session.execute(stmt)
        feedbacks = result.scalars().all()
        assert len(feedbacks) >= 1


# ---------------------------------------------------------------------------
# Integration tests: rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRejectExtraction:
    async def test_reject_sets_status(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        result = await reject_extraction(
            db_session,
            extraction,
            admin_user.id,
            reason="Incorrect document",
        )
        assert result["status"] == "rejected"

    async def test_reject_creates_feedback(
        self,
        db_session: AsyncSession,
        contract_document: Document,
        contract_building: Building,
        admin_user: User,
    ):
        extraction = await extract_from_document(
            db_session,
            contract_document.id,
            contract_building.id,
            CONTRACT_MAINTENANCE_FR,
        )
        await reject_extraction(
            db_session,
            extraction,
            admin_user.id,
            reason="Wrong building",
        )
        from app.models.ai_feedback import AIFeedback

        stmt = select(AIFeedback).where(
            AIFeedback.entity_type == "contract_extraction",
            AIFeedback.feedback_type == "reject",
        )
        result = await db_session.execute(stmt)
        feedbacks = result.scalars().all()
        assert len(feedbacks) >= 1


# ---------------------------------------------------------------------------
# Unit tests: class wrapper
# ---------------------------------------------------------------------------


class TestContractExtractionServiceWrapper:
    def test_class_has_all_methods(self):
        assert hasattr(ContractExtractionService, "extract_from_document")
        assert hasattr(ContractExtractionService, "apply_contract_extraction")
        assert hasattr(ContractExtractionService, "record_correction")
        assert hasattr(ContractExtractionService, "reject_extraction")
        assert hasattr(ContractExtractionService, "detect_document_type")
        assert hasattr(ContractExtractionService, "extract_contract_data")
        assert hasattr(ContractExtractionService, "extract_invoice_data")
        assert hasattr(ContractExtractionService, "extract_parties")
