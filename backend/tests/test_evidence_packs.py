import uuid

from app.api.evidence_packs import router as evidence_packs_router
from app.main import app

app.include_router(evidence_packs_router, prefix="/api/v1")

PACK_PAYLOAD = {
    "pack_type": "authority_pack",
    "title": "Dossier autorisation VD - Amiante",
    "description": "Pack pour soumission DFIRE canton de Vaud",
    "status": "draft",
}


class TestCreateEvidencePack:
    async def test_create_pack_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["pack_type"] == "authority_pack"
        assert data["title"] == "Dossier autorisation VD - Amiante"
        assert data["building_id"] == str(sample_building.id)
        assert data["status"] == "draft"

    async def test_create_pack_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_create_pack_with_all_optional_fields(self, client, admin_user, auth_headers, sample_building):
        full_payload = {
            **PACK_PAYLOAD,
            "required_sections_json": [{"section_type": "diagnostic", "label": "Diagnostic amiante", "required": True}],
            "included_artefacts_json": [{"artefact_type": "waste_manifest", "artefact_id": str(uuid.uuid4())}],
            "included_documents_json": [{"document_id": str(uuid.uuid4()), "document_type": "lab_report"}],
            "recipient_name": "DFIRE Vaud",
            "recipient_type": "authority",
            "notes": "Urgent submission",
        }
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=full_payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["recipient_name"] == "DFIRE Vaud"
        assert data["recipient_type"] == "authority"
        assert len(data["required_sections_json"]) == 1
        assert data["notes"] == "Urgent submission"


class TestListEvidencePacks:
    async def test_list_empty(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_packs(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json={**PACK_PAYLOAD, "pack_type": "contractor_pack", "title": "Handoff Pack"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_filtered_by_pack_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json={**PACK_PAYLOAD, "pack_type": "contractor_pack", "title": "Contractor Handoff"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            params={"pack_type": "contractor_pack"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["pack_type"] == "contractor_pack"

    async def test_list_filtered_by_status(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json={**PACK_PAYLOAD, "status": "complete", "title": "Complete Pack"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            params={"status": "complete"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "complete"


class TestGetEvidencePack:
    async def test_get_pack(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        pack_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs/{pack_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == pack_id

    async def test_get_pack_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateEvidencePack:
    async def test_update_pack(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        pack_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs/{pack_id}",
            json={"status": "complete", "recipient_name": "Service Environnement VD"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["recipient_name"] == "Service Environnement VD"
        assert data["title"] == "Dossier autorisation VD - Amiante"


class TestDeleteEvidencePack:
    async def test_delete_pack(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs",
            json=PACK_PAYLOAD,
            headers=auth_headers,
        )
        pack_id = create_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs/{pack_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/evidence-packs/{pack_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
