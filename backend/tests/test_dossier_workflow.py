"""Tests for the Safe-to-Start Dossier Workflow service.

End-to-end integration tests proving the FULL lifecycle:
  assess -> fix gaps -> generate pack -> submit -> complement -> resubmit -> acknowledged
"""

import json
import os
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_pack import EvidencePack
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.authority_pack import AuthorityPackConfig
from app.services.authority_pack_service import generate_pack_artifact
from app.services.dossier_workflow_service import DossierWorkflowService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_service = DossierWorkflowService()


def _make_org(db_session) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Property Management",
        type="property_management",
    )
    db_session.add(org)
    return org


def _make_building(db_session, admin_user, *, construction_year=1965, org=None, **kwargs):
    building = Building(
        id=uuid.uuid4(),
        address="Rue de Bourg 42",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        organization_id=org.id if org else None,
        **kwargs,
    )
    db_session.add(building)
    return building


def _make_diagnostic(db_session, building, *, status="completed", context="AvT", **kwargs):
    defaults = {
        "date_inspection": date(2024, 1, 15),
    }
    defaults.update(kwargs)
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        diagnostic_context=context,
        status=status,
        **defaults,
    )
    db_session.add(diag)
    return diag


def _make_sample(
    db_session,
    diag,
    *,
    pollutant_type="asbestos",
    concentration=5.0,
    unit="percent_weight",
    **kwargs,
):
    defaults = {
        "risk_level": "high",
        "threshold_exceeded": True,
        "cfst_work_category": "medium",
        "action_required": "remove_planned",
        "waste_disposal_type": "type_e",
    }
    defaults.update(kwargs)
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
        **defaults,
    )
    db_session.add(sample)
    return sample


def _make_document(db_session, building, *, document_type="diagnostic_report", **kwargs):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path=f"/docs/{uuid.uuid4().hex}.pdf",
        file_name="report.pdf",
        document_type=document_type,
        **kwargs,
    )
    db_session.add(doc)
    return doc


def _make_action(db_session, building, *, priority="medium", status="open", **kwargs):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Test action",
        priority=priority,
        status=status,
        **kwargs,
    )
    db_session.add(action)
    return action


def _make_zone(db_session, building, *, zone_type="floor", name="Ground floor", **kwargs):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type=zone_type,
        name=name,
        **kwargs,
    )
    db_session.add(zone)
    return zone


