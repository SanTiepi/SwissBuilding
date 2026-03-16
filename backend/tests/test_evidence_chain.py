"""Tests for Evidence Chain service and API endpoints."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.evidence_chain_service import (
    assess_evidence_strength,
    build_evidence_timeline,
    get_provenance_gaps,
    validate_evidence_chain,
)


def _make_token(user_id, email, role):
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
async def setup_building(db_session):
    """Create a building with full evidence chain for testing."""
    user = User(
        id=uuid.uuid4(),
        email="chain-admin@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg2PzSh3Kxqzxu7vFJHk0MIl3T6Y5Y4Y5Y4Y5Y4Y5Y4Y5",
        first_name="Chain",
        last_name="Admin",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)

    building = Building(
        id=uuid.uuid4(),
        address="Rue Evidence 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(building)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=user.id,
        laboratory="LabTest SA",
        laboratory_report_number="LT-2024-001",
        date_inspection=date(2024, 6, 15),
        date_report=date(2024, 7, 1),
    )
    db_session.add(diag)

    sample1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        location_floor="1er",
        pollutant_type="asbestos",
        concentration=1.2,
        unit="%",
        threshold_exceeded=True,
        risk_level="high",
        created_at=datetime.now(UTC),
    )
    sample2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S002",
        location_floor="2eme",
        pollutant_type="asbestos",
        concentration=0.0,
        unit="%",
        threshold_exceeded=False,
        risk_level="low",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([sample1, sample2])

    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/report.pdf",
        file_name="rapport_amiante.pdf",
        document_type="diagnostic_report",
        uploaded_by=user.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(doc)

    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="removal",
        title="Asbestos removal floor 1",
        status="completed",
        diagnostic_id=diag.id,
        date_start=date(2024, 8, 1),
        created_by=user.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(intervention)

    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_id=diag.id,
        sample_id=sample1.id,
        source_type="diagnostic",
        action_type="removal",
        title="Remove asbestos from floor 1",
        priority="high",
        status="open",
        created_by=user.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(action)

    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        name="Floor 1",
        zone_type="floor",
    )
    db_session.add(zone)

    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building.id,
        artefact_type="suva_notification",
        status="submitted",
        title="SUVA notification amiante",
        diagnostic_id=diag.id,
        created_by=user.id,
    )
    db_session.add(artefact)

    await db_session.commit()

    return {
        "user": user,
        "building": building,
        "diagnostic": diag,
        "samples": [sample1, sample2],
        "document": doc,
        "intervention": intervention,
        "action": action,
        "zone": zone,
        "artefact": artefact,
    }


# --------------------------------------------------------------------------
# Service Tests: validate_evidence_chain
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidateEvidenceChain:
    async def test_complete_chain_high_score(self, db_session, setup_building):
        """A complete evidence chain should score high."""
        data = setup_building
        result = await validate_evidence_chain(db_session, data["building"].id)
        assert result.integrity_score >= 80
        assert result.total_checks > 0
        assert result.passed_checks > 0

    async def test_empty_building_perfect_score(self, db_session, sample_building):
        """A building with no entities should get 100 (no checks to fail)."""
        result = await validate_evidence_chain(db_session, sample_building.id)
        assert result.integrity_score == 100
        assert result.total_checks == 0

    async def test_diagnostic_without_samples_medium_break(self, db_session, admin_user, sample_building):
        """Diagnostic with no samples should produce a medium broken link."""
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="pcb",
            status="draft",
        )
        db_session.add(diag)
        await db_session.commit()

        result = await validate_evidence_chain(db_session, sample_building.id)
        medium_breaks = [b for b in result.broken_links if b.severity == "medium"]
        assert len(medium_breaks) >= 1
        assert any("no samples" in b.issue for b in medium_breaks)

    async def test_intervention_without_diagnostic_link(self, db_session, admin_user, sample_building):
        """Intervention without diagnostic link should be flagged."""
        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            intervention_type="encapsulation",
            title="Seal pipes",
            status="planned",
        )
        db_session.add(intervention)
        await db_session.commit()

        result = await validate_evidence_chain(db_session, sample_building.id)
        breaks = [b for b in result.broken_links if b.entity_type == "intervention"]
        assert len(breaks) >= 1

    async def test_broken_links_returned(self, db_session, setup_building):
        """Broken links list should contain valid BrokenLink objects."""
        data = setup_building
        result = await validate_evidence_chain(db_session, data["building"].id)
        for bl in result.broken_links:
            assert bl.entity_type in ("sample", "diagnostic", "compliance_artefact", "intervention")
            assert bl.severity in ("critical", "high", "medium", "low")


# --------------------------------------------------------------------------
# Service Tests: get_provenance_gaps
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetProvenanceGaps:
    async def test_no_gaps_complete_data(self, db_session, setup_building):
        """Complete data should have no or minimal gaps."""
        data = setup_building
        result = await get_provenance_gaps(db_session, data["building"].id)
        # Complete data: all fields filled — should have 0 gaps
        assert result.total_gaps == 0

    async def test_document_without_uploader(self, db_session, admin_user, sample_building):
        """Document without uploaded_by should be flagged."""
        doc = Document(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            file_path="/docs/orphan.pdf",
            file_name="orphan.pdf",
            uploaded_by=None,
        )
        db_session.add(doc)
        await db_session.commit()

        result = await get_provenance_gaps(db_session, sample_building.id)
        doc_gaps = [g for g in result.gaps if g.entity_type == "document"]
        assert len(doc_gaps) >= 1
        assert doc_gaps[0].gap_type == "missing_source"

    async def test_diagnostic_without_diagnostician(self, db_session, admin_user, sample_building):
        """Diagnostic without diagnostician_id should be flagged."""
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="lead",
            status="draft",
            diagnostician_id=None,
        )
        db_session.add(diag)
        await db_session.commit()

        result = await get_provenance_gaps(db_session, sample_building.id)
        diag_gaps = [g for g in result.gaps if g.entity_type == "diagnostic"]
        assert len(diag_gaps) >= 1
        assert diag_gaps[0].gap_type == "missing_author"

    async def test_action_without_trigger(self, db_session, admin_user, sample_building):
        """Action without diagnostic/sample link should be flagged."""
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            source_type="manual",
            action_type="inspection",
            title="Manual check",
            priority="low",
            status="open",
        )
        db_session.add(action)
        await db_session.commit()

        result = await get_provenance_gaps(db_session, sample_building.id)
        action_gaps = [g for g in result.gaps if g.entity_type == "action"]
        assert len(action_gaps) >= 1
        assert action_gaps[0].gap_type == "missing_trigger"

    async def test_sample_without_lab_reference(self, db_session, admin_user, sample_building):
        """Sample whose diagnostic has no lab should be flagged."""
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            diagnostic_type="hap",
            status="draft",
            diagnostician_id=admin_user.id,
            laboratory=None,
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="X001",
            pollutant_type="hap",
        )
        db_session.add(sample)
        await db_session.commit()

        result = await get_provenance_gaps(db_session, sample_building.id)
        sample_gaps = [g for g in result.gaps if g.entity_type == "sample"]
        assert len(sample_gaps) >= 1
        assert sample_gaps[0].gap_type == "missing_lab_reference"

    async def test_empty_building_no_gaps(self, db_session, sample_building):
        """Empty building should have no gaps."""
        result = await get_provenance_gaps(db_session, sample_building.id)
        assert result.total_gaps == 0


# --------------------------------------------------------------------------
# Service Tests: build_evidence_timeline
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBuildEvidenceTimeline:
    async def test_timeline_ordered_by_date(self, db_session, setup_building):
        """Timeline events should be ordered chronologically."""
        data = setup_building
        result = await build_evidence_timeline(db_session, data["building"].id)
        assert result.total_events > 0
        for i in range(1, len(result.events)):
            assert result.events[i].date >= result.events[i - 1].date

    async def test_timeline_contains_all_entity_types(self, db_session, setup_building):
        """Timeline should include diagnostics, samples, documents, interventions, actions."""
        data = setup_building
        result = await build_evidence_timeline(db_session, data["building"].id)
        entity_types = {e.entity_type for e in result.events}
        assert "diagnostic" in entity_types
        assert "sample" in entity_types
        assert "document" in entity_types
        assert "intervention" in entity_types
        assert "action" in entity_types

    async def test_timeline_empty_building(self, db_session, sample_building):
        """Empty building should have 0 events."""
        result = await build_evidence_timeline(db_session, sample_building.id)
        assert result.total_events == 0
        assert result.events == []

    async def test_timeline_event_has_actor(self, db_session, setup_building):
        """Events with known actors should include actor info."""
        data = setup_building
        result = await build_evidence_timeline(db_session, data["building"].id)
        actor_events = [e for e in result.events if e.actor_name is not None]
        assert len(actor_events) > 0


# --------------------------------------------------------------------------
# Service Tests: assess_evidence_strength
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAssessEvidenceStrength:
    async def test_strength_all_pollutants(self, db_session, setup_building):
        """Should return strength for all 5 pollutant types."""
        data = setup_building
        result = await assess_evidence_strength(db_session, data["building"].id)
        assert len(result.pollutants) == 5
        types = {p.pollutant_type for p in result.pollutants}
        assert types == {"asbestos", "pcb", "lead", "hap", "radon"}

    async def test_strength_asbestos_detected(self, db_session, setup_building):
        """Asbestos with threshold-exceeding samples should be 'detected'."""
        data = setup_building
        result = await assess_evidence_strength(db_session, data["building"].id)
        asbestos = next(p for p in result.pollutants if p.pollutant_type == "asbestos")
        assert asbestos.claim == "detected"
        assert asbestos.sample_count == 2

    async def test_strength_unknown_pollutants(self, db_session, setup_building):
        """Pollutants with no samples should be 'unknown' and 'insufficient'."""
        data = setup_building
        result = await assess_evidence_strength(db_session, data["building"].id)
        pcb = next(p for p in result.pollutants if p.pollutant_type == "pcb")
        assert pcb.claim == "unknown"
        assert pcb.strength == "insufficient"
        assert pcb.sample_count == 0

    async def test_strength_empty_building(self, db_session, sample_building):
        """Empty building: all pollutants unknown/insufficient."""
        result = await assess_evidence_strength(db_session, sample_building.id)
        assert result.overall_strength == "insufficient"
        for p in result.pollutants:
            assert p.claim == "unknown"
            assert p.strength == "insufficient"

    async def test_overall_strength_computed(self, db_session, setup_building):
        """Overall strength should be one of the valid values."""
        data = setup_building
        result = await assess_evidence_strength(db_session, data["building"].id)
        assert result.overall_strength in ("strong", "moderate", "weak", "insufficient")

    async def test_strength_has_lab_reference(self, db_session, setup_building):
        """Asbestos with lab-backed diagnostic should have has_lab_reference=True."""
        data = setup_building
        result = await assess_evidence_strength(db_session, data["building"].id)
        asbestos = next(p for p in result.pollutants if p.pollutant_type == "asbestos")
        assert asbestos.has_lab_reference is True


# --------------------------------------------------------------------------
# API Tests
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEvidenceChainAPI:
    async def test_validate_endpoint(self, client, setup_building):
        """GET /buildings/{id}/evidence-chain/validate should return 200."""
        data = setup_building
        headers = {"Authorization": f"Bearer {_make_token(data['user'].id, data['user'].email, 'admin')}"}
        resp = await client.get(
            f"/api/v1/buildings/{data['building'].id}/evidence-chain/validate",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "integrity_score" in body
        assert "broken_links" in body

    async def test_provenance_gaps_endpoint(self, client, setup_building):
        """GET /buildings/{id}/evidence-chain/provenance-gaps should return 200."""
        data = setup_building
        headers = {"Authorization": f"Bearer {_make_token(data['user'].id, data['user'].email, 'admin')}"}
        resp = await client.get(
            f"/api/v1/buildings/{data['building'].id}/evidence-chain/provenance-gaps",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_gaps" in body
        assert "gaps" in body

    async def test_timeline_endpoint(self, client, setup_building):
        """GET /buildings/{id}/evidence-chain/timeline should return 200."""
        data = setup_building
        headers = {"Authorization": f"Bearer {_make_token(data['user'].id, data['user'].email, 'admin')}"}
        resp = await client.get(
            f"/api/v1/buildings/{data['building'].id}/evidence-chain/timeline",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "events" in body
        assert "total_events" in body

    async def test_strength_endpoint(self, client, setup_building):
        """GET /buildings/{id}/evidence-chain/strength should return 200."""
        data = setup_building
        headers = {"Authorization": f"Bearer {_make_token(data['user'].id, data['user'].email, 'admin')}"}
        resp = await client.get(
            f"/api/v1/buildings/{data['building'].id}/evidence-chain/strength",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "pollutants" in body
        assert "overall_strength" in body
        assert len(body["pollutants"]) == 5

    async def test_unauthenticated_returns_403(self, client, setup_building):
        """Endpoints should reject unauthenticated requests."""
        data = setup_building
        resp = await client.get(f"/api/v1/buildings/{data['building'].id}/evidence-chain/validate")
        assert resp.status_code == 403
