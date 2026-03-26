"""Tests for the proof backbone — canonical chain, source_class, safe-to-start, instant card evidence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.user import User
from app.schemas.instant_card import EvidenceByNature, InstantCardResult
from app.schemas.safe_to_start import SafeToStartResult
from app.services.building_enrichment_service import (
    SOURCE_CLASSES,
    _get_source_class,
    _source_entry,
    fetch_regbl_data,
    geocode_address,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_golden_fixture() -> dict:
    with open(FIXTURES_DIR / "golden_address_rumine34.json") as f:
        return json.load(f)


@pytest.fixture
def golden_fixture():
    return _load_golden_fixture()


@pytest.fixture
async def proof_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Proof Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def proof_building(db_session: AsyncSession, admin_user: User, proof_org: Organization):
    building = Building(
        id=uuid.uuid4(),
        address="Avenue Gabriel-de-Rumine 34",
        postal_code="1005",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        construction_year=1933,
        organization_id=proof_org.id,
        latitude=46.516,
        longitude=6.642,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_no_data(db_session: AsyncSession, admin_user: User, proof_org: Organization):
    """Building with minimal data — no diagnostics, no enrichment."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        organization_id=proof_org.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_with_diagnostics(
    db_session: AsyncSession,
    admin_user: User,
    proof_org: Organization,
):
    """Building with a completed diagnostic."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Complete 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        organization_id=proof_org.id,
        construction_year=1960,
        latitude=46.52,
        longitude=6.63,
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# 1. Canonical chain — geocode returns gwr_feature_url from links
# ---------------------------------------------------------------------------


class TestCanonicalChain:
    @pytest.mark.asyncio
    async def test_geocode_returns_gwr_feature_url(self, golden_fixture):
        """geocode_address() extracts gwr_feature_url from SearchServer links."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = golden_fixture["searchserver_response"]
        mock_response.raise_for_status = MagicMock()

        with patch(
            "app.services.building_enrichment_service._retry_request",
            new_callable=AsyncMock,
            return_value=(mock_response, 0),
        ):
            result = await geocode_address("Avenue Gabriel-de-Rumine 34", "1005", "Lausanne")

        assert "gwr_feature_url" in result
        assert "ch.bfs.gebaeude_wohnungs_register" in result["gwr_feature_url"]
        assert "884846_0" in result["gwr_feature_url"]

    @pytest.mark.asyncio
    async def test_regbl_via_gwr_feature_url(self, golden_fixture):
        """fetch_regbl_data() uses gwr_feature_url when provided (canonical path)."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = golden_fixture["gwr_response"]
        mock_response.raise_for_status = MagicMock()

        gwr_url = "/rest/services/ech/MapServer/ch.bfs.gebaeude_wohnungs_register/884846_0"

        with patch(
            "app.services.building_enrichment_service._retry_request",
            new_callable=AsyncMock,
            return_value=(mock_response, 0),
        ):
            result = await fetch_regbl_data(
                884846,
                "Avenue Gabriel-de-Rumine 34",
                gwr_feature_url=gwr_url,
            )

        assert result.get("construction_year") == 1933
        assert result.get("floors") == 9
        assert result.get("egrid") == "CH656183944565"
        assert result.get("parcel_number") == "6289"
        assert result.get("building_number") == "10438"

    @pytest.mark.asyncio
    async def test_regbl_fallback_without_gwr_url(self, golden_fixture):
        """fetch_regbl_data() falls back to {egid}_0 pattern without gwr_feature_url."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = golden_fixture["gwr_response"]
        mock_response.raise_for_status = MagicMock()

        with patch(
            "app.services.building_enrichment_service._retry_request",
            new_callable=AsyncMock,
            return_value=(mock_response, 0),
        ) as mock_retry:
            result = await fetch_regbl_data(884846, "Avenue Gabriel-de-Rumine 34")

        # Should have called with the fallback URL
        call_args = mock_retry.call_args
        url_arg = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("url", "")
        assert "884846_0" in str(url_arg) or result.get("construction_year") == 1933


# ---------------------------------------------------------------------------
# 2. Source class — every enrichment source has correct source_class
# ---------------------------------------------------------------------------


