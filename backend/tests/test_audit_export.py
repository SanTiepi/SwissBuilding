"""Tests for the audit trail export feature."""

import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.audit_log import AuditLog


@pytest.fixture
async def audit_logs_data(db_session, admin_user):
    """Create sample audit log records for testing."""
    now = datetime.now(UTC)
    building_id = uuid.uuid4()
    logs = [
        AuditLog(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            action="create",
            entity_type="building",
            entity_id=building_id,
            details={"address": "Rue Test 1"},
            ip_address="127.0.0.1",
            timestamp=now - timedelta(hours=3),
        ),
        AuditLog(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            action="update",
            entity_type="diagnostic",
            entity_id=uuid.uuid4(),
            details={"status": "completed"},
            ip_address="127.0.0.1",
            timestamp=now - timedelta(hours=2),
        ),
        AuditLog(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            action="delete",
            entity_type="building",
            entity_id=uuid.uuid4(),
            details=None,
            ip_address="127.0.0.1",
            timestamp=now - timedelta(hours=1),
        ),
    ]
    for log in logs:
        db_session.add(log)
    await db_session.commit()
    return {"logs": logs, "building_id": building_id}


class TestAuditExportAPI:
    async def test_export_no_filters_returns_all(self, client, auth_headers, audit_logs_data):
        """Export with no filters returns all audit logs."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "csv", "include_details": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_records"] == 3
        assert data["format"] == "csv"
        assert data["filename"].startswith("audit-export-")
        assert data["filename"].endswith("-all.csv")

    async def test_export_filter_by_building_id(self, client, auth_headers, audit_logs_data):
        """Export filtered by building_id returns only matching logs."""
        building_id = str(audit_logs_data["building_id"])
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {"building_id": building_id}, "format": "csv"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the one log with entity_type=building AND entity_id=building_id
        assert data["total_records"] == 1

    async def test_export_filter_by_date_range(self, client, auth_headers, audit_logs_data):
        """Export filtered by date range works correctly."""
        now = datetime.now(UTC)
        date_from = (now - timedelta(hours=2, minutes=30)).isoformat()
        date_to = (now - timedelta(hours=1, minutes=30)).isoformat()
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={
                "filters": {"date_from": date_from, "date_to": date_to},
                "format": "csv",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the "update" log at -2h falls in this range
        assert data["total_records"] == 1

    async def test_export_filter_by_action_type(self, client, auth_headers, audit_logs_data):
        """Export filtered by action_type works."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {"action_type": "delete"}, "format": "csv"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_records"] == 1

    async def test_csv_format_valid(self, client, auth_headers, audit_logs_data):
        """CSV format generates valid CSV content."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "csv", "include_details": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        content = data["content"]
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 3
        assert "timestamp" in reader.fieldnames
        assert "user_email" in reader.fieldnames
        assert "action_type" in reader.fieldnames
        assert "details" in reader.fieldnames

    async def test_json_format_valid(self, client, auth_headers, audit_logs_data):
        """JSON format generates valid JSON array."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "json", "include_details": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        parsed = json.loads(data["content"])
        assert isinstance(parsed, list)
        assert len(parsed) == 3
        assert "timestamp" in parsed[0]
        assert "user_email" in parsed[0]

    async def test_count_endpoint(self, client, auth_headers, audit_logs_data):
        """Count endpoint returns correct count."""
        resp = await client.post(
            "/api/v1/audit-logs/export/count",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3

    async def test_export_exclude_details(self, client, auth_headers, audit_logs_data):
        """Export with include_details=False excludes details column."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "csv", "include_details": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        content = data["content"]
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 3
        assert "details" not in reader.fieldnames

    async def test_empty_result(self, client, auth_headers, admin_user):
        """Empty result (no matching logs) returns empty export."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {"action_type": "nonexistent"}, "format": "csv"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_records"] == 0
        # CSV should have header row only
        content = data["content"]
        lines = content.strip().split("\n")
        assert len(lines) == 1  # header only

    async def test_filename_format(self, client, auth_headers, audit_logs_data):
        """Filename format is correct."""
        building_id = str(audit_logs_data["building_id"])
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {"building_id": building_id}, "format": "json"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        filename = data["filename"]
        assert filename.startswith("audit-export-")
        assert building_id in filename
        assert filename.endswith(".json")

    async def test_requires_authentication(self, client):
        """API endpoint requires authentication."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "csv"},
        )
        assert resp.status_code in (401, 403)

    async def test_admin_gets_200(self, client, auth_headers, admin_user):
        """API endpoint returns 200 for admin user."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "csv"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_diagnostician_cannot_export(self, client, diag_headers, diagnostician_user):
        """Diagnostician role cannot export audit logs."""
        resp = await client.post(
            "/api/v1/audit-logs/export",
            json={"filters": {}, "format": "csv"},
            headers=diag_headers,
        )
        assert resp.status_code in (401, 403)

    async def test_count_filter_by_resource_type(self, client, auth_headers, audit_logs_data):
        """Count with resource_type filter returns correct count."""
        resp = await client.post(
            "/api/v1/audit-logs/export/count",
            json={"resource_type": "building"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2  # two building-type logs

    async def test_download_endpoint(self, client, auth_headers, audit_logs_data):
        """Download endpoint returns streaming response with correct headers."""
        resp = await client.get(
            "/api/v1/audit-logs/export/download?format=csv",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert "attachment" in resp.headers.get("content-disposition", "")
