"""Tests for authority pack generation service and API."""

import uuid
from datetime import UTC, datetime

import pytest

from app.api.authority_packs import router as authority_packs_router
from app.main import app
from app.models.action_item import ActionItem
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_pack import EvidencePack
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.authority_pack import AuthorityPackConfig
from app.services.authority_pack_service import (
    ALL_SECTION_TYPES,
    generate_authority_pack,
    get_authority_pack,
    list_authority_packs,
)

app.include_router(authority_packs_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_diagnostic(db_session, building_id, **kwargs):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=kwargs.get("diagnostic_type", "asbestos"),
        status=kwargs.get("status", "completed"),
        laboratory=kwargs.get("laboratory", "LabTest SA"),
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


async def _create_sample(db_session, diagnostic_id, **kwargs):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=kwargs.get("sample_number", "S-001"),
        pollutant_type=kwargs.get("pollutant_type", "asbestos"),
        concentration=kwargs.get("concentration", 2.5),
        unit=kwargs.get("unit", "percent_weight"),
        threshold_exceeded=kwargs.get("threshold_exceeded", True),
        risk_level=kwargs.get("risk_level", "high"),
        material_category=kwargs.get("material_category", "flocage"),
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


async def _create_action(db_session, building_id, **kwargs):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        source_type=kwargs.get("source_type", "diagnostic"),
        action_type=kwargs.get("action_type", "remove_planned"),
        title=kwargs.get("title", "Retrait amiante flocage"),
        priority=kwargs.get("priority", "high"),
        status=kwargs.get("status", "open"),
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


async def _create_document(db_session, building_id, **kwargs):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/test/doc.pdf",
        file_name=kwargs.get("file_name", "rapport.pdf"),
        document_type=kwargs.get("document_type", "lab_report"),
        file_size_bytes=kwargs.get("file_size_bytes", 1024),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


async def _create_intervention(db_session, building_id, **kwargs):
    interv = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=kwargs.get("intervention_type", "removal"),
        title=kwargs.get("title", "Retrait amiante"),
        status=kwargs.get("status", "completed"),
    )
    db_session.add(interv)
    await db_session.commit()
    await db_session.refresh(interv)
    return interv


async def _create_compliance_artefact(db_session, building_id, **kwargs):
    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building_id,
        artefact_type=kwargs.get("artefact_type", "waste_manifest"),
        title=kwargs.get("title", "Plan elimination dechets"),
        status=kwargs.get("status", "submitted"),
        authority_name=kwargs.get("authority_name", "DGE-DIRNA"),
    )
    db_session.add(artefact)
    await db_session.commit()
    await db_session.refresh(artefact)
    return artefact


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestGenerateAuthorityPack:
    async def test_generate_empty_building(self, db_session, sample_building, admin_user):
        """Pack on an empty building should have all sections but low completeness."""
        config = AuthorityPackConfig(building_id=sample_building.id)
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        assert result.pack_id is not None
        assert result.building_id == sample_building.id
        assert result.canton == "VD"
        assert result.total_sections == len(ALL_SECTION_TYPES)
        assert len(result.sections) == len(ALL_SECTION_TYPES)
        # Building identity should have some completeness (address + canton exist)
        identity = next(s for s in result.sections if s.section_type == "building_identity")
        assert identity.completeness > 0.0
        # Diagnostic summary should have 0 items
        diag_section = next(s for s in result.sections if s.section_type == "diagnostic_summary")
        assert len(diag_section.items) == 0

    async def test_generate_with_seeded_data(self, db_session, sample_building, admin_user):
        """Pack with diagnostics, samples, actions, docs should have higher completeness."""
        diag = await _create_diagnostic(db_session, sample_building.id)
        await _create_sample(db_session, diag.id)
        await _create_action(db_session, sample_building.id)
        await _create_document(db_session, sample_building.id)
        await _create_intervention(db_session, sample_building.id)
        await _create_compliance_artefact(db_session, sample_building.id)

        config = AuthorityPackConfig(building_id=sample_building.id)
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        assert result.total_sections == len(ALL_SECTION_TYPES)
        assert result.overall_completeness > 0.5

        # Check sections have items
        diag_section = next(s for s in result.sections if s.section_type == "diagnostic_summary")
        assert len(diag_section.items) == 1

        sample_section = next(s for s in result.sections if s.section_type == "sample_results")
        assert len(sample_section.items) == 1

        action_section = next(s for s in result.sections if s.section_type == "action_plan")
        assert len(action_section.items) == 1

        doc_section = next(s for s in result.sections if s.section_type == "document_inventory")
        assert len(doc_section.items) == 1

    async def test_section_filtering(self, db_session, sample_building, admin_user):
        """Only requested sections should be included."""
        config = AuthorityPackConfig(
            building_id=sample_building.id,
            include_sections=["building_identity", "risk_assessment"],
        )
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        assert result.total_sections == 2
        section_types = {s.section_type for s in result.sections}
        assert section_types == {"building_identity", "risk_assessment"}

    async def test_unknown_section_type_warning(self, db_session, sample_building, admin_user):
        """Unknown section types produce warnings."""
        config = AuthorityPackConfig(
            building_id=sample_building.id,
            include_sections=["building_identity", "nonexistent_section"],
        )
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        assert result.total_sections == 1
        assert any("nonexistent_section" in w for w in result.warnings)

    async def test_evidence_pack_record_created(self, db_session, sample_building, admin_user):
        """An EvidencePack record should be created in the DB."""
        config = AuthorityPackConfig(building_id=sample_building.id)
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        from sqlalchemy import select

        pack_result = await db_session.execute(select(EvidencePack).where(EvidencePack.id == result.pack_id))
        pack = pack_result.scalar_one_or_none()
        assert pack is not None
        assert pack.pack_type == "authority_pack"
        assert pack.status == "complete"
        assert pack.building_id == sample_building.id
        assert pack.created_by == admin_user.id

    async def test_building_not_found(self, db_session, admin_user):
        """Should raise ValueError for non-existent building."""
        fake_id = uuid.uuid4()
        config = AuthorityPackConfig(building_id=fake_id)
        with pytest.raises(ValueError, match="Building not found"):
            await generate_authority_pack(db_session, fake_id, config, admin_user.id)

    async def test_canton_auto_detect(self, db_session, sample_building, admin_user):
        """Canton should be auto-detected from building."""
        config = AuthorityPackConfig(building_id=sample_building.id, canton=None)
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)
        assert result.canton == "VD"

    async def test_canton_override(self, db_session, sample_building, admin_user):
        """Explicit canton should override auto-detect."""
        config = AuthorityPackConfig(building_id=sample_building.id, canton="GE")
        result = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)
        assert result.canton == "GE"


