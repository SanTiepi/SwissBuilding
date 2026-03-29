"""Tests for quote_extraction_service — pure extraction logic (no DB)."""

from datetime import date

from app.services.quote_extraction_service import (
    _normalize_text,
    _parse_amount,
    _parse_date,
    detect_quote_type,
    extract_contractor_info,
    extract_dates,
    extract_exclusions_inclusions,
    extract_positions,
    extract_regulatory_mentions,
    extract_scope,
    extract_totals,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_collapses_whitespace(self):
        assert _normalize_text("hello   world") == "hello world"

    def test_strips_edges(self):
        assert _normalize_text("  hello  ") == "hello"

    def test_tabs_and_newlines(self):
        assert _normalize_text("hello\t\nworld") == "hello world"


class TestParseDate:
    def test_dot_format(self):
        assert _parse_date("15.03.2025") == date(2025, 3, 15)

    def test_slash_format(self):
        assert _parse_date("15/03/2025") == date(2025, 3, 15)

    def test_two_digit_year(self):
        assert _parse_date("01.01.25") == date(2025, 1, 1)

    def test_invalid_date(self):
        assert _parse_date("32.13.2025") is None

    def test_no_date(self):
        assert _parse_date("no date here") is None


class TestParseAmount:
    def test_swiss_format_apostrophe(self):
        assert _parse_amount("12'345.50") == 12345.50

    def test_swiss_format_space(self):
        assert _parse_amount("12 345.50") == 12345.50

    def test_comma_decimal(self):
        assert _parse_amount("12345,50") == 12345.50

    def test_simple_number(self):
        assert _parse_amount("1500") == 1500.0

    def test_invalid_returns_none(self):
        assert _parse_amount("not a number") is None


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


class TestDetectQuoteType:
    def test_asbestos_fr(self):
        text = "Devis pour le désamiantage complet du bâtiment, amiante dans les joints"
        assert detect_quote_type(text) == "asbestos_removal"

    def test_pcb(self):
        text = "Travaux d'assainissement PCB dans les joints de dilatation"
        assert detect_quote_type(text) == "pcb_removal"

    def test_lead_de(self):
        text = "Offerte für Bleisanierung der Fensterrahmen im Gebäude"
        assert detect_quote_type(text) == "lead_removal"

    def test_radon(self):
        text = "Assainissement radon: installation d'un système de ventilation"
        assert detect_quote_type(text) == "radon_mitigation"

    def test_pfas(self):
        text = "Remediation des PFAS et PFOS dans le sol contaminé"
        assert detect_quote_type(text) == "pfas_remediation"

    def test_demolition(self):
        text = "Offre pour la déconstruction et le rückbau du bâtiment annexe"
        assert detect_quote_type(text) == "demolition"

    def test_unknown(self):
        assert detect_quote_type("bonjour tout le monde") == "unknown"

    def test_multi_keyword_highest_wins(self):
        # More amiante keywords than PCB
        text = "amiante chrysotile amiante dans les joints. PCB détecté."
        assert detect_quote_type(text) == "asbestos_removal"


class TestExtractContractorInfo:
    def test_basic_extraction(self):
        text = "SanaChem SA\nRoute de Genève 42\n1003 Lausanne\nTél: 021 123 45 67\nDevis #2025-001"
        result = extract_contractor_info(text)
        assert result is not None
        assert isinstance(result, dict)
        assert "name" in result
        assert "confidence" in result

    def test_empty_text(self):
        result = extract_contractor_info("")
        assert result["confidence"] <= 0.5


class TestExtractPositions:
    def test_basic_positions(self):
        text = """
        Pos. 1: Désamiantage flocage — 250 m2 x CHF 45.00 = CHF 11'250.00
        Pos. 2: Évacuation déchets — 15 t x CHF 180.00 = CHF 2'700.00
        Pos. 3: Installation chantier — forfait CHF 3'500.00
        """
        positions = extract_positions(text)
        assert isinstance(positions, list)

    def test_empty_text(self):
        assert extract_positions("") == []


class TestExtractTotals:
    def test_total_detection(self):
        text = """
        Sous-total: CHF 25'500.00
        TVA 8.1%: CHF 2'065.50
        Total TTC: CHF 27'565.50
        """
        totals = extract_totals(text)
        assert isinstance(totals, dict)

    def test_no_totals(self):
        totals = extract_totals("no numbers here")
        assert isinstance(totals, dict)


class TestExtractScope:
    def test_scope_extraction(self):
        text = """
        Objet: Bâtiment résidentiel, Rue du Lac 15, 1003 Lausanne
        Surface concernée: environ 350 m2 de flocage dans les sous-sols
        Nombre d'étages: 4
        """
        scope = extract_scope(text)
        assert isinstance(scope, dict)


class TestExtractExclusionsInclusions:
    def test_exclusion_detection(self):
        text = """
        Non compris dans le devis:
        - Travaux de peinture
        - Remplacement des fenêtres
        Compris dans le devis:
        - Protection du chantier
        - Nettoyage final
        """
        exclusions, inclusions = extract_exclusions_inclusions(text)
        assert isinstance(exclusions, list)
        assert isinstance(inclusions, list)


class TestExtractDates:
    def test_date_extraction(self):
        text = """
        Date du devis: 15.03.2025
        Début des travaux: 01.04.2025
        Fin prévue: 30.06.2025
        Validité: 30 jours
        """
        dates = extract_dates(text)
        assert isinstance(dates, dict)


class TestExtractRegulatoryMentions:
    def test_swiss_regulation_detection(self):
        text = """
        Travaux conformes à l'OTConst Art. 60a et la directive CFST 6503.
        Élimination des déchets selon OLED. Classification: travaux majeurs.
        """
        mentions = extract_regulatory_mentions(text)
        assert isinstance(mentions, dict)

    def test_no_regulations(self):
        mentions = extract_regulatory_mentions("simple text without regulations")
        assert isinstance(mentions, dict)
