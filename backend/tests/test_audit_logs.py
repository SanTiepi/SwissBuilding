import uuid

from app.models.audit_log import AuditLog


class TestAuditLogsAPI:
    async def test_list_audit_logs_admin(self, client, auth_headers, db_session, admin_user):
        """Admin can list audit logs."""
        log = AuditLog(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            action="create",
            entity_type="building",
            entity_id=uuid.uuid4(),
            details={"key": "value"},
            ip_address="127.0.0.1",
        )
        db_session.add(log)
        await db_session.commit()

        resp = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["action"] == "create"
        assert item["entity_type"] == "building"
        assert item["user_email"] == admin_user.email
        assert item["user_name"] == f"{admin_user.first_name} {admin_user.last_name}"

    async def test_list_audit_logs_pagination(self, client, auth_headers, db_session, admin_user):
        """Pagination works correctly."""
        for i in range(5):
            db_session.add(
                AuditLog(
                    id=uuid.uuid4(),
                    user_id=admin_user.id,
                    action=f"action_{i}",
                    entity_type="building",
                )
            )
        await db_session.commit()

        resp = await client.get("/api/v1/audit-logs?page=1&size=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_filter_by_entity_type(self, client, auth_headers, db_session, admin_user):
        """Filter by entity_type works."""
        db_session.add(AuditLog(id=uuid.uuid4(), action="create", entity_type="building"))
        db_session.add(AuditLog(id=uuid.uuid4(), action="update", entity_type="diagnostic"))
        await db_session.commit()

        resp = await client.get("/api/v1/audit-logs?entity_type=building", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "building"

    async def test_filter_by_action(self, client, auth_headers, db_session, admin_user):
        """Filter by action works."""
        db_session.add(AuditLog(id=uuid.uuid4(), action="create", entity_type="building"))
        db_session.add(AuditLog(id=uuid.uuid4(), action="delete", entity_type="building"))
        await db_session.commit()

        resp = await client.get("/api/v1/audit-logs?action=delete", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "delete"

    async def test_filter_by_user_id(self, client, auth_headers, db_session, admin_user):
        """Filter by user_id works."""
        other_id = uuid.uuid4()
        db_session.add(AuditLog(id=uuid.uuid4(), user_id=admin_user.id, action="create", entity_type="building"))
        db_session.add(AuditLog(id=uuid.uuid4(), user_id=other_id, action="update", entity_type="building"))
        await db_session.commit()

        resp = await client.get(f"/api/v1/audit-logs?user_id={admin_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == str(admin_user.id)

    async def test_diagnostician_cannot_access(self, client, diag_headers, diagnostician_user):
        """Diagnostician role cannot access audit logs."""
        resp = await client.get("/api/v1/audit-logs", headers=diag_headers)
        assert resp.status_code in (401, 403)

    async def test_owner_cannot_access(self, client, owner_headers, owner_user):
        """Owner role cannot access audit logs."""
        resp = await client.get("/api/v1/audit-logs", headers=owner_headers)
        assert resp.status_code in (401, 403)

    async def test_unauthenticated_cannot_access(self, client):
        """Unauthenticated request gets 401/403."""
        resp = await client.get("/api/v1/audit-logs")
        assert resp.status_code in (401, 403)

    async def test_empty_list(self, client, auth_headers, admin_user):
        """Returns empty list when no audit logs exist."""
        resp = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pages"] == 0

    async def test_null_user_id_log(self, client, auth_headers, db_session, admin_user):
        """Logs with null user_id (system actions) work correctly."""
        db_session.add(
            AuditLog(
                id=uuid.uuid4(),
                user_id=None,
                action="system_cleanup",
                entity_type="system",
            )
        )
        await db_session.commit()

        resp = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["user_id"] is None
        assert item["user_email"] is None
        assert item["user_name"] is None
