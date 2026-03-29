"""Tests for diagnostic_extraction_service — pure extraction logic (no DB)."""

from datetime import date

from app.services.diagnostic_extraction_service import (
    _classify_asbestos_result,
    _classify_concentration_result,
    _classify_generic_result,
    _normalize_text,
    _parse_date,
    _sample_risk_level,
    detect_report_type,
    extract_conclusions,
    extract_diagnostic_metadata,
    extract_samples,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_collapses_whitespace(self):
        assert _normalize_text("hello   world") == "hello world"

    def test_strips_edges(self):
        assert _normalize_text("  test  ") == "test"


class TestParseDate:
    def test_dot_format(self):
        assert _parse_date("15.03.2025") == date(2025, 3, 15)

    def test_slash_format(self):
        assert _parse_date("15/03/2025") == date(2025, 3, 15)

    def test_two_digit_year(self):
        assert _parse_date("01.01.25") == date(2025, 1, 1)

    def test_invalid_returns_none(self):
        assert _parse_date("not a date") is None


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


class TestDetectReportType:
    def test_asbestos_fr(self):
        text = "Rapport de diagnostic amiante. Chrysotile détecté dans les joints."
        assert detect_report_type(text) == "asbestos"

    def test_pcb(self):
        text = "Analyse des joints: PCB polychlorobiphényle détecté à 85 mg/kg"
        assert detect_report_type(text) == "pcb"

    def test_lead(self):
        text = "Mesure de plomb dans les peintures: concentration Pb élevée"
        assert detect_report_type(text) == "lead"

    def test_radon(self):
        text = "Mesure du radon: concentration de 450 Bq/m3 dans le sous-sol"
        assert detect_report_type(text) == "radon"

    def test_pfas(self):
        text = "Analyse PFAS et PFOS dans les eaux souterraines du site"
        assert detect_report_type(text) == "pfas"

    def test_hap(self):
        text = "Analyse HAP hydrocarbure aromatique polycyclique dans le bitume"
        assert detect_report_type(text) == "hap"

    def test_multi_pollutant(self):
        text = "Diagnostic amiante et PCB dans le bâtiment industriel"
        assert detect_report_type(text) == "multi"

    def test_unknown(self):
        assert detect_report_type("rapport technique général") == "unknown"


class TestExtractDiagnosticMetadata:
    def test_lab_name_extraction(self):
        text = "Laboratoire: LaboChem SA\nRéférence: LC-2025-0042\nDate: 15.03.2025"
        metadata = extract_diagnostic_metadata(text)
        assert metadata["lab_name"] == "LaboChem SA"

    def test_reference_extraction(self):
        text = "Référence: ABC-2025-001\nDate du rapport: 20.03.2025"
        metadata = extract_diagnostic_metadata(text)
        assert metadata["lab_reference"] is not None

    def test_empty_text(self):
        metadata = extract_diagnostic_metadata("")
        assert isinstance(metadata, dict)
        assert metadata.get("lab_name") is None


class TestExtractSamples:
    def test_asbestos_report(self):
        text = """
        Échantillon E-01: Flocage plafond sous-sol
        Résultat: Chrysotile détecté (amiante positif)
        Matériau: Flocage

        Échantillon E-02: Joint de fenêtre 3e étage
        Résultat: Négatif — aucune fibre d'amiante détectée
        Matériau: Mastic
        """
        samples = extract_samples(text, "asbestos")
        assert isinstance(samples, list)

    def test_pcb_report(self):
        text = """
        Échantillon P-01: Joint de dilatation façade nord
        Concentration PCB: 85 mg/kg
        """
        samples = extract_samples(text, "pcb")
        assert isinstance(samples, list)

    def test_empty_text(self):
        samples = extract_samples("", "asbestos")
        assert isinstance(samples, list)


class TestClassifyAsbestosResult:
    def test_positive_chrysotile(self):
        sample = {"result": None, "confidence": 0.3}
        result = _classify_asbestos_result(sample, "chrysotile détecté présence d'amiante positif")
        assert result["result"] == "positive"
        assert result["threshold_exceeded"] is True

    def test_negative(self):
        sample = {"result": None, "confidence": 0.3}
        result = _classify_asbestos_result(sample, "négatif absence d'amiante aucune fibre")
        assert result["result"] == "negative"
        assert result["threshold_exceeded"] is False


class TestClassifyConcentrationResult:
    def test_pcb_above_threshold(self):
        sample = {"concentration": 85.0, "unit": "mg/kg", "confidence": 0.3}
        result = _classify_concentration_result(sample, "pcb")
        assert result["result"] == "positive"
        assert result["threshold_exceeded"] is True

    def test_lead_above_threshold(self):
        sample = {"concentration": 6000.0, "unit": "mg/kg", "confidence": 0.3}
        result = _classify_concentration_result(sample, "lead")
        assert result["result"] == "positive"

    def test_no_concentration(self):
        sample = {"concentration": None, "confidence": 0.3}
        result = _classify_concentration_result(sample, "pcb")
        assert "threshold_exceeded" not in result


class TestClassifyGenericResult:
    def test_positive_text(self):
        sample = {"result": None, "confidence": 0.3}
        result = _classify_generic_result(sample, "détecté présence positif")
        assert result["result"] == "positive"

    def test_negative_text(self):
        sample = {"result": None, "confidence": 0.3}
        result = _classify_generic_result(sample, "négatif absence conforme")
        assert result["result"] == "negative"

    def test_non_detecte_is_negative(self):
        """BUG-01 regression: 'non détecté' must be negative, not positive."""
        sample = {"result": None, "confidence": 0.3}
        result = _classify_generic_result(sample, "non détecté dans l'échantillon")
        assert result["result"] == "negative"
        assert result["threshold_exceeded"] is False

    def test_not_detected_is_negative(self):
        sample = {"result": None, "confidence": 0.3}
        result = _classify_generic_result(sample, "substance not detected in sample")
        assert result["result"] == "negative"


class TestExtractConclusions:
    def test_conclusion_extraction(self):
        text = """
        Conclusion:
        Le bâtiment présente de l'amiante dans les flocages du sous-sol.
        Recommandation: désamiantage avant travaux de rénovation.
        Niveau d'urgence: élevé.
        """
        conclusions = extract_conclusions(text)
        assert isinstance(conclusions, dict)

    def test_empty_text(self):
        conclusions = extract_conclusions("")
        assert isinstance(conclusions, dict)


class TestSampleRiskLevel:
    def test_high_risk(self):
        sample = {"risk_level": "high"}
        assert _sample_risk_level(sample) in ("high", "critical", "medium", "low", "unknown")

    def test_missing_risk(self):
        sample = {}
        result = _sample_risk_level(sample)
        assert isinstance(result, str)