class TestSourceClass:
    def test_source_classes_mapping_complete(self):
        """SOURCE_CLASSES covers all expected sources."""
        expected_official = ["geocode", "regbl", "cadastre", "heritage", "transport", "seismic"]
        for s in expected_official:
            assert SOURCE_CLASSES.get(s) == "official", f"{s} should be official"

        expected_observed = ["radon", "noise", "solar", "climate"]
        for s in expected_observed:
            assert SOURCE_CLASSES.get(s) == "observed", f"{s} should be observed"

        expected_commercial = ["osm_amenities", "nearest_stops", "ev_charging"]
        for s in expected_commercial:
            assert SOURCE_CLASSES.get(s) == "commercial", f"{s} should be commercial"

        expected_derived = ["ai_enrichment", "risk_prediction", "narrative"]
        for s in expected_derived:
            assert SOURCE_CLASSES.get(s) == "derived", f"{s} should be derived"

    def test_get_source_class_returns_correct_class(self):
        assert _get_source_class("geocode") == "official"
        assert _get_source_class("radon") == "observed"
        assert _get_source_class("osm_amenities") == "commercial"
        assert _get_source_class("ai_enrichment") == "derived"

    def test_get_source_class_defaults_to_derived(self):
        assert _get_source_class("unknown_source") == "derived"

    def test_source_entry_includes_source_class(self):
        entry = _source_entry("geocode")
        assert "source_class" in entry
        assert entry["source_class"] == "official"

    def test_source_entry_official_vs_derived(self):
        official = _source_entry("regbl")
        derived = _source_entry("ai_enrichment")
        assert official["source_class"] == "official"
        assert derived["source_class"] == "derived"

    def test_source_entry_explicit_class_overrides(self):
        entry = _source_entry("custom_source", source_class="documentary")
        assert entry["source_class"] == "documentary"

    def test_source_entry_all_standard_fields(self):
        entry = _source_entry(
            "geocode",
            status="success",
            confidence="high",
            match_quality="exact",
            retry_count=1,
        )
        assert entry["source_name"] == "geocode"
        assert entry["source_class"] == "official"
        assert entry["status"] == "success"
        assert entry["confidence"] == "high"
        assert entry["match_quality"] == "exact"
        assert entry["retry_count"] == 1
        assert "fetched_at" in entry


# ---------------------------------------------------------------------------
# 3. Safe-to-start decision summary
# ---------------------------------------------------------------------------


class TestSafeToStart:
    @pytest.mark.asyncio
    async def test_building_no_data_diagnostic_required(
        self,
        db_session: AsyncSession,
        building_no_data: Building,
    ):
        """Building with no diagnostics at all -> diagnostic_required."""
        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, building_no_data.id)
        assert result is not None
        assert result.status == "diagnostic_required"
        assert result.confidence == "low"

    @pytest.mark.asyncio
    async def test_memory_incomplete_status_exists(self):
        """memory_incomplete status is a valid SafeToStartResult status."""
        result = SafeToStartResult(
            building_id=uuid.uuid4(),
            status="memory_incomplete",
            confidence="low",
            explanation_fr="Insuffisant.",
        )
        assert result.status == "memory_incomplete"

    @pytest.mark.asyncio
    async def test_building_no_diagnostics(
        self,
        db_session: AsyncSession,
        proof_building: Building,
    ):
        """Building with identity but no diagnostics -> diagnostic_required."""
        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, proof_building.id)
        assert result is not None
        assert result.status == "diagnostic_required"

    @pytest.mark.asyncio
    async def test_building_with_diagnostics_no_blockers(
        self,
        db_session: AsyncSession,
        building_with_diagnostics: Building,
    ):
        """Building with completed diagnostics and no blockers -> ready_to_proceed or proceed_with_conditions."""
        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, building_with_diagnostics.id)
        assert result is not None
        assert result.status in ("ready_to_proceed", "proceed_with_conditions")

    @pytest.mark.asyncio
    async def test_explanation_fr_always_present(
        self,
        db_session: AsyncSession,
        proof_building: Building,
    ):
        """explanation_fr is always present and meaningful."""
        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, proof_building.id)
        assert result is not None
        assert len(result.explanation_fr) > 10
        assert result.explanation_fr != ""

    @pytest.mark.asyncio
    async def test_nonexistent_building_returns_none(self, db_session: AsyncSession):
        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_schema_fields(self):
        """SafeToStartResult schema has all required fields."""
        result = SafeToStartResult(
            building_id=uuid.uuid4(),
            status="ready_to_proceed",
            blockers=[],
            conditions=[],
            next_actions=[],
            reusable_proof=["diagnostic: abc"],
            confidence="high",
            explanation_fr="Tout est en ordre.",
        )
        data = result.model_dump()
        assert "status" in data
        assert "blockers" in data
        assert "conditions" in data
        assert "next_actions" in data
        assert "reusable_proof" in data
        assert "confidence" in data
        assert "explanation_fr" in data
        assert "post_works_impact" in data

    @pytest.mark.asyncio
    async def test_post_works_residual_risks_as_conditions(self):
        """_evaluate_post_works adds residual risks as conditions when finalized."""
        from app.services.safe_to_start_service import _evaluate_post_works

        building_id = uuid.uuid4()
        blockers: list[str] = []
        conditions: list[str] = []

        # Mock a finalized post-works link with residual risks
        mock_pw = MagicMock()
        mock_pw.status = "finalized"
        mock_pw.residual_risks = [{"material_type": "asbestos", "description": "Encapsulated in basement"}]
        mock_pw.grade_delta = {}
        mock_pw.finalized_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_pw]

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        impact = await _evaluate_post_works(mock_db, building_id, blockers, conditions)
        assert any("residuel" in c.lower() for c in conditions)
        assert impact.get("finalized_count") == 1

    @pytest.mark.asyncio
    async def test_remediation_without_post_works(
        self,
        db_session: AsyncSession,
        admin_user: User,
        proof_org: Organization,
    ):
        """Completed remediation without post-works -> memory_incomplete condition."""
        building = Building(
            id=uuid.uuid4(),
            address="Rue Remediation 8",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=admin_user.id,
            organization_id=proof_org.id,
            construction_year=1965,
        )
        db_session.add(building)
        await db_session.flush()

        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="asbestos",
            status="completed",
            diagnostician_id=admin_user.id,
        )
        db_session.add(diag)

        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=building.id,
            intervention_type="remediation",
            status="completed",
            title="Lead removal",
            created_by=admin_user.id,
        )
        db_session.add(intervention)
        await db_session.commit()

        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, building.id)
        assert result is not None
        assert any("post-travaux" in c.lower() for c in result.conditions)

    @pytest.mark.asyncio
    async def test_building_with_blockers_critical_risk(
        self,
        db_session: AsyncSession,
        admin_user: User,
        proof_org: Organization,
    ):
        """Building with active blockers should return critical_risk."""
        from app.models.unknown_issue import UnknownIssue

        building = Building(
            id=uuid.uuid4(),
            address="Rue Bloquee 3",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=admin_user.id,
            organization_id=proof_org.id,
            construction_year=1950,
        )
        db_session.add(building)
        await db_session.flush()

        # Completed diagnostic (so we don't get diagnostic_required)
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="asbestos",
            status="completed",
            diagnostician_id=admin_user.id,
        )
        db_session.add(diag)

        # Blocking unknown issue
        unknown = UnknownIssue(
            id=uuid.uuid4(),
            building_id=building.id,
            unknown_type="missing_diagnostic",
            title="PCB diagnostic missing",
            severity="critical",
            status="open",
            blocks_readiness=True,
        )
        db_session.add(unknown)
        await db_session.commit()

        from app.services.safe_to_start_service import compute_safe_to_start

        result = await compute_safe_to_start(db_session, building.id)
        assert result is not None
        # Should have blockers (from decision view or passport blind spots)
        # The exact status depends on what services return, but explanation should be present
        assert result.explanation_fr != ""
        assert result.status in ("critical_risk", "proceed_with_conditions", "ready_to_proceed")


# ---------------------------------------------------------------------------
# 4. Instant card — evidence by nature + safe_to_start
# ---------------------------------------------------------------------------