async def _create_ready_building(db_session, admin_user):
    """Create a building with all data needed for safe_to_start: ready."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)
    diag = _make_diagnostic(
        db_session,
        building,
        suva_notification_required=True,
        suva_notification_date=date(2024, 2, 1),
    )
    # All 6 pollutants
    _make_sample(db_session, diag, pollutant_type="asbestos")
    _make_sample(
        db_session,
        diag,
        pollutant_type="pcb",
        concentration=100.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="lead",
        concentration=200.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="hap",
        concentration=10.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="radon",
        concentration=100.0,
        unit="Bq_per_m3",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="pfas",
        concentration=0.5,
        unit="ug_per_l",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_document(db_session, building, document_type="diagnostic_report")
    await db_session.commit()
    return building, org


async def _create_not_ready_building(db_session, admin_user):
    """Create a building that is NOT ready (missing pollutants, no SUVA)."""
    org = _make_org(db_session)
    building = _make_building(db_session, admin_user, org=org)
    # Completed diagnostic but missing several pollutants
    diag = _make_diagnostic(db_session, building)
    _make_sample(db_session, diag, pollutant_type="asbestos")
    # Only asbestos -- missing pcb, lead, hap, radon, pfas
    # No SUVA notification (positive asbestos but no SUVA)
    await db_session.commit()
    return building, org


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDossierWorkflowLifecycle:
    """End-to-end dossier workflow tests."""

    @pytest.mark.asyncio
    async def test_initial_status_not_assessed(self, db_session, admin_user):
        """New building with no data has 'not_assessed' lifecycle stage."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        status = await _service.get_dossier_status(db_session, building.id)

        assert status["lifecycle_stage"] in ("not_assessed", "not_ready")
        assert status["building_id"] == str(building.id)
        assert status["work_type"] == "asbestos_removal"

    @pytest.mark.asyncio
    async def test_status_shows_readiness_and_completeness(self, db_session, admin_user):
        """Status includes readiness verdict, completeness, unknowns, actions."""
        building, _org = await _create_not_ready_building(db_session, admin_user)

        status = await _service.get_dossier_status(db_session, building.id)

        # Readiness section
        assert "readiness" in status
        assert "verdict" in status["readiness"]
        assert "blockers" in status["readiness"]

        # Completeness section
        assert "completeness" in status
        assert "score_pct" in status["completeness"]

        # Unknowns section
        assert "unknowns" in status
        assert "count" in status["unknowns"]

        # Actions section
        assert "actions" in status
        assert "total_open" in status["actions"]

    @pytest.mark.asyncio
    async def test_status_shows_progress_steps(self, db_session, admin_user):
        """Progress shows 6 lifecycle steps with correct statuses."""
        building, _org = await _create_not_ready_building(db_session, admin_user)

        status = await _service.get_dossier_status(db_session, building.id)

        progress = status["progress"]
        assert progress["steps_total"] == 6
        assert len(progress["steps"]) == 6
        # All steps should have name and status
        for step in progress["steps"]:
            assert "name" in step
            assert "status" in step
            assert step["status"] in ("done", "in_progress", "pending")

    @pytest.mark.asyncio
    async def test_status_next_action_when_not_ready(self, db_session, admin_user):
        """Next action is 'fix_blocker' when readiness is not ready."""
        building, _org = await _create_not_ready_building(db_session, admin_user)

        status = await _service.get_dossier_status(db_session, building.id)

        next_action = status["next_action"]
        assert next_action["action_type"] == "fix_blocker"
        assert "title" in next_action
        assert "description" in next_action

    @pytest.mark.asyncio
    async def test_status_next_action_when_ready(self, db_session, admin_user):
        """Next action is 'generate_pack' when building is ready."""
        building, _org = await _create_ready_building(db_session, admin_user)

        status = await _service.get_dossier_status(db_session, building.id)

        # Building should be ready or conditionally ready
        assert status["lifecycle_stage"] in ("ready", "partially_ready")
        if status["lifecycle_stage"] == "ready":
            assert status["next_action"]["action_type"] == "generate_pack"

    @pytest.mark.asyncio
    async def test_generate_pack_when_ready(self, db_session, admin_user):
        """Can generate pack when readiness allows it."""
        building, org = await _create_ready_building(db_session, admin_user)

        result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )

        assert "pack_id" in result
        assert result["overall_completeness"] > 0
        assert result["total_sections"] > 0
        assert "sha256_hash" in result

    @pytest.mark.asyncio
    async def test_generate_pack_blocked_when_not_ready(self, db_session, admin_user):
        """Cannot generate pack when completeness too low."""
        building, org = await _create_not_ready_building(db_session, admin_user)

        with pytest.raises(ValueError, match="pas pret"):
            await _service.generate_dossier_pack(db_session, building.id, "asbestos_removal", admin_user.id, org.id)

    @pytest.mark.asyncio
    async def test_submit_updates_lifecycle(self, db_session, admin_user):
        """Submitting moves lifecycle to 'submitted'."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Generate pack first
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])

        # Submit
        status = await _service.submit_to_authority(db_session, building.id, pack_id, admin_user.id, org.id)

        assert status["lifecycle_stage"] == "submitted"
        assert status["pack"]["status"] == "submitted"
        assert status["pack"]["submitted_at"] is not None

    @pytest.mark.asyncio
    async def test_complement_reopens_blockers(self, db_session, admin_user):
        """Complement request creates new actions and updates pack."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Generate + submit
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])
        await _service.submit_to_authority(db_session, building.id, pack_id, admin_user.id, org.id)

        # Handle complement
        status = await _service.handle_complement_request(
            db_session,
            building.id,
            pack_id,
            "Manque le plan de gestion des dechets et la notification SUVA actualisee.",
            admin_user.id,
        )

        assert status["lifecycle_stage"] == "complement_requested"
        assert status["pack"]["status"] == "complement_requested"
        # Should have created at least one new action
        assert status["actions"]["total_open"] >= 1

    @pytest.mark.asyncio
    async def test_resubmit_after_complement(self, db_session, admin_user):
        """After fixing complement issues, can regenerate and resubmit."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Generate + submit
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])
        await _service.submit_to_authority(db_session, building.id, pack_id, admin_user.id, org.id)

        # Handle complement
        await _service.handle_complement_request(
            db_session,
            building.id,
            pack_id,
            "Manque le plan de gestion des dechets.",
            admin_user.id,
        )

        # Resubmit
        resubmit_result = await _service.resubmit_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )

        assert "pack_id" in resubmit_result
        # New pack should be different from old pack
        assert resubmit_result["pack_id"] != str(pack_id)
        # Status should be submitted after resubmit
        assert resubmit_result["status"]["lifecycle_stage"] == "submitted"

    @pytest.mark.asyncio
    async def test_acknowledge_completes_lifecycle(self, db_session, admin_user):
        """Acknowledge marks dossier as authority-ready."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Generate + submit
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])
        await _service.submit_to_authority(db_session, building.id, pack_id, admin_user.id, org.id)

        # Acknowledge
        status = await _service.acknowledge_receipt(db_session, building.id, pack_id, admin_user.id, org.id)

        assert status["lifecycle_stage"] == "acknowledged"
        assert status["pack"]["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_full_lifecycle_happy_path(self, db_session, admin_user):
        """Complete lifecycle: assess -> generate -> submit -> acknowledge."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Step 1: Assess
        status = await _service.get_dossier_status(db_session, building.id)
        assert status["lifecycle_stage"] in ("ready", "partially_ready")

        # Step 2: Generate pack
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])
        status = await _service.get_dossier_status(db_session, building.id)
        assert status["lifecycle_stage"] == "pack_generated"

        # Step 3: Submit
        status = await _service.submit_to_authority(db_session, building.id, pack_id, admin_user.id, org.id)
        assert status["lifecycle_stage"] == "submitted"

        # Step 4: Acknowledge
        status = await _service.acknowledge_receipt(db_session, building.id, pack_id, admin_user.id, org.id)
        assert status["lifecycle_stage"] == "acknowledged"

        # Final check: next action should be 'wait'
        assert status["next_action"]["action_type"] == "wait"

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_complement(self, db_session, admin_user):
        """Lifecycle with complement: assess -> generate -> submit -> complement -> fix -> resubmit -> acknowledge."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Step 1: Generate pack
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])

        # Step 2: Submit
        await _service.submit_to_authority(db_session, building.id, pack_id, admin_user.id, org.id)

        # Step 3: Complement request
        status = await _service.handle_complement_request(
            db_session,
            building.id,
            pack_id,
            "Diagnostic rapport incomplet",
            admin_user.id,
        )
        assert status["lifecycle_stage"] == "complement_requested"
        assert status["next_action"]["action_type"] == "fix_complement"

        # Step 4: Resubmit
        resubmit_result = await _service.resubmit_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        new_pack_id = uuid.UUID(resubmit_result["pack_id"])
        assert resubmit_result["status"]["lifecycle_stage"] == "submitted"

        # Step 5: Acknowledge
        status = await _service.acknowledge_receipt(db_session, building.id, new_pack_id, admin_user.id, org.id)
        assert status["lifecycle_stage"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_fix_blocker_re_evaluates(self, db_session, admin_user):
        """fix_blocker re-evaluates readiness and returns updated status."""
        building, _org = await _create_not_ready_building(db_session, admin_user)

        status = await _service.fix_blocker(
            db_session,
            building.id,
            "missing_pollutant",
            {"pollutant": "pcb"},
            admin_user.id,
        )

        # Should return a valid status dict
        assert "lifecycle_stage" in status
        assert "readiness" in status
        assert "progress" in status

    @pytest.mark.asyncio
    async def test_pack_not_found_raises(self, db_session, admin_user):
        """Submitting with an invalid pack_id raises ValueError."""
        building, _org = await _create_ready_building(db_session, admin_user)

        fake_pack_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await _service.submit_to_authority(db_session, building.id, fake_pack_id, admin_user.id)

    @pytest.mark.asyncio
    async def test_acknowledge_unsubmitted_pack_raises(self, db_session, admin_user):
        """Cannot acknowledge a pack that hasn't been submitted."""
        building, org = await _create_ready_building(db_session, admin_user)

        # Generate but don't submit
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        pack_id = uuid.UUID(pack_result["pack_id"])

        with pytest.raises(ValueError, match="not been submitted"):
            await _service.acknowledge_receipt(db_session, building.id, pack_id, admin_user.id)

    @pytest.mark.asyncio
    async def test_building_not_found_raises(self, db_session, admin_user):
        """Operations on non-existent building raise ValueError."""
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await _service.get_dossier_status(db_session, fake_id)

    @pytest.mark.asyncio
    async def test_complement_creates_invalidation_and_actions(self, db_session, admin_user):
        """Proving the complement loop: submit -> complement -> invalidation + new actions -> resubmit.

        This test verifies the full invalidation chain:
        1. Generate pack and submit to authority
        2. Authority requests complement (complement_requested)
        3. Old pack is marked with complement details in notes
        4. New action is created for the complement request
        5. Readiness is re-evaluated
        6. Resubmit generates a new pack that supersedes the old one
        7. Old pack is marked as expired
        8. New pack is submitted and has a different ID
        """
        building, org = await _create_ready_building(db_session, admin_user)

        # 1. Generate pack
        pack_result = await _service.generate_dossier_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )
        original_pack_id = uuid.UUID(pack_result["pack_id"])
        original_hash = pack_result["sha256_hash"]
        assert original_hash is not None

        # 2. Submit
        status = await _service.submit_to_authority(db_session, building.id, original_pack_id, admin_user.id, org.id)
        assert status["lifecycle_stage"] == "submitted"

        # Count open actions before complement
        actions_before = status["actions"]["total_open"]

        # 3. Handle complement request
        complement_text = "Manque le plan de gestion des dechets et la notification SUVA actualisee."
        status = await _service.handle_complement_request(
            db_session,
            building.id,
            original_pack_id,
            complement_text,
            admin_user.id,
        )

        # 4. Verify complement effects
        assert status["lifecycle_stage"] == "complement_requested"
        assert status["pack"]["status"] == "complement_requested"

        # Verify new actions were created (more than before)
        assert status["actions"]["total_open"] > actions_before

        # Verify the pack notes contain complement details
        result = await db_session.execute(select(EvidencePack).where(EvidencePack.id == original_pack_id))
        old_pack = result.scalar_one()
        notes_data = json.loads(old_pack.notes)
        assert notes_data["complement_requested"] is True
        assert complement_text in notes_data["complement_details"]

        # Verify complement action exists in DB
        action_result = await db_session.execute(
            select(ActionItem).where(
                ActionItem.building_id == building.id,
                ActionItem.source_type == "dossier_workflow",
            )
        )
        complement_actions = action_result.scalars().all()
        assert len(complement_actions) >= 1
        assert any("Complement" in (a.title or "") for a in complement_actions)

        # 5. Resubmit (generates new pack, supersedes old)
        resubmit_result = await _service.resubmit_pack(
            db_session, building.id, "asbestos_removal", admin_user.id, org.id
        )

        new_pack_id = uuid.UUID(resubmit_result["pack_id"])
        assert new_pack_id != original_pack_id

        # 6. Verify old pack is expired (superseded)
        await db_session.refresh(old_pack)
        assert old_pack.status == "expired"

        # 7. Verify new pack is submitted
        result = await db_session.execute(select(EvidencePack).where(EvidencePack.id == new_pack_id))
        new_pack = result.scalar_one()
        assert new_pack.status == "submitted"
        assert new_pack.submitted_at is not None

        # 8. New pack has different hash (different content/timestamp)
        assert resubmit_result["sha256_hash"] is not None
        assert resubmit_result["sha256_hash"] != original_hash

        # 9. Final lifecycle should be submitted
        assert resubmit_result["status"]["lifecycle_stage"] == "submitted"


