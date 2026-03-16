import uuid

import pytest

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.compliance_artefact import ComplianceArtefactCreate
from app.services.compliance_artefact_service import (
    acknowledge_artefact,
    check_required_artefacts,
    create_artefact,
    get_building_compliance_summary,
    reject_artefact,
    submit_artefact,
)


async def _create_building(db, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


class TestCreateArtefact:
    async def test_create_artefact(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        data = ComplianceArtefactCreate(
            artefact_type="suva_notification",
            title="SUVA Notification for asbestos",
            authority_name="SUVA",
            authority_type="federal",
            legal_basis="OTConst Art. 82-86",
        )
        artefact = await create_artefact(db_session, building.id, data, admin_user.id)
        assert artefact.artefact_type == "suva_notification"
        assert artefact.status == "draft"
        assert artefact.title == "SUVA Notification for asbestos"
        assert artefact.building_id == building.id
        assert artefact.created_by == admin_user.id
        assert artefact.authority_name == "SUVA"
        assert artefact.legal_basis == "OTConst Art. 82-86"


class TestSubmitArtefact:
    async def test_submit_artefact(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        data = ComplianceArtefactCreate(
            artefact_type="authority_submission",
            title="Canton submission",
        )
        artefact = await create_artefact(db_session, building.id, data, admin_user.id)
        assert artefact.status == "draft"

        submitted = await submit_artefact(db_session, artefact.id)
        assert submitted.status == "submitted"
        assert submitted.submitted_at is not None


class TestAcknowledgeArtefact:
    async def test_acknowledge_artefact(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        data = ComplianceArtefactCreate(
            artefact_type="authority_submission",
            title="Canton submission",
        )
        artefact = await create_artefact(db_session, building.id, data, admin_user.id)
        await submit_artefact(db_session, artefact.id)

        acknowledged = await acknowledge_artefact(db_session, artefact.id, reference_number="REF-2026-001")
        assert acknowledged.status == "acknowledged"
        assert acknowledged.acknowledged_at is not None
        assert acknowledged.reference_number == "REF-2026-001"


class TestRejectArtefact:
    async def test_reject_artefact(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        data = ComplianceArtefactCreate(
            artefact_type="authority_submission",
            title="Canton submission",
        )
        artefact = await create_artefact(db_session, building.id, data, admin_user.id)
        await submit_artefact(db_session, artefact.id)

        rejected = await reject_artefact(db_session, artefact.id, reason="Missing documentation")
        assert rejected.status == "rejected"


class TestCannotSubmitNonDraft:
    async def test_cannot_submit_non_draft(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        data = ComplianceArtefactCreate(
            artefact_type="authority_submission",
            title="Canton submission",
        )
        artefact = await create_artefact(db_session, building.id, data, admin_user.id)
        await submit_artefact(db_session, artefact.id)

        with pytest.raises(ValueError, match="Cannot submit"):
            await submit_artefact(db_session, artefact.id)


class TestComplianceSummary:
    async def test_compliance_summary(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)

        # Create multiple artefacts
        for atype, astatus in [
            ("suva_notification", "draft"),
            ("suva_notification", "submitted"),
            ("authority_submission", "acknowledged"),
            ("waste_manifest", "draft"),
        ]:
            a = ComplianceArtefact(
                id=uuid.uuid4(),
                building_id=building.id,
                artefact_type=atype,
                status=astatus,
                title=f"Test {atype}",
                created_by=admin_user.id,
            )
            db_session.add(a)
        await db_session.flush()

        summary = await get_building_compliance_summary(db_session, building.id)
        assert summary["total"] == 4
        assert summary["by_type"]["suva_notification"] == 2
        assert summary["by_type"]["authority_submission"] == 1
        assert summary["by_type"]["waste_manifest"] == 1
        assert summary["by_status"]["draft"] == 2
        assert summary["by_status"]["submitted"] == 1
        assert summary["by_status"]["acknowledged"] == 1
        assert summary["pending_submissions"] == 2


class TestCheckRequiredArtefactsAsbestos:
    async def test_check_required_artefacts_asbestos(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)

        # Create diagnostic with positive asbestos sample
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="asbestos",
            status="completed",
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S001",
            pollutant_type="asbestos",
            location_room="Floor 2",
            material_category="insulation",
            threshold_exceeded=True,
        )
        db_session.add(sample)
        await db_session.flush()

        missing = await check_required_artefacts(db_session, building.id)
        assert len(missing) >= 1
        types = [m["artefact_type"] for m in missing]
        assert "suva_notification" in types


class TestCheckRequiredArtefactsIntervention:
    async def test_check_required_artefacts_intervention(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)

        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=building.id,
            intervention_type="removal",
            title="Asbestos removal",
            status="completed",
            created_by=admin_user.id,
        )
        db_session.add(intervention)
        await db_session.flush()

        missing = await check_required_artefacts(db_session, building.id)
        assert len(missing) >= 1
        types = [m["artefact_type"] for m in missing]
        assert "post_remediation_report" in types


class TestCheckRequiredArtefactsAllPresent:
    async def test_check_required_artefacts_all_present(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)

        # Create diagnostic with positive asbestos sample
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="asbestos",
            status="completed",
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S001",
            pollutant_type="asbestos",
            location_room="Floor 2",
            material_category="insulation",
            threshold_exceeded=True,
        )
        db_session.add(sample)

        # Create completed intervention
        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=building.id,
            intervention_type="removal",
            title="Asbestos removal",
            status="completed",
            created_by=admin_user.id,
        )
        db_session.add(intervention)

        # Create the required artefacts
        suva = ComplianceArtefact(
            id=uuid.uuid4(),
            building_id=building.id,
            artefact_type="suva_notification",
            title="SUVA notification",
            status="submitted",
            created_by=admin_user.id,
        )
        db_session.add(suva)

        report = ComplianceArtefact(
            id=uuid.uuid4(),
            building_id=building.id,
            artefact_type="post_remediation_report",
            title="Post-remediation report",
            status="draft",
            created_by=admin_user.id,
        )
        db_session.add(report)
        await db_session.flush()

        missing = await check_required_artefacts(db_session, building.id)
        assert len(missing) == 0


ARTEFACT_PAYLOAD = {
    "artefact_type": "suva_notification",
    "title": "SUVA Notification for asbestos",
    "authority_name": "SUVA",
    "authority_type": "federal",
    "legal_basis": "OTConst Art. 82-86",
}


class TestApiListArtefacts:
    async def test_api_list_artefacts(self, client, admin_user, auth_headers, sample_building):
        # Create an artefact first
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/compliance-artefacts",
            json=ARTEFACT_PAYLOAD,
            headers=auth_headers,
        )
        assert resp.status_code == 201

        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/compliance-artefacts",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["artefact_type"] == "suva_notification"


class TestApiCreateArtefact:
    async def test_api_create_artefact(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/compliance-artefacts",
            json=ARTEFACT_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["artefact_type"] == "suva_notification"
        assert data["status"] == "draft"
        assert data["title"] == "SUVA Notification for asbestos"
        assert data["authority_name"] == "SUVA"


class TestApiSubmitArtefact:
    async def test_api_submit_artefact(self, client, admin_user, auth_headers, sample_building):
        # Create
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/compliance-artefacts",
            json=ARTEFACT_PAYLOAD,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        artefact_id = resp.json()["id"]

        # Submit
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/compliance-artefacts/{artefact_id}/submit",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None
