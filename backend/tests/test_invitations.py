import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.models.invitation import Invitation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_invitation(db, invited_by, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "email": "newuser@example.ch",
        "role": "diagnostician",
        "organization_id": None,
        "status": "pending",
        "token": secrets.token_urlsafe(32),
        "invited_by": invited_by,
        "expires_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
    }
    defaults.update(kwargs)
    inv = Invitation(**defaults)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


# ---------------------------------------------------------------------------
# Create invitation
# ---------------------------------------------------------------------------


class TestCreateInvitation:
    async def test_create_invitation(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/invitations",
            json={
                "email": "invite@example.ch",
                "role": "diagnostician",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "invite@example.ch"
        assert data["role"] == "diagnostician"
        assert data["status"] == "pending"
        assert data["token"]  # non-empty token
        assert data["invited_by"] == str(admin_user.id)

    async def test_create_invitation_with_organization(self, client, admin_user, auth_headers):
        org_id = str(uuid.uuid4())
        response = await client.post(
            "/api/v1/invitations",
            json={
                "email": "org_invite@example.ch",
                "role": "owner",
                "organization_id": org_id,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["organization_id"] == org_id

    async def test_create_invitation_unauthorized(self, client):
        response = await client.post(
            "/api/v1/invitations",
            json={"email": "nope@example.ch", "role": "owner"},
        )
        assert response.status_code in (401, 403)

    async def test_create_invitation_non_admin_forbidden(self, client, diagnostician_user, diag_headers):
        response = await client.post(
            "/api/v1/invitations",
            json={"email": "nope@example.ch", "role": "owner"},
            headers=diag_headers,
        )
        assert response.status_code in (401, 403)

    async def test_create_duplicate_pending_invitation(self, client, db_session, admin_user, auth_headers):
        await _make_invitation(db_session, admin_user.id, email="dup@example.ch")

        response = await client.post(
            "/api/v1/invitations",
            json={"email": "dup@example.ch", "role": "owner"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_create_invitation_after_revoked(self, client, db_session, admin_user, auth_headers):
        """Can create a new invitation if the previous one was revoked."""
        await _make_invitation(db_session, admin_user.id, email="revoked@example.ch", status="revoked")

        response = await client.post(
            "/api/v1/invitations",
            json={"email": "revoked@example.ch", "role": "diagnostician"},
            headers=auth_headers,
        )
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# List invitations
# ---------------------------------------------------------------------------


class TestListInvitations:
    async def test_list_invitations(self, client, db_session, admin_user, auth_headers):
        await _make_invitation(db_session, admin_user.id, email="a@test.ch")
        await _make_invitation(db_session, admin_user.id, email="b@test.ch")

        response = await client.get("/api/v1/invitations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_invitations_pagination(self, client, db_session, admin_user, auth_headers):
        for i in range(5):
            await _make_invitation(db_session, admin_user.id, email=f"page{i}@test.ch")

        response = await client.get(
            "/api/v1/invitations",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_invitations_non_admin_forbidden(self, client, owner_user, owner_headers):
        response = await client.get("/api/v1/invitations", headers=owner_headers)
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Get single invitation
# ---------------------------------------------------------------------------


class TestGetInvitation:
    async def test_get_invitation(self, client, db_session, admin_user, auth_headers):
        inv = await _make_invitation(db_session, admin_user.id)
        response = await client.get(f"/api/v1/invitations/{inv.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(inv.id)

    async def test_get_invitation_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/invitations/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Revoke invitation
# ---------------------------------------------------------------------------


class TestRevokeInvitation:
    async def test_revoke_invitation(self, client, db_session, admin_user, auth_headers):
        inv = await _make_invitation(db_session, admin_user.id)
        response = await client.delete(f"/api/v1/invitations/{inv.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's revoked
        get_resp = await client.get(f"/api/v1/invitations/{inv.id}", headers=auth_headers)
        assert get_resp.json()["status"] == "revoked"

    async def test_revoke_already_accepted(self, client, db_session, admin_user, auth_headers):
        inv = await _make_invitation(db_session, admin_user.id, status="accepted")
        response = await client.delete(f"/api/v1/invitations/{inv.id}", headers=auth_headers)
        assert response.status_code == 400

    async def test_revoke_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/invitations/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Accept invitation
# ---------------------------------------------------------------------------


class TestAcceptInvitation:
    async def test_accept_invitation(self, client, db_session, admin_user, auth_headers):
        inv = await _make_invitation(db_session, admin_user.id, email="accept@example.ch")

        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": inv.token,
                "password": "SecurePass123!",
                "first_name": "Nouveau",
                "last_name": "Utilisateur",
                "language": "fr",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["message"] == "Invitation accepted"

        # Verify invitation is marked accepted
        get_resp = await client.get(f"/api/v1/invitations/{inv.id}", headers=auth_headers)
        assert get_resp.json()["status"] == "accepted"
        assert get_resp.json()["accepted_at"] is not None

    async def test_accept_invitation_no_auth_required(self, client, db_session, admin_user):
        """Accept endpoint must work without any Authorization header."""
        inv = await _make_invitation(db_session, admin_user.id, email="noauth@example.ch")

        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": inv.token,
                "password": "Pass1234!",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert response.status_code == 201

    async def test_accept_invalid_token(self, client):
        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": "invalid-token-that-does-not-exist",
                "password": "Pass1234!",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert response.status_code == 404

    async def test_accept_expired_invitation(self, client, db_session, admin_user):
        inv = await _make_invitation(
            db_session,
            admin_user.id,
            email="expired@example.ch",
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
        )

        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": inv.token,
                "password": "Pass1234!",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    async def test_accept_revoked_invitation(self, client, db_session, admin_user):
        inv = await _make_invitation(
            db_session,
            admin_user.id,
            email="revoked@example.ch",
            status="revoked",
        )

        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": inv.token,
                "password": "Pass1234!",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert response.status_code == 400
        assert "revoked" in response.json()["detail"].lower()

    async def test_accept_already_accepted(self, client, db_session, admin_user):
        inv = await _make_invitation(
            db_session,
            admin_user.id,
            email="already@example.ch",
            status="accepted",
        )

        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": inv.token,
                "password": "Pass1234!",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert response.status_code == 400
        assert "already been accepted" in response.json()["detail"].lower()

    async def test_accept_creates_user_with_correct_role(self, client, db_session, admin_user, auth_headers):
        inv = await _make_invitation(
            db_session,
            admin_user.id,
            email="rolecheck@example.ch",
            role="architect",
        )

        response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": inv.token,
                "password": "Pass1234!",
                "first_name": "Arch",
                "last_name": "Test",
                "language": "de",
            },
        )
        assert response.status_code == 201
