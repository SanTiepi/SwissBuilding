class TestUpdateProfile:
    async def test_update_profile_full(self, client, admin_user, auth_headers):
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"first_name": "Updated", "last_name": "Name", "language": "de"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["language"] == "de"

    async def test_update_profile_partial(self, client, admin_user, auth_headers):
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"first_name": "OnlyFirst"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "OnlyFirst"
        assert data["last_name"] == "Test"  # unchanged

    async def test_update_profile_empty_body(self, client, admin_user, auth_headers):
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Admin"  # unchanged

    async def test_update_profile_unauthenticated(self, client):
        response = await client.put(
            "/api/v1/auth/me",
            json={"first_name": "Hacker"},
        )
        assert response.status_code in (401, 403)


class TestChangePassword:
    async def test_change_password_success(self, client, admin_user, auth_headers):
        response = await client.put(
            "/api/v1/auth/me/password",
            headers=auth_headers,
            json={"current_password": "admin123", "new_password": "newpass123"},
        )
        assert response.status_code == 204

        # Verify can login with new password
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "newpass123"},
        )
        assert response.status_code == 200

    async def test_change_password_wrong_current(self, client, admin_user, auth_headers):
        response = await client.put(
            "/api/v1/auth/me/password",
            headers=auth_headers,
            json={"current_password": "wrongpass", "new_password": "newpass123"},
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    async def test_change_password_too_short(self, client, admin_user, auth_headers):
        response = await client.put(
            "/api/v1/auth/me/password",
            headers=auth_headers,
            json={"current_password": "admin123", "new_password": "short"},
        )
        assert response.status_code == 422

    async def test_change_password_unauthenticated(self, client):
        response = await client.put(
            "/api/v1/auth/me/password",
            json={"current_password": "admin123", "new_password": "newpass123"},
        )
        assert response.status_code in (401, 403)


class TestGetMe:
    async def test_get_me_returns_profile(self, client, admin_user, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.ch"
        assert data["first_name"] == "Admin"
        assert data["role"] == "admin"
        assert "password_hash" not in data
