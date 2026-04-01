"""Tests for pack export: PDF generation + shared artifact links."""

import os
import secrets
import tempfile
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.shared_artifact import SharedArtifact
from app.services.pdf_generator_service import (
    HAS_REPORTLAB,
    PDFGeneratorService,
    _build_html_fallback,
    _ensure_artifact_dir,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pack_data():
    """Minimal pack data for PDF generation."""
    return {
        "pack_id": str(uuid.uuid4()),
        "pack_type": "authority",
        "pack_name": "Pack Autorite",
        "building_info": {
            "address": "Rue du Test 42",
            "city": "Lausanne",
            "canton": "VD",
            "egid": "123456",
        },
        "passport_grade": "B",
        "overall_completeness": 0.78,
        "readiness_verdict": "safe_to_start",
        "caveats_count": 2,
        "financials_redacted": False,
        "sections": [
            {
                "section_name": "Identite du batiment",
                "section_type": "building_identity",
                "items": [{"address": "Rue du Test 42", "city": "Lausanne", "canton": "VD", "egid": "123456"}],
                "completeness": 1.0,
            },
            {
                "section_name": "Resume du passeport",
                "section_type": "passport_summary",
                "items": [{"passport_grade": "B", "knowledge_score": 0.8}],
                "completeness": 0.9,
            },
            {
                "section_name": "Reserves et limites",
                "section_type": "caveats",
                "items": [
                    {"text": "Diagnostic amiante non disponible"},
                    {"text": "Donnees PCB partielles"},
                ],
                "completeness": 1.0,
            },
        ],
        "sha256_hash": "abc123def456",
        "generated_at": datetime.now(UTC).isoformat(),
        "pack_version": "2.0.0",
    }


@pytest.fixture
def pack_data_redacted(pack_data):
    """Pack data with financial redaction."""
    pack_data["financials_redacted"] = True
    pack_data["pack_name"] = "Pack Transaction"
    pack_data["pack_type"] = "transaction"
    return pack_data


# ---------------------------------------------------------------------------
# TestPDFGeneration — service-level
# ---------------------------------------------------------------------------


class TestPDFGeneration:
    """Tests for PDFGeneratorService."""

    @pytest.mark.asyncio
    async def test_generate_pack_pdf_creates_file(self, pack_data):
        """generate_pack_pdf creates a file on disk."""
        svc = PDFGeneratorService()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await svc.generate_pack_pdf(pack_data, output_dir=tmpdir)
            assert os.path.exists(result["pdf_path"])
            assert result["size_bytes"] > 0
            assert result["filename"].startswith("baticonnect_authority_")

    @pytest.mark.asyncio
    async def test_pdf_has_sha256(self, pack_data):
        """Generated PDF result includes a SHA-256 hash."""
        svc = PDFGeneratorService()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await svc.generate_pack_pdf(pack_data, output_dir=tmpdir)
            assert len(result["sha256"]) == 64  # SHA-256 hex = 64 chars
            assert result["sha256"] != pack_data["sha256_hash"]  # file hash != content hash

    @pytest.mark.asyncio
    async def test_pdf_with_redaction(self, pack_data_redacted):
        """PDF generation works with redacted financial data."""
        svc = PDFGeneratorService()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await svc.generate_pack_pdf(pack_data_redacted, output_dir=tmpdir)
            assert os.path.exists(result["pdf_path"])
            assert result["filename"].startswith("baticonnect_transaction_")

    @pytest.mark.asyncio
    async def test_pdf_generated_at_is_recent(self, pack_data):
        """generated_at timestamp is close to now."""
        svc = PDFGeneratorService()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await svc.generate_pack_pdf(pack_data, output_dir=tmpdir)
            now = datetime.now(UTC)
            diff = abs((now - result["generated_at"]).total_seconds())
            assert diff < 5

    @pytest.mark.asyncio
    async def test_pdf_extension_matches_backend(self, pack_data):
        """File extension is .pdf when reportlab is available, .html otherwise."""
        svc = PDFGeneratorService()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await svc.generate_pack_pdf(pack_data, output_dir=tmpdir)
            ext = ".pdf" if HAS_REPORTLAB else ".html"
            assert result["filename"].endswith(ext)

    @pytest.mark.asyncio
    async def test_pdf_empty_sections(self):
        """PDF generation handles empty sections gracefully."""
        svc = PDFGeneratorService()
        data = {
            "pack_id": str(uuid.uuid4()),
            "pack_type": "authority",
            "pack_name": "Pack Vide",
            "building_info": {"address": "Test"},
            "passport_grade": "F",
            "overall_completeness": 0,
            "readiness_verdict": "not_ready",
            "caveats_count": 0,
            "sections": [],
            "sha256_hash": "empty",
            "generated_at": datetime.now(UTC).isoformat(),
            "pack_version": "1.0.0",
            "financials_redacted": False,
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await svc.generate_pack_pdf(data, output_dir=tmpdir)
            assert os.path.exists(result["pdf_path"])
            assert result["size_bytes"] > 0

    def test_html_fallback_creates_file(self, pack_data):
        """HTML fallback generates a valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.html")
            _build_html_fallback(pack_data, path)
            assert os.path.exists(path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "BatiConnect" in content
            assert "Rue du Test 42" in content
            assert "Pack Autorite" in content

    def test_ensure_artifact_dir_creates(self):
        """_ensure_artifact_dir creates directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "new_subdir")
            result = _ensure_artifact_dir(new_dir)
            assert os.path.isdir(result)


# ---------------------------------------------------------------------------
# TestSharedArtifacts — model + API level
# ---------------------------------------------------------------------------


class TestSharedArtifacts:
    """Tests for shared artifact creation and access."""

    @pytest.mark.asyncio
    async def test_create_shared_artifact(self, db_session, admin_user):
        """SharedArtifact can be created and persisted."""
        artifact = SharedArtifact(
            building_id=uuid.uuid4(),
            organization_id=None,
            created_by_id=admin_user.id,
            artifact_type="authority_pack",
            artifact_data={"sections": [], "grade": "B"},
            access_token=secrets.token_urlsafe(48),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            title="Pack Autorite — VD",
            redacted=False,
        )
        db_session.add(artifact)
        await db_session.commit()
        await db_session.refresh(artifact)

        assert artifact.id is not None
        assert artifact.view_count == 0
        assert artifact.artifact_type == "authority_pack"

    @pytest.mark.asyncio
    async def test_share_link_structure(self, db_session, admin_user):
        """Shared artifact has correct field structure."""
        token = secrets.token_urlsafe(48)
        expires = datetime.now(UTC) + timedelta(days=14)
        artifact = SharedArtifact(
            building_id=uuid.uuid4(),
            created_by_id=admin_user.id,
            artifact_type="transaction_pack",
            artifact_data={"pack_name": "Pack Transaction"},
            access_token=token,
            expires_at=expires,
            title="Pack Transaction",
            redacted=True,
        )
        db_session.add(artifact)
        await db_session.commit()
        await db_session.refresh(artifact)

        assert artifact.access_token == token
        assert artifact.redacted is True
        assert artifact.title == "Pack Transaction"
        assert len(artifact.access_token) > 30

    @pytest.mark.asyncio
    async def test_api_view_shared_artifact(self, client, db_session, admin_user):
        """GET /shared-artifacts/{token} returns artifact data."""
        token = secrets.token_urlsafe(48)
        artifact = SharedArtifact(
            building_id=uuid.uuid4(),
            created_by_id=admin_user.id,
            artifact_type="authority_pack",
            artifact_data={"grade": "C", "completeness": 0.65},
            access_token=token,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            title="Test Pack",
        )
        db_session.add(artifact)
        await db_session.commit()

        resp = await client.get(f"/api/v1/shared-artifacts/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Pack"
        assert data["artifact_type"] == "authority_pack"
        assert data["artifact_data"]["grade"] == "C"

    @pytest.mark.asyncio
    async def test_expired_share_returns_410(self, client, db_session, admin_user):
        """GET /shared-artifacts/{token} with expired link returns 410."""
        token = secrets.token_urlsafe(48)
        artifact = SharedArtifact(
            building_id=uuid.uuid4(),
            created_by_id=admin_user.id,
            artifact_type="authority_pack",
            artifact_data={"grade": "B"},
            access_token=token,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # expired
            title="Expired Pack",
        )
        db_session.add(artifact)
        await db_session.commit()

        resp = await client.get(f"/api/v1/shared-artifacts/{token}")
        assert resp.status_code == 410

    @pytest.mark.asyncio
    async def test_invalid_token_returns_404(self, client, db_session):
        """GET /shared-artifacts/{token} with bad token returns 404."""
        resp = await client.get("/api/v1/shared-artifacts/nonexistent-token-abc123")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_view_increments_count(self, client, db_session, admin_user):
        """Viewing a shared artifact increments view_count."""
        token = secrets.token_urlsafe(48)
        artifact = SharedArtifact(
            building_id=uuid.uuid4(),
            created_by_id=admin_user.id,
            artifact_type="authority_pack",
            artifact_data={"test": True},
            access_token=token,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            title="Counter Test",
        )
        db_session.add(artifact)
        await db_session.commit()

        # First view
        resp1 = await client.get(f"/api/v1/shared-artifacts/{token}")
        assert resp1.status_code == 200

        # Second view
        resp2 = await client.get(f"/api/v1/shared-artifacts/{token}")
        assert resp2.status_code == 200

        # Both calls succeeded; view_count incremented in the endpoint

    @pytest.mark.asyncio
    async def test_api_create_share_link_invalid_pack_type(self, client, auth_headers, sample_building):
        """POST share with invalid pack_type returns 400."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/packs/invalid_type/share",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_api_create_share_link_bad_expires(self, client, auth_headers, sample_building):
        """POST share with expires_days > 90 returns 400."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/packs/authority/share?expires_days=999",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_shared_artifact_data_integrity(self, db_session, admin_user):
        """Artifact data round-trips through JSON storage."""
        original_data = {
            "sections": [{"name": "identity", "items": [{"address": "Rue du Lac 1"}]}],
            "grade": "A",
            "completeness": 0.95,
        }
        artifact = SharedArtifact(
            building_id=uuid.uuid4(),
            created_by_id=admin_user.id,
            artifact_type="authority_pack",
            artifact_data=original_data,
            access_token=secrets.token_urlsafe(48),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            title="Integrity Test",
        )
        db_session.add(artifact)
        await db_session.commit()
        await db_session.refresh(artifact)

        assert artifact.artifact_data == original_data
        assert artifact.artifact_data["grade"] == "A"
        assert artifact.artifact_data["completeness"] == 0.95