class TestListAuthorityPacks:
    async def test_list_empty(self, db_session, sample_building):
        result = await list_authority_packs(db_session, sample_building.id)
        assert result == []

    async def test_list_after_generation(self, db_session, sample_building, admin_user):
        config = AuthorityPackConfig(building_id=sample_building.id)
        await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        result = await list_authority_packs(db_session, sample_building.id)
        assert len(result) == 1
        assert result[0].building_id == sample_building.id
        assert result[0].canton == "VD"
        assert result[0].status == "complete"


class TestGetAuthorityPack:
    async def test_get_existing(self, db_session, sample_building, admin_user):
        config = AuthorityPackConfig(building_id=sample_building.id)
        generated = await generate_authority_pack(db_session, sample_building.id, config, admin_user.id)

        result = await get_authority_pack(db_session, generated.pack_id)
        assert result is not None
        assert result.pack_id == generated.pack_id
        assert result.canton == "VD"

    async def test_get_nonexistent(self, db_session):
        result = await get_authority_pack(db_session, uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


class TestAuthorityPackAPI:
    async def test_generate_endpoint(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/authority-packs/generate",
            json={"language": "fr"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["building_id"] == str(sample_building.id)
        assert data["canton"] == "VD"
        assert data["total_sections"] == len(ALL_SECTION_TYPES)
        assert "sections" in data

    async def test_generate_404_building(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/authority-packs/generate",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_list_endpoint(self, client, admin_user, auth_headers, sample_building):
        # Generate one first
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/authority-packs/generate",
            json={},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/authority-packs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_get_pack_endpoint(self, client, admin_user, auth_headers, sample_building):
        gen_response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/authority-packs/generate",
            json={},
            headers=auth_headers,
        )
        pack_id = gen_response.json()["pack_id"]
        response = await client.get(
            f"/api/v1/authority-packs/{pack_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["pack_id"] == pack_id

    async def test_get_pack_404(self, client, admin_user, auth_headers):
        response = await client.get(
            f"/api/v1/authority-packs/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_permission_denied_for_contractor(self, client, db_session):
        """Contractor role should not have buildings:update for generation."""
        from jose import jwt

        from app.models.user import User

        contractor = User(
            id=uuid.uuid4(),
            email="contractor@test.ch",
            password_hash="$2b$12$LJ3m4ks/abc",  # dummy hash
            first_name="Hans",
            last_name="Weber",
            role="contractor",
            is_active=True,
            language="fr",
        )
        db_session.add(contractor)
        await db_session.commit()

        from app.models.building import Building

        building = Building(
            id=uuid.uuid4(),
            address="Rue Test 2",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1970,
            building_type="residential",
            created_by=contractor.id,
            status="active",
        )
        db_session.add(building)
        await db_session.commit()

        payload = {
            "sub": str(contractor.id),
            "email": contractor.email,
            "role": "contractor",
            "exp": datetime.now(UTC).timestamp() + 3600,
        }
        token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            f"/api/v1/buildings/{building.id}/authority-packs/generate",
            json={},
            headers=headers,
        )
        assert response.status_code == 403

    async def test_generate_with_section_filter(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/authority-packs/generate",
            json={"include_sections": ["building_identity", "action_plan"]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total_sections"] == 2
        section_types = {s["section_type"] for s in data["sections"]}
        assert section_types == {"building_identity", "action_plan"}