class TestAuthorityPackArtifact:
    """Tests for the authority pack artifact file generation."""

    @pytest.mark.asyncio
    async def test_generate_pack_artifact_writes_file(self, db_session, admin_user, tmp_path):
        """generate_pack_artifact writes a real JSON file to disk."""
        building, _org = await _create_ready_building(db_session, admin_user)

        config = AuthorityPackConfig(building_id=building.id, language="fr")
        output_dir = str(tmp_path / "artifacts")

        result = await generate_pack_artifact(db_session, building.id, config, admin_user.id, output_dir=output_dir)

        # Verify the file was written
        assert os.path.isfile(result.artifact_path)
        assert result.artifact_path.startswith(output_dir)
        assert result.artifact_path.endswith(".json")

        # Verify the file content is valid JSON and contains sections
        with open(result.artifact_path, encoding="utf-8") as f:
            content = f.read()
        pack_from_file = json.loads(content)
        assert "sections" in pack_from_file
        assert len(pack_from_file["sections"]) > 0

        # Verify SHA-256 hash matches file content
        import hashlib

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result.sha256 == expected_hash

        # Verify metadata
        assert result.metadata.building_id == str(building.id)
        assert result.metadata.generated_by == str(admin_user.id)
        assert result.metadata.version == "2.0.0"
        assert result.metadata.financials_redacted is False

        # Verify pack_data is populated
        assert result.pack_data.pack_id is not None
        assert result.pack_data.building_id == building.id
        assert result.pack_data.total_sections > 0

    @pytest.mark.asyncio
    async def test_artifact_with_redaction(self, db_session, admin_user, tmp_path):
        """Artifact with redact_financials=True produces redacted output."""
        building, _org = await _create_ready_building(db_session, admin_user)

        config = AuthorityPackConfig(
            building_id=building.id,
            language="fr",
            redact_financials=True,
        )
        output_dir = str(tmp_path / "artifacts-redacted")

        result = await generate_pack_artifact(db_session, building.id, config, admin_user.id, output_dir=output_dir)

        assert result.metadata.financials_redacted is True
        assert result.pack_data.financials_redacted is True
        assert os.path.isfile(result.artifact_path)

    @pytest.mark.asyncio
    async def test_artifact_filename_contains_building_id(self, db_session, admin_user, tmp_path):
        """Artifact filename embeds building ID for traceability."""
        building, _org = await _create_ready_building(db_session, admin_user)

        config = AuthorityPackConfig(building_id=building.id, language="fr")
        output_dir = str(tmp_path / "artifacts-named")

        result = await generate_pack_artifact(db_session, building.id, config, admin_user.id, output_dir=output_dir)

        filename = os.path.basename(result.artifact_path)
        assert str(building.id) in filename
        assert filename.startswith("authority-pack-")

    @pytest.mark.asyncio
    async def test_artifact_nonexistent_building_raises(self, db_session, admin_user, tmp_path):
        """Generating artifact for non-existent building raises ValueError."""
        fake_id = uuid.uuid4()
        config = AuthorityPackConfig(building_id=fake_id, language="fr")

        with pytest.raises(ValueError, match="not found"):
            await generate_pack_artifact(db_session, fake_id, config, admin_user.id, output_dir=str(tmp_path))
