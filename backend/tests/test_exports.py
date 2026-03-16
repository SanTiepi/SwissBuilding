import uuid

from app.models.export_job import ExportJob


class TestListExports:
    async def test_list_exports_empty(self, client, admin_user, auth_headers):
        response = await client.get("/api/v1/exports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_exports_with_items(self, client, admin_user, auth_headers, db_session):
        job = ExportJob(
            id=uuid.uuid4(),
            type="building_dossier",
            status="queued",
            requested_by=admin_user.id,
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.get("/api/v1/exports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["type"] == "building_dossier"

    async def test_list_exports_status_filter(self, client, admin_user, auth_headers, db_session):
        for status in ("queued", "completed"):
            db_session.add(
                ExportJob(
                    id=uuid.uuid4(),
                    type="building_dossier",
                    status=status,
                    requested_by=admin_user.id,
                )
            )
        await db_session.commit()

        response = await client.get("/api/v1/exports?status=completed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    async def test_list_exports_own_only_for_non_admin(
        self, client, admin_user, diagnostician_user, diag_headers, db_session
    ):
        # Create export for admin
        db_session.add(
            ExportJob(
                id=uuid.uuid4(),
                type="building_dossier",
                status="queued",
                requested_by=admin_user.id,
            )
        )
        # Create export for diagnostician
        db_session.add(
            ExportJob(
                id=uuid.uuid4(),
                type="audit_pack",
                status="queued",
                requested_by=diagnostician_user.id,
            )
        )
        await db_session.commit()

        response = await client.get("/api/v1/exports", headers=diag_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["type"] == "audit_pack"


class TestCreateExport:
    async def test_create_export(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/exports",
            headers=auth_headers,
            json={"type": "building_dossier"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "building_dossier"
        assert data["status"] == "queued"
        assert data["requested_by"] == str(admin_user.id)

    async def test_create_export_unauthenticated(self, client):
        response = await client.post(
            "/api/v1/exports",
            json={"type": "building_dossier"},
        )
        assert response.status_code in (401, 403)


class TestGetExport:
    async def test_get_export(self, client, admin_user, auth_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            ExportJob(
                id=job_id,
                type="handoff_pack",
                status="completed",
                requested_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.get(f"/api/v1/exports/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["type"] == "handoff_pack"

    async def test_get_export_not_found(self, client, admin_user, auth_headers):
        response = await client.get(f"/api/v1/exports/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404

    async def test_get_export_other_user_denied(self, client, admin_user, diagnostician_user, diag_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            ExportJob(
                id=job_id,
                type="building_dossier",
                status="queued",
                requested_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.get(f"/api/v1/exports/{job_id}", headers=diag_headers)
        assert response.status_code == 403


class TestCancelExport:
    async def test_cancel_queued_export(self, client, admin_user, auth_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            ExportJob(
                id=job_id,
                type="building_dossier",
                status="queued",
                requested_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.delete(f"/api/v1/exports/{job_id}", headers=auth_headers)
        assert response.status_code == 204

    async def test_cancel_non_queued_export_rejected(self, client, admin_user, auth_headers, db_session):
        job_id = uuid.uuid4()
        db_session.add(
            ExportJob(
                id=job_id,
                type="building_dossier",
                status="processing",
                requested_by=admin_user.id,
            )
        )
        await db_session.commit()

        response = await client.delete(f"/api/v1/exports/{job_id}", headers=auth_headers)
        assert response.status_code == 400

    async def test_cancel_export_non_admin_denied(
        self, client, admin_user, diagnostician_user, diag_headers, db_session
    ):
        job_id = uuid.uuid4()
        db_session.add(
            ExportJob(
                id=job_id,
                type="building_dossier",
                status="queued",
                requested_by=diagnostician_user.id,
            )
        )
        await db_session.commit()

        response = await client.delete(f"/api/v1/exports/{job_id}", headers=diag_headers)
        assert response.status_code == 403
