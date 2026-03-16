"""Tests for evidence link API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.api.evidence import router as evidence_router
from app.main import app
from app.models.action_item import ActionItem
from app.models.building_risk_score import BuildingRiskScore
from app.models.evidence_link import EvidenceLink

# Register the router for tests (not yet in router.py)
app.include_router(evidence_router, prefix="/api/v1")


def _make_token(user_id, email, role):
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")


@pytest.mark.asyncio
class TestEvidenceAPI:
    """Evidence link API tests."""

    async def test_create_evidence_link_admin(self, client, admin_user, auth_headers):
        """Admin can create evidence links."""
        data = {
            "source_type": "diagnostic",
            "source_id": str(uuid.uuid4()),
            "target_type": "risk_score",
            "target_id": str(uuid.uuid4()),
            "relationship": "confirms",
            "confidence": 0.85,
        }
        resp = await client.post("/api/v1/evidence", json=data, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["source_type"] == "diagnostic"
        assert body["relationship"] == "confirms"
        assert body["confidence"] == 0.85
        assert body["created_by"] == str(admin_user.id)

    async def test_create_evidence_link_diagnostician(self, client, diagnostician_user, diag_headers):
        """Diagnostician can create evidence links."""
        data = {
            "source_type": "sample",
            "source_id": str(uuid.uuid4()),
            "target_type": "action_item",
            "target_id": str(uuid.uuid4()),
            "relationship": "justifies",
        }
        resp = await client.post("/api/v1/evidence", json=data, headers=diag_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["created_by"] == str(diagnostician_user.id)

    async def test_create_evidence_link_with_legal_reference(self, client, auth_headers):
        """Evidence link can include legal reference and explanation."""
        data = {
            "source_type": "regulation",
            "source_id": str(uuid.uuid4()),
            "target_type": "risk_score",
            "target_id": str(uuid.uuid4()),
            "relationship": "mandates",
            "confidence": 1.0,
            "legal_reference": "OTConst Art. 60a",
            "explanation": "Obligation de diagnostic amiante avant travaux",
        }
        resp = await client.post("/api/v1/evidence", json=data, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["legal_reference"] == "OTConst Art. 60a"
        assert body["explanation"] == "Obligation de diagnostic amiante avant travaux"

    async def test_owner_cannot_create_evidence(self, client, owner_headers):
        """Owner role does not have evidence:create permission."""
        data = {
            "source_type": "diagnostic",
            "source_id": str(uuid.uuid4()),
            "target_type": "risk_score",
            "target_id": str(uuid.uuid4()),
            "relationship": "confirms",
        }
        resp = await client.post("/api/v1/evidence", json=data, headers=owner_headers)
        assert resp.status_code == 403

    async def test_architect_cannot_create_evidence(self, client, db_session):
        """Architect role does not have evidence:create permission."""
        from app.models.user import User

        architect = User(
            id=uuid.uuid4(),
            email="architect@test.ch",
            password_hash="$2b$12$LJ3m4ys3Lg2V5K7G0q/8OerFEH3sGy7r7K0u5e5v5K7G0q/8Oabc",
            first_name="Archi",
            last_name="Test",
            role="architect",
            is_active=True,
            language="fr",
        )
        db_session.add(architect)
        await db_session.commit()
        headers = {"Authorization": f"Bearer {_make_token(architect.id, architect.email, 'architect')}"}

        data = {
            "source_type": "diagnostic",
            "source_id": str(uuid.uuid4()),
            "target_type": "risk_score",
            "target_id": str(uuid.uuid4()),
            "relationship": "confirms",
        }
        resp = await client.post("/api/v1/evidence", json=data, headers=headers)
        assert resp.status_code == 403

    async def test_get_evidence_by_id(self, client, admin_user, auth_headers, db_session):
        """Can retrieve a single evidence link by ID."""
        evidence = EvidenceLink(
            id=uuid.uuid4(),
            source_type="diagnostic",
            source_id=uuid.uuid4(),
            target_type="risk_score",
            target_id=uuid.uuid4(),
            relationship="confirms",
            confidence=0.9,
            created_by=admin_user.id,
        )
        db_session.add(evidence)
        await db_session.commit()

        resp = await client.get(f"/api/v1/evidence/{evidence.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(evidence.id)
        assert body["relationship"] == "confirms"

    async def test_evidence_not_found(self, client, auth_headers):
        """Returns 404 for non-existent evidence link."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/evidence/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_list_building_evidence(self, client, admin_user, auth_headers, db_session, sample_building):
        """List evidence links aggregated for a building."""
        # Create a risk score for the building
        risk_score = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            overall_risk_level="high",
        )
        db_session.add(risk_score)

        # Create an action item for the building
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            source_type="manual",
            action_type="remediation",
            title="Remove asbestos",
            priority="high",
            status="open",
        )
        db_session.add(action)
        await db_session.flush()

        # Create evidence links targeting these
        ev1 = EvidenceLink(
            id=uuid.uuid4(),
            source_type="diagnostic",
            source_id=uuid.uuid4(),
            target_type="risk_score",
            target_id=risk_score.id,
            relationship="confirms",
            created_by=admin_user.id,
        )
        ev2 = EvidenceLink(
            id=uuid.uuid4(),
            source_type="sample",
            source_id=uuid.uuid4(),
            target_type="action_item",
            target_id=action.id,
            relationship="justifies",
            created_by=admin_user.id,
        )
        db_session.add_all([ev1, ev2])
        await db_session.commit()

        resp = await client.get(f"/api/v1/buildings/{sample_building.id}/evidence", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        ids = {item["id"] for item in body}
        assert str(ev1.id) in ids
        assert str(ev2.id) in ids

    async def test_list_risk_score_evidence(self, client, admin_user, auth_headers, db_session):
        """List evidence links for a specific risk score."""
        score_id = uuid.uuid4()
        ev = EvidenceLink(
            id=uuid.uuid4(),
            source_type="diagnostic",
            source_id=uuid.uuid4(),
            target_type="risk_score",
            target_id=score_id,
            relationship="confirms",
            created_by=admin_user.id,
        )
        db_session.add(ev)
        await db_session.commit()

        resp = await client.get(f"/api/v1/risk-scores/{score_id}/evidence", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["id"] == str(ev.id)

    async def test_list_building_evidence_empty(self, client, auth_headers, sample_building):
        """Returns empty list when building has no risk scores or action items."""
        resp = await client.get(f"/api/v1/buildings/{sample_building.id}/evidence", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []
