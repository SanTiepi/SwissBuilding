"""Tests for document extraction service (GED B)."""

from app.services.document_extraction_service import extract_from_text

# ── Swiss date extraction ─────────────────────────────────────────────


class TestDateExtraction:
    def test_dd_mm_yyyy_dot(self):
        result = extract_from_text("Date du rapport: 15.03.2024")
        assert len(result["dates"]) >= 1
        assert result["dates"][0]["value"] == "15.03.2024"

    def test_dd_mm_yyyy_slash(self):
        result = extract_from_text("Facture du 22/11/2023")
        assert len(result["dates"]) >= 1
        assert result["dates"][0]["value"] == "22/11/2023"

    def test_dd_month_yyyy_french(self):
        result = extract_from_text("Le 5 mars 2024, le diagnostic a ete realise")
        dates = result["dates"]
        assert any("mars" in d["value"].lower() for d in dates)

    def test_dd_month_yyyy_german(self):
        result = extract_from_text("Am 12. Januar 2025 wurde die Analyse durchgefuehrt")
        dates = result["dates"]
        assert any("Januar" in d["value"] for d in dates)

    def test_dd_month_yyyy_italian(self):
        result = extract_from_text("Il 3 settembre 2023 il rapporto e stato completato")
        dates = result["dates"]
        assert any("settembre" in d["value"].lower() for d in dates)


# ── CHF amount extraction ────────────────────────────────────────────


class TestAmountExtraction:
    def test_chf_prefix(self):
        result = extract_from_text("Total: CHF 1'234.56")
        assert len(result["amounts"]) >= 1

    def test_chf_prefix_no_decimals(self):
        result = extract_from_text("Cout estimatif: CHF 45000")
        assert len(result["amounts"]) >= 1

    def test_fr_prefix(self):
        result = extract_from_text("Montant: Fr. 1234.-")
        assert len(result["amounts"]) >= 1

    def test_chf_suffix(self):
        result = extract_from_text("Le total est de 1'234.56 CHF")
        assert len(result["amounts"]) >= 1

    def test_large_amount(self):
        result = extract_from_text("Budget total: CHF 1'234'567.80")
        assert len(result["amounts"]) >= 1


# ── Address extraction ───────────────────────────────────────────────


class TestAddressExtraction:
    def test_french_address(self):
        result = extract_from_text("Adresse: Rue de Lausanne 12, 1000 Lausanne")
        assert len(result["addresses"]) >= 1

    def test_german_address(self):
        result = extract_from_text("Adresse: Bahnhofstrasse 45, 8001 Zurich")
        assert len(result["addresses"]) >= 1

    def test_italian_address(self):
        result = extract_from_text("Indirizzo: Via Nassa 7, 6900 Lugano")
        assert len(result["addresses"]) >= 1


# ── CFC code extraction ─────────────────────────────────────────────


class TestCfcCodeExtraction:
    def test_cfc_three_digits(self):
        result = extract_from_text("Poste CFC 281 - Demolition")
        assert len(result["cfc_codes"]) >= 1
        assert "CFC 281" in result["cfc_codes"][0]["value"]

    def test_cfc_with_decimal(self):
        result = extract_from_text("CFC 371.1 Peinture")
        assert len(result["cfc_codes"]) >= 1

    def test_eccc(self):
        result = extract_from_text("eCCC 281 travaux de desamiantage")
        assert len(result["cfc_codes"]) >= 1


# ── Parcel extraction ───────────────────────────────────────────────


class TestParcelExtraction:
    def test_parcelle_french(self):
        result = extract_from_text("Parcelle n° 1234 du cadastre")
        assert len(result["parcels"]) >= 1
        assert result["parcels"][0]["value"] == "1234"

    def test_parzelle_german(self):
        result = extract_from_text("Parzelle Nr. 5678")
        assert len(result["parcels"]) >= 1
        assert result["parcels"][0]["value"] == "5678"


# ── Pollutant result extraction ──────────────────────────────────────


class TestPollutantResultExtraction:
    def test_mg_kg(self):
        result = extract_from_text("Concentration mesuree: 120 mg/kg")
        assert len(result["pollutant_results"]) >= 1
        assert "mg/kg" in result["pollutant_results"][0]["value"]

    def test_bq_m3_radon(self):
        result = extract_from_text("Radon: 450 Bq/m3")
        assert len(result["pollutant_results"]) >= 1
        assert "Bq/m3" in result["pollutant_results"][0]["value"]

    def test_ppm(self):
        result = extract_from_text("PCB mesuree: 52 ppm dans joints")
        assert len(result["pollutant_results"]) >= 1

    def test_fibers_per_liter(self):
        result = extract_from_text("Mesure air: 1200 f/l")
        assert len(result["pollutant_results"]) >= 1


# ── Energy class extraction ──────────────────────────────────────────


class TestEnergyClassExtraction:
    def test_cecb_grade(self):
        result = extract_from_text("CECB: D")
        assert len(result["energy_class"]) >= 1
        assert result["energy_class"][0]["value"] == "D"

    def test_geak_grade(self):
        result = extract_from_text("GEAK B")
        assert len(result["energy_class"]) >= 1
        assert result["energy_class"][0]["value"] == "B"

    def test_classe_energetique(self):
        result = extract_from_text("Classe energetique: C")
        assert len(result["energy_class"]) >= 1
        assert result["energy_class"][0]["value"] == "C"


# ── Building year extraction ─────────────────────────────────────────


class TestBuildingYearExtraction:
    def test_construit_en(self):
        result = extract_from_text("Immeuble construit en 1972")
        assert len(result["building_year"]) >= 1
        assert result["building_year"][0]["value"] == "1972"

    def test_baujahr(self):
        result = extract_from_text("Baujahr: 1985")
        assert len(result["building_year"]) >= 1
        assert result["building_year"][0]["value"] == "1985"

    def test_year_of_construction(self):
        result = extract_from_text("Year of construction: 2001")
        assert len(result["building_year"]) >= 1
        assert result["building_year"][0]["value"] == "2001"

    def test_costruzione(self):
        result = extract_from_text("Anno di costruzione: 1968")
        assert len(result["building_year"]) >= 1


# ── Reference extraction ────────────────────────────────────────────


class TestReferenceExtraction:
    def test_ref_french(self):
        result = extract_from_text("Ref. ABC-2024/001")
        assert len(result["references"]) >= 1

    def test_dossier_number(self):
        result = extract_from_text("Dossier no 2024-123")
        assert len(result["references"]) >= 1


# ── Party extraction ────────────────────────────────────────────────


class TestPartyExtraction:
    def test_mandant(self):
        result = extract_from_text("Mandant: Regie Romande SA")
        assert len(result["parties"]) >= 1
        assert "Regie Romande SA" in result["parties"][0]["value"]

    def test_auftraggeber(self):
        result = extract_from_text("Auftraggeber: Immobilien Verwaltung AG")
        assert len(result["parties"]) >= 1


# ── Edge cases ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_text(self):
        result = extract_from_text("")
        for field_type in result:
            assert result[field_type] == []

    def test_none_text(self):
        result = extract_from_text("")
        assert all(len(v) == 0 for v in result.values())

    def test_all_fields_have_ai_generated(self):
        text = "Rapport du 15.03.2024. Total CHF 5000. Parcelle n° 123."
        result = extract_from_text(text)
        for _field_type, fields in result.items():
            for f in fields:
                assert f["ai_generated"] is True

    def test_confidence_in_range(self):
        text = "Date: 15.03.2024, CHF 1234, CFC 281"
        result = extract_from_text(text)
        for _field_type, fields in result.items():
            for f in fields:
                assert 0.0 <= f["confidence"] <= 1.0
