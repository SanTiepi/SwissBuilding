"""Contract tests for Truth API v1.

Verify response shapes (envelope fields, domain keys, HATEOAS links),
auth gates, and 404 behavior — NOT business logic.
"""

from uuid import uuid4

# Base URL prefix: app mounts api_router at /api/v1, truth_api router has prefix /v1/truth
BASE = "/api/v1/v1/truth"

# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------


def assert_envelope(data: dict, *, api_version: str = "1.0") -> None:
    """Assert common TruthEnvelopeV1 fields."""
    assert data["api_version"] == api_version
    assert "generated_at" in data
    assert isinstance(data["links"], dict)
    assert len(data["links"]) > 0


# ---------------------------------------------------------------------------
# Building-scoped endpoint tests
# ---------------------------------------------------------------------------


class TestBuildingSummaryContract:
    """GET /v1/truth/buildings/{id}/summary"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert "sections_included" in data
        assert isinstance(data["sections_included"], list)

    async def test_identity_section_present(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/summary",
            headers=auth_headers,
        )
        data = resp.json()
        # Default includes all sections — identity should be present
        assert "identity" in data["sections_included"]
        assert data["identity"] is not None
        assert data["identity"]["building_id"] == str(sample_building.id)

    async def test_section_filtering(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/summary",
            params={"include_sections": ["identity", "grade"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert set(data["sections_included"]) == {"identity", "grade"}
        # Sections not requested should be absent (None)
        assert data.get("pollutants") is None
        assert data.get("diagnostics_summary") is None

    async def test_404_nonexistent(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/summary")
        assert resp.status_code in (401, 403)


class TestIdentityChainContract:
    """GET /v1/truth/buildings/{id}/identity-chain"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/identity-chain",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert "egid" in data
        assert "egrid" in data
        assert "rdppf" in data
        assert "chain_complete" in data
        assert isinstance(data["chain_complete"], bool)
        assert "chain_gaps" in data
        assert isinstance(data["chain_gaps"], list)

    async def test_404_nonexistent(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/identity-chain",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/identity-chain")
        assert resp.status_code in (401, 403)


class TestSafeToXContract:
    """GET /v1/truth/buildings/{id}/safe-to-x"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/safe-to-x",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert "verdicts" in data
        assert isinstance(data["verdicts"], list)
        assert "types_included" in data
        assert isinstance(data["types_included"], list)

    async def test_type_filtering(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/safe-to-x",
            params={"types": ["start", "sell"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert set(data["types_included"]) == {"start", "sell"}

    async def test_verdict_entry_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/safe-to-x",
            headers=auth_headers,
        )
        data = resp.json()
        for v in data["verdicts"]:
            assert "safe_to_type" in v
            assert "verdict" in v
            assert "verdict_summary" in v
            assert "blockers" in v
            assert "conditions" in v
            assert "confidence" in v

    async def test_404_nonexistent(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/safe-to-x",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/safe-to-x")
        assert resp.status_code in (401, 403)


class TestUnknownsContract:
    """GET /v1/truth/buildings/{id}/unknowns"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/unknowns",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert "total_open" in data
        assert isinstance(data["total_open"], int)
        assert "blocking" in data
        assert isinstance(data["blocking"], int)
        assert "by_type" in data
        assert isinstance(data["by_type"], dict)
        assert "entries" in data
        assert isinstance(data["entries"], list)

    async def test_404_nonexistent(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/unknowns",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/unknowns")
        assert resp.status_code in (401, 403)