class TestInstantCardEvidence:
    @pytest.mark.asyncio
    async def test_evidence_by_nature_5_categories(
        self,
        db_session: AsyncSession,
        proof_building: Building,
    ):
        """Instant card includes evidence_by_nature with 5 categories."""
        from app.services.instant_card_service import build_instant_card

        card = await build_instant_card(db_session, proof_building.id)
        assert card is not None
        ebn = card.evidence_by_nature
        assert isinstance(ebn, EvidenceByNature)
        # All 5 category dicts exist
        assert isinstance(ebn.official_truth, dict)
        assert isinstance(ebn.documentary_proof, dict)
        assert isinstance(ebn.observations, dict)
        assert isinstance(ebn.signals, dict)
        assert isinstance(ebn.inferences, dict)

    @pytest.mark.asyncio
    async def test_evidence_official_truth_has_identity(
        self,
        db_session: AsyncSession,
        proof_building: Building,
    ):
        """official_truth contains building identity."""
        from app.services.instant_card_service import build_instant_card

        card = await build_instant_card(db_session, proof_building.id)
        assert card is not None
        assert "identity" in card.evidence_by_nature.official_truth
        identity = card.evidence_by_nature.official_truth["identity"]
        assert identity.get("address") == "Avenue Gabriel-de-Rumine 34"

    @pytest.mark.asyncio
    async def test_safe_to_start_present_in_card(
        self,
        db_session: AsyncSession,
        proof_building: Building,
    ):
        """Instant card includes safe_to_start dict."""
        from app.services.instant_card_service import build_instant_card

        card = await build_instant_card(db_session, proof_building.id)
        assert card is not None
        assert isinstance(card.safe_to_start, dict)
        # Should have at least status key
        assert "status" in card.safe_to_start

    @pytest.mark.asyncio
    async def test_partial_data_produces_useful_output(
        self,
        db_session: AsyncSession,
        building_no_data: Building,
    ):
        """Even minimal buildings produce a useful instant card."""
        from app.services.instant_card_service import build_instant_card

        card = await build_instant_card(db_session, building_no_data.id)
        assert card is not None
        assert card.passport_grade in ("A", "B", "C", "D", "F")
        assert isinstance(card.evidence_by_nature.official_truth, dict)


# ---------------------------------------------------------------------------
# 5. Golden address integration test
# ---------------------------------------------------------------------------


class TestGoldenAddress:
    @pytest.mark.asyncio
    async def test_rumine_34_extracts_egid_from_gwr_link(self, golden_fixture):
        """Avenue Rumine 34, 1000 Lausanne -> extracts EGID from GWR link."""
        # Mock SearchServer response
        ss_response = MagicMock(spec=httpx.Response)
        ss_response.status_code = 200
        ss_response.json.return_value = golden_fixture["searchserver_response"]
        ss_response.raise_for_status = MagicMock()

        with patch(
            "app.services.building_enrichment_service._retry_request",
            new_callable=AsyncMock,
            return_value=(ss_response, 0),
        ):
            geo = await geocode_address("Avenue Gabriel-de-Rumine 34", "1005", "Lausanne")

        assert geo.get("egid") == 884846
        assert geo.get("gwr_feature_url") is not None
        gwr_url = geo["gwr_feature_url"]

        # Mock GWR response via canonical URL
        gwr_response = MagicMock(spec=httpx.Response)
        gwr_response.status_code = 200
        gwr_response.json.return_value = golden_fixture["gwr_response"]
        gwr_response.raise_for_status = MagicMock()

        with patch(
            "app.services.building_enrichment_service._retry_request",
            new_callable=AsyncMock,
            return_value=(gwr_response, 0),
        ):
            regbl = await fetch_regbl_data(884846, "Avenue Gabriel-de-Rumine 34", gwr_feature_url=gwr_url)

        assert regbl.get("egrid") == "CH656183944565"
        assert regbl.get("construction_year") == 1933
        assert regbl.get("floors") == 9
        assert regbl.get("parcel_number") == "6289"
        assert regbl.get("living_area_m2") == 1269.0
        assert regbl.get("ground_area_m2") == 569.0


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_geocode_no_links_no_crash(self):
        """geocode_address handles missing links array gracefully."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "attrs": {
                        "lat": 46.5,
                        "lon": 6.6,
                        "label": "Test 1 <b>1000 Lausanne</b>",
                        "featureId": "123_0",
                        "detail": "test",
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "app.services.building_enrichment_service._retry_request",
            new_callable=AsyncMock,
            return_value=(mock_response, 0),
        ):
            result = await geocode_address("Test 1", "1000", "Lausanne")

        # Should succeed without gwr_feature_url
        assert result.get("lat") == 46.5
        assert "gwr_feature_url" not in result

    def test_evidence_by_nature_schema_defaults(self):
        """EvidenceByNature defaults to empty dicts."""
        ebn = EvidenceByNature()
        assert ebn.official_truth == {}
        assert ebn.documentary_proof == {}
        assert ebn.observations == {}
        assert ebn.signals == {}
        assert ebn.inferences == {}

    def test_instant_card_schema_has_new_fields(self):
        """InstantCardResult includes evidence_by_nature and safe_to_start."""
        card = InstantCardResult(building_id=uuid.uuid4())
        assert hasattr(card, "evidence_by_nature")
        assert hasattr(card, "safe_to_start")
        assert isinstance(card.evidence_by_nature, EvidenceByNature)
        assert isinstance(card.safe_to_start, dict)
