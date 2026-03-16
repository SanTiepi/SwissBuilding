class TestHealthCheck:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestLogin:
    async def test_login_success(self, client, admin_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_wrong_password(self, client, admin_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@test.ch", "password": "whatever"},
        )
        assert response.status_code == 401


class TestMe:
    async def test_get_me_authenticated(self, client, admin_user, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.ch"
        assert data["first_name"] == "Admin"
        assert data["last_name"] == "Test"
        assert data["role"] == "admin"

    async def test_get_me_no_token(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)


class TestRegister:
    async def test_register_owner(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newowner@test.ch",
                "password": "securepass123",
                "first_name": "New",
                "last_name": "Owner",
                "role": "owner",
                "language": "fr",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newowner@test.ch"
        assert data["role"] == "owner"

    async def test_register_non_owner_rejected(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hacker@test.ch",
                "password": "securepass123",
                "first_name": "Hack",
                "last_name": "Er",
                "role": "admin",
                "language": "fr",
            },
        )
        assert response.status_code == 400