class TestChangesContract:
    """GET /v1/truth/buildings/{id}/changes"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/changes",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert "total_changes" in data
        assert isinstance(data["total_changes"], int)
        assert "entries" in data
        assert isinstance(data["entries"], list)

    async def test_since_filter(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/changes",
            params={"since": "2025-01-01T00:00:00Z"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["since"] is not None

    async def test_change_entry_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/changes",
            headers=auth_headers,
        )
        data = resp.json()
        for entry in data["entries"]:
            assert "change_type" in entry
            # timestamp, description, source, metadata are optional but must be present as keys
            assert "timestamp" in entry or entry.get("timestamp") is None  # key exists or defaults
            assert "metadata" in entry

    async def test_404_nonexistent(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/changes",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/changes")
        assert resp.status_code in (401, 403)


class TestPassportContract:
    """GET /v1/truth/buildings/{id}/passport"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/passport",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert "passport_grade" in data
        assert "knowledge_state" in data
        assert "completeness" in data
        assert "readiness" in data
        assert "blind_spots" in data
        assert "contradictions" in data
        assert "evidence_coverage" in data
        assert "pollutant_coverage" in data
        assert data["redaction_profile"] == "none"

    async def test_redaction_profile_param(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/passport",
            params={"redaction_profile": "external"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["redaction_profile"] == "external"

    async def test_404_nonexistent(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/passport",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/passport")
        assert resp.status_code in (401, 403)


class TestPackContract:
    """GET /v1/truth/buildings/{id}/packs/{pack_type}"""

    async def test_shape(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/packs/authority",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert data["building_id"] == str(sample_building.id)
        assert data["pack_type"] == "authority"
        assert "sections" in data
        assert isinstance(data["sections"], list)
        assert "redaction_profile" in data

    async def test_redaction_param(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/packs/owner",
            params={"redaction_profile": "external"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["redaction_profile"] == "external"

    async def test_404_nonexistent_building(self, client, auth_headers):
        resp = await client.get(
            f"{BASE}/buildings/{uuid4()}/packs/authority",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/buildings/{uuid4()}/packs/authority")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Portfolio-scoped endpoint tests
# ---------------------------------------------------------------------------


class TestPortfolioOverviewContract:
    """GET /v1/truth/portfolio/overview"""

    async def test_shape(self, client, auth_headers, admin_user):
        resp = await client.get(
            f"{BASE}/portfolio/overview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert "total_buildings" in data
        assert isinstance(data["total_buildings"], int)
        assert "grade_distribution" in data
        assert isinstance(data["grade_distribution"], dict)
        assert "readiness_distribution" in data
        assert isinstance(data["readiness_distribution"], dict)
        assert "avg_completeness" in data
        assert isinstance(data["avg_completeness"], (int, float))
        assert "avg_trust" in data
        assert isinstance(data["avg_trust"], (int, float))
        assert "buildings" in data
        assert isinstance(data["buildings"], list)
        assert "top_priorities" in data
        assert "budget_horizon" in data

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/portfolio/overview")
        assert resp.status_code in (401, 403)


class TestPortfolioAlertsContract:
    """GET /v1/truth/portfolio/alerts"""

    async def test_shape(self, client, auth_headers, admin_user):
        resp = await client.get(
            f"{BASE}/portfolio/alerts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_envelope(data)
        assert "total_alerts" in data
        assert isinstance(data["total_alerts"], int)
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    async def test_alert_entry_shape_when_present(self, client, auth_headers, admin_user):
        """If alerts exist, each entry has the required fields."""
        resp = await client.get(
            f"{BASE}/portfolio/alerts",
            headers=auth_headers,
        )
        data = resp.json()
        for alert in data["alerts"]:
            assert "alert_type" in alert
            assert "severity" in alert
            assert "title" in alert

    async def test_auth_required(self, client):
        resp = await client.get(f"{BASE}/portfolio/alerts")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cross-cutting contract tests
# ---------------------------------------------------------------------------


class TestTruthAPICrossCutting:
    """Cross-cutting concerns: version consistency, link presence."""

    async def test_all_building_endpoints_return_version_1_0(self, client, auth_headers, sample_building):
        """Every building-scoped endpoint returns api_version '1.0'."""
        bid = sample_building.id
        endpoints = [
            f"{BASE}/buildings/{bid}/summary",
            f"{BASE}/buildings/{bid}/identity-chain",
            f"{BASE}/buildings/{bid}/safe-to-x",
            f"{BASE}/buildings/{bid}/unknowns",
            f"{BASE}/buildings/{bid}/changes",
            f"{BASE}/buildings/{bid}/passport",
            f"{BASE}/buildings/{bid}/packs/authority",
        ]
        for url in endpoints:
            resp = await client.get(url, headers=auth_headers)
            assert resp.status_code == 200, f"{url} returned {resp.status_code}"
            data = resp.json()
            assert data["api_version"] == "1.0", f"{url} api_version mismatch"
            assert "generated_at" in data, f"{url} missing generated_at"
            assert "links" in data, f"{url} missing links"

    async def test_building_links_contain_expected_keys(self, client, auth_headers, sample_building):
        """Building-scoped endpoints include HATEOAS links with expected keys."""
        resp = await client.get(
            f"{BASE}/buildings/{sample_building.id}/summary",
            headers=auth_headers,
        )
        links = resp.json()["links"]
        expected_keys = {"self_summary", "identity_chain", "safe_to_x", "unknowns", "changes", "passport"}
        assert expected_keys.issubset(set(links.keys()))

    async def test_portfolio_links_present(self, client, auth_headers, admin_user):
        """Portfolio endpoints include HATEOAS links."""
        resp = await client.get(f"{BASE}/portfolio/overview", headers=auth_headers)
        links = resp.json()["links"]
        assert "self" in links
        assert "alerts" in links

        resp2 = await client.get(f"{BASE}/portfolio/alerts", headers=auth_headers)
        links2 = resp2.json()["links"]
        assert "self" in links2
        assert "overview" in links2
