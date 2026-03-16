"""
SwissBuildingOS - Comprehensive UI Simulation Stress Tests

Simulates every form the UI would present to users with normal, edge-case,
unicode, empty, boundary, and wrong-type data.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(user, role=None):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": role or user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")


def _headers(user, role=None):
    return {"Authorization": f"Bearer {_make_token(user, role)}"}


VALID_BUILDING = {
    "address": "Rue de Bourg 1",
    "postal_code": "1003",
    "city": "Lausanne",
    "canton": "VD",
    "building_type": "residential",
    "construction_year": 1965,
}


def _valid_diagnostic(date_str="2024-06-15"):
    return {
        "diagnostic_type": "asbestos",
        "diagnostic_context": "AvT",
        "date_inspection": date_str,
    }


def _valid_sample():
    return {
        "sample_number": "ECH-001",
        "material_category": "flocage",
        "pollutant_type": "asbestos",
        "concentration": 5.0,
        "unit": "percent_weight",
    }


async def _create_building(client, headers, overrides=None):
    data = dict(VALID_BUILDING)
    if overrides:
        data.update(overrides)
    return await client.post("/api/v1/buildings", json=data, headers=headers)


async def _create_diagnostic(client, headers, building_id, overrides=None):
    data = _valid_diagnostic()
    if overrides:
        data.update(overrides)
    return await client.post(f"/api/v1/buildings/{building_id}/diagnostics", json=data, headers=headers)


async def _create_sample(client, headers, diagnostic_id, overrides=None):
    data = _valid_sample()
    if overrides:
        data.update(overrides)
    return await client.post(f"/api/v1/diagnostics/{diagnostic_id}/samples", json=data, headers=headers)


# ===================================================================
# 1. LOGIN FORM TESTS
# ===================================================================


class TestLoginForm:
    """Simulate the login form with various inputs."""

    async def test_login_valid_credentials(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "admin123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@test.ch"

    async def test_login_wrong_password(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "wrongpass"},
        )
        assert r.status_code == 401

    async def test_login_nonexistent_email(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.ch", "password": "admin123"},
        )
        assert r.status_code == 401

    async def test_login_empty_email(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "", "password": "admin123"},
        )
        assert r.status_code in (401, 422)

    async def test_login_empty_password(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": ""},
        )
        assert r.status_code in (401, 422)

    async def test_login_unicode_password(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "\u00e9\u00e0\u00fc\u00f6\u00e4\u00df\u00e7\u00f1"},
        )
        assert r.status_code == 401

    async def test_login_very_long_email(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "a" * 5000 + "@test.ch", "password": "admin123"},
        )
        assert r.status_code in (401, 422)

    async def test_login_very_long_password(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "x" * 10000},
        )
        # bcrypt silently truncates at 72 bytes, so this returns 401
        assert r.status_code in (401, 422, 500)

    async def test_login_special_chars_password(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": '!@#$%^&*(){}[]|\\:";<>,.?/~`'},
        )
        assert r.status_code == 401

    async def test_login_null_bytes_password(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.ch", "password": "pass\x00word"},
        )
        # bcrypt does not allow NULL bytes - may raise 401, 422, or 500
        assert r.status_code in (401, 422, 500)

    async def test_login_missing_fields(self, client, admin_user):
        r = await client.post("/api/v1/auth/login", json={})
        assert r.status_code == 422

    async def test_login_sql_injection_attempt(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "' OR 1=1 --", "password": "admin123"},
        )
        assert r.status_code == 401


# ===================================================================
# 2. REGISTER FORM TESTS
# ===================================================================


class TestRegisterForm:
    """Simulate the registration form."""

    async def test_register_basic(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@test.ch",
                "password": "securepassword123",
                "first_name": "Jean",
                "last_name": "Dupont",
                "role": "owner",
                "language": "fr",
            },
        )
        assert r.status_code == 201
        assert r.json()["email"] == "new@test.ch"

    @pytest.mark.parametrize("lang", ["fr", "de", "it", "en"])
    async def test_register_all_languages(self, client, lang):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"user_{lang}@test.ch",
                "password": "securepassword123",
                "first_name": "Test",
                "last_name": "User",
                "role": "owner",
                "language": lang,
            },
        )
        assert r.status_code == 201
        assert r.json()["language"] == lang

    async def test_register_accented_names_muller(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "muller@test.ch",
                "password": "securepassword123",
                "first_name": "Hans",
                "last_name": "M\u00fcller",
                "role": "owner",
            },
        )
        assert r.status_code == 201
        assert r.json()["last_name"] == "M\u00fcller"

    async def test_register_accented_names_crete(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "crete@test.ch",
                "password": "securepassword123",
                "first_name": "Pierre",
                "last_name": "Cr\u00eate",
                "role": "owner",
            },
        )
        assert r.status_code == 201
        assert r.json()["last_name"] == "Cr\u00eate"

    async def test_register_accented_names_bjork(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "bjork@test.ch",
                "password": "securepassword123",
                "first_name": "Bj\u00f6rk",
                "last_name": "Gudmundsdottir",
                "role": "owner",
            },
        )
        assert r.status_code == 201

    async def test_register_short_password(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpw@test.ch",
                "password": "short",
                "first_name": "A",
                "last_name": "B",
                "role": "owner",
            },
        )
        assert r.status_code == 422

    async def test_register_non_owner_role_rejected(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "notowner@test.ch",
                "password": "securepassword123",
                "first_name": "A",
                "last_name": "B",
                "role": "admin",
            },
        )
        assert r.status_code == 400

    async def test_register_duplicate_email(self, client, admin_user):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.ch",
                "password": "securepassword123",
                "first_name": "Dup",
                "last_name": "User",
                "role": "owner",
            },
        )
        assert r.status_code == 409

    async def test_register_very_long_name(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "longname@test.ch",
                "password": "securepassword123",
                "first_name": "A" * 500,
                "last_name": "B" * 500,
                "role": "owner",
            },
        )
        # Should succeed or fail gracefully
        assert r.status_code in (201, 422, 500)

    async def test_register_special_chars_in_name(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "specialname@test.ch",
                "password": "securepassword123",
                "first_name": "Jean-Pierre",
                "last_name": "O'Connor",
                "role": "owner",
            },
        )
        assert r.status_code == 201


# ===================================================================
# 3. AUTH/ME TESTS
# ===================================================================


class TestAuthMe:
    async def test_me_valid_token(self, client, admin_user, auth_headers):
        r = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "admin@test.ch"

    async def test_me_no_token(self, client, admin_user):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code in (401, 403)

    async def test_me_invalid_token(self, client, admin_user):
        r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401


# ===================================================================
# 4. BUILDING FORM TESTS
# ===================================================================


class TestBuildingForm:
    """Simulate the building creation form."""

    ALL_CANTONS = [
        "AG",
        "AI",
        "AR",
        "BE",
        "BL",
        "BS",
        "FR",
        "GE",
        "GL",
        "GR",
        "JU",
        "LU",
        "NE",
        "NW",
        "OW",
        "SG",
        "SH",
        "SO",
        "SZ",
        "TG",
        "TI",
        "UR",
        "VD",
        "VS",
        "ZG",
        "ZH",
    ]

    ALL_BUILDING_TYPES = [
        "residential",
        "commercial",
        "industrial",
        "mixed",
        "public",
        "education",
        "health",
        "religious",
        "historical",
    ]

    @pytest.mark.parametrize("canton", ALL_CANTONS)
    async def test_building_every_canton(self, client, admin_user, auth_headers, canton):
        r = await _create_building(
            client,
            auth_headers,
            {
                "canton": canton,
                "address": f"Strasse {canton}",
                "postal_code": "1000",
                "city": f"City{canton}",
            },
        )
        assert r.status_code == 201
        assert r.json()["canton"] == canton

    @pytest.mark.parametrize("btype", ALL_BUILDING_TYPES)
    async def test_building_every_type(self, client, admin_user, auth_headers, btype):
        r = await _create_building(
            client,
            auth_headers,
            {
                "building_type": btype,
                "address": f"Addr {btype}",
            },
        )
        assert r.status_code == 201
        assert r.json()["building_type"] == btype

    async def test_building_boundary_year_1800(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"construction_year": 1800})
        assert r.status_code == 201

    async def test_building_boundary_year_1990(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"construction_year": 1990})
        assert r.status_code == 201

    async def test_building_boundary_year_2025(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"construction_year": 2025})
        assert r.status_code == 201

    async def test_building_no_year(self, client, admin_user, auth_headers):
        data = dict(VALID_BUILDING)
        data.pop("construction_year", None)
        r = await client.post("/api/v1/buildings", json=data, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["construction_year"] is None

    async def test_building_negative_year(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"construction_year": -100})
        # The API doesn't validate year range, should create but use today's date for event
        assert r.status_code in (201, 422)

    async def test_building_year_zero(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"construction_year": 0})
        assert r.status_code in (201, 422)

    async def test_building_invalid_postal_code_short(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"postal_code": "123"})
        assert r.status_code == 422

    async def test_building_invalid_postal_code_long(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"postal_code": "12345"})
        assert r.status_code == 422

    async def test_building_invalid_postal_code_letters(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"postal_code": "ABCD"})
        assert r.status_code == 422

    async def test_building_canton_too_long(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"canton": "VDD"})
        assert r.status_code == 422

    async def test_building_canton_too_short(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"canton": "V"})
        assert r.status_code == 422

    async def test_building_with_coordinates(self, client, admin_user, auth_headers):
        r = await _create_building(
            client,
            auth_headers,
            {
                "latitude": 46.5197,
                "longitude": 6.6323,
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["latitude"] == pytest.approx(46.5197)
        assert data["longitude"] == pytest.approx(6.6323)

    async def test_building_huge_surface(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"surface_area_m2": 999999.99})
        assert r.status_code == 201

    async def test_building_negative_floors(self, client, admin_user, auth_headers):
        r = await _create_building(
            client,
            auth_headers,
            {
                "floors_above": -1,
                "floors_below": -3,
            },
        )
        assert r.status_code in (201, 422)

    async def test_building_with_egrid(self, client, admin_user, auth_headers):
        r = await _create_building(
            client,
            auth_headers,
            {
                "egrid": "CH123456789012",
            },
        )
        assert r.status_code == 201
        assert r.json()["egrid"] == "CH123456789012"

    async def test_building_unicode_address(self, client, admin_user, auth_headers):
        r = await _create_building(
            client,
            auth_headers,
            {
                "address": "Rue de l'\u00c9glise 42",
                "city": "Gen\u00e8ve",
            },
        )
        assert r.status_code == 201
        assert "\u00c9glise" in r.json()["address"]

    async def test_building_missing_required_fields(self, client, admin_user, auth_headers):
        r = await client.post("/api/v1/buildings", json={}, headers=auth_headers)
        assert r.status_code == 422

    async def test_building_float_construction_year(self, client, admin_user, auth_headers):
        r = await _create_building(client, auth_headers, {"construction_year": 1965.5})
        # Pydantic should coerce or reject
        assert r.status_code in (201, 422)


# ===================================================================
# 5. DIAGNOSTIC FORM TESTS
# ===================================================================


class TestDiagnosticForm:
    """Simulate the diagnostic creation form."""

    DIAGNOSTIC_TYPES = ["asbestos", "pcb", "lead", "hap", "radon", "full"]
    DIAGNOSTIC_CONTEXTS = ["UN", "AvT", "ApT"]

    @pytest.mark.parametrize("dtype", DIAGNOSTIC_TYPES)
    async def test_diagnostic_each_type(self, client, admin_user, auth_headers, sample_building, dtype):
        r = await _create_diagnostic(
            client,
            auth_headers,
            sample_building.id,
            {
                "diagnostic_type": dtype,
            },
        )
        assert r.status_code == 201
        assert r.json()["diagnostic_type"] == dtype

    @pytest.mark.parametrize("ctx", DIAGNOSTIC_CONTEXTS)
    async def test_diagnostic_each_context(self, client, admin_user, auth_headers, sample_building, ctx):
        r = await _create_diagnostic(
            client,
            auth_headers,
            sample_building.id,
            {
                "diagnostic_context": ctx,
            },
        )
        assert r.status_code == 201
        assert r.json()["diagnostic_context"] == ctx

    async def test_diagnostic_past_date(self, client, admin_user, auth_headers, sample_building):
        r = await _create_diagnostic(
            client,
            auth_headers,
            sample_building.id,
            {
                "date_inspection": "2020-01-15",
            },
        )
        assert r.status_code == 201

    async def test_diagnostic_future_date(self, client, admin_user, auth_headers, sample_building):
        future = (date.today() + timedelta(days=30)).isoformat()
        r = await _create_diagnostic(
            client,
            auth_headers,
            sample_building.id,
            {
                "date_inspection": future,
            },
        )
        assert r.status_code == 201

    async def test_diagnostic_with_laboratory(self, client, admin_user, auth_headers, sample_building):
        r = await _create_diagnostic(
            client,
            auth_headers,
            sample_building.id,
            {
                "laboratory": "Laboratoire de Microanalyse SA, Lancy",
                "methodology": "PLM + MET",
                "summary": "Diagnostic amiante avant travaux",
            },
        )
        assert r.status_code == 201
        assert r.json()["laboratory"] == "Laboratoire de Microanalyse SA, Lancy"

    async def test_diagnostic_missing_date(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/diagnostics",
            json={"diagnostic_type": "asbestos"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    async def test_diagnostic_nonexistent_building(self, client, admin_user, auth_headers):
        fake_id = str(uuid.uuid4())
        r = await _create_diagnostic(client, auth_headers, fake_id)
        # Should 404 or create (depends on FK enforcement in SQLite)
        assert r.status_code in (201, 404, 422, 500)

    async def test_diagnostic_invalid_date_format(self, client, admin_user, auth_headers, sample_building):
        r = await _create_diagnostic(
            client,
            auth_headers,
            sample_building.id,
            {
                "date_inspection": "15/06/2024",
            },
        )
        assert r.status_code == 422


# ===================================================================
# 6. SAMPLE FORM TESTS
# ===================================================================


class TestSampleForm:
    """Simulate the sample creation form."""

    POLLUTANT_UNIT_PAIRS = [
        ("asbestos", "percent_weight", 2.5),
        ("asbestos", "fibers_per_m3", 5000.0),
        ("pcb", "mg_per_kg", 120.0),
        ("pcb", "ng_per_m3", 8000.0),
        ("lead", "mg_per_kg", 7000.0),
        ("lead", "ug_per_l", 15.0),
        ("hap", "mg_per_kg", 500.0),
        ("radon", "bq_per_m3", 450.0),
    ]

    MATERIAL_STATES = ["bon", "mauvais", "degraded", "good", "heavily_degraded", "friable"]

    MATERIAL_CATEGORIES = [
        "flocage",
        "calorifuge",
        "joints",
        "colles_carrelage",
        "dalles_vinyle",
        "fibre_cement",
        "enduit",
        "peinture",
        "mastic_fenetre",
        "etancheite_toiture",
        "conduits",
    ]

    @pytest.fixture
    async def diagnostic_for_samples(self, client, admin_user, auth_headers, sample_building):
        r = await _create_diagnostic(client, auth_headers, sample_building.id)
        assert r.status_code == 201
        return r.json()["id"]

    @pytest.mark.parametrize("pollutant,unit,concentration", POLLUTANT_UNIT_PAIRS)
    async def test_sample_each_pollutant_unit(
        self, client, admin_user, auth_headers, diagnostic_for_samples, pollutant, unit, concentration
    ):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "sample_number": f"S-{pollutant}-{unit}",
                "pollutant_type": pollutant,
                "unit": unit,
                "concentration": concentration,
                "material_category": "flocage",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["pollutant_type"] == pollutant
        assert data["unit"] == unit

    async def test_sample_extreme_concentration_low(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "concentration": 0.0001,
            },
        )
        assert r.status_code == 201
        assert r.json()["concentration"] == pytest.approx(0.0001)

    async def test_sample_extreme_concentration_high(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "concentration": 999999.0,
            },
        )
        assert r.status_code == 201

    async def test_sample_zero_concentration(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "concentration": 0.0,
            },
        )
        assert r.status_code == 201

    async def test_sample_null_concentration(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "concentration": None,
            },
        )
        assert r.status_code == 201
        assert r.json()["risk_level"] == "low"

    async def test_sample_negative_concentration(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "concentration": -5.0,
            },
        )
        # Negative concentration is unusual but the API does not reject it
        assert r.status_code in (201, 422)

    @pytest.mark.parametrize("state", MATERIAL_STATES)
    async def test_sample_each_material_state(self, client, admin_user, auth_headers, diagnostic_for_samples, state):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "sample_number": f"S-{state}",
                "material_state": state,
            },
        )
        assert r.status_code == 201

    @pytest.mark.parametrize("cat", MATERIAL_CATEGORIES)
    async def test_sample_each_material_category(self, client, admin_user, auth_headers, diagnostic_for_samples, cat):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "sample_number": f"S-cat-{cat}",
                "material_category": cat,
            },
        )
        assert r.status_code == 201

    async def test_sample_with_location(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "location_floor": "2\u00e8me \u00e9tage",
                "location_room": "Salle de bain",
                "location_detail": "Derri\u00e8re le lavabo, joints carrelage",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert "\u00e9tage" in data["location_floor"]

    async def test_sample_with_notes(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await _create_sample(
            client,
            auth_headers,
            diagnostic_for_samples,
            {
                "notes": "Mat\u00e9riau friable, pr\u00e9l\u00e8vement difficile. Observation: fibres visibles.",
                "pollutant_subtype": "chrysotile",
            },
        )
        assert r.status_code == 201

    async def test_sample_missing_required_fields(self, client, admin_user, auth_headers, diagnostic_for_samples):
        r = await client.post(
            f"/api/v1/diagnostics/{diagnostic_for_samples}/samples",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 422


# ===================================================================
# 7. EVENT FORM TESTS
# ===================================================================


class TestEventForm:
    """Simulate the event creation form."""

    async def test_event_basic(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={
                "event_type": "inspection",
                "date": "2024-03-15",
                "title": "Inspection annuelle",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["event_type"] == "inspection"

    async def test_event_unicode_title(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={
                "event_type": "renovation",
                "date": "2024-07-01",
                "title": "R\u00e9novation fa\u00e7ade - b\u00e2timent \u00c9glise",
                "description": "\u00c9limination de l'amiante dans les joints de fa\u00e7ade",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201

    async def test_event_very_long_description(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={
                "event_type": "note",
                "date": "2024-01-01",
                "title": "Note",
                "description": "D" * 5000,
            },
            headers=auth_headers,
        )
        assert r.status_code == 201

    async def test_event_with_metadata(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={
                "event_type": "permit",
                "date": "2024-02-20",
                "title": "Permis de construire",
                "metadata_json": {"permit_number": "PC-2024-001", "authority": "Commune"},
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["metadata_json"]["permit_number"] == "PC-2024-001"

    async def test_event_list(self, client, admin_user, auth_headers, sample_building):
        # Create then list
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={"event_type": "test", "date": "2024-01-01", "title": "Test"},
            headers=auth_headers,
        )
        r = await client.get(
            f"/api/v1/buildings/{sample_building.id}/events",
            headers=auth_headers,
        )
        assert r.status_code == 200
        # At least 1 event (from building creation) + the one we just made
        assert len(r.json()) >= 1


# ===================================================================
# 8. CONCURRENT OPERATIONS (Full workflow)
# ===================================================================


class TestConcurrentOperations:
    """Simulate a full user workflow: create building -> diagnostic -> samples -> list."""

    async def test_full_workflow(self, client, admin_user, auth_headers):
        # Create building
        br = await _create_building(
            client,
            auth_headers,
            {
                "address": "Workflow Strasse 1",
                "postal_code": "8001",
                "city": "Zurich",
                "canton": "ZH",
                "building_type": "commercial",
                "construction_year": 1975,
            },
        )
        assert br.status_code == 201
        building_id = br.json()["id"]

        # Create diagnostic
        dr = await _create_diagnostic(
            client,
            auth_headers,
            building_id,
            {
                "diagnostic_type": "full",
                "diagnostic_context": "AvT",
                "date_inspection": "2024-06-01",
                "laboratory": "EMPA Z\u00fcrich",
            },
        )
        assert dr.status_code == 201
        diag_id = dr.json()["id"]

        # Create samples
        for i in range(3):
            sr = await _create_sample(
                client,
                auth_headers,
                diag_id,
                {
                    "sample_number": f"WF-{i + 1:03d}",
                    "material_category": "joints",
                    "pollutant_type": "pcb",
                    "concentration": 50.0 + i * 30,
                    "unit": "mg_per_kg",
                },
            )
            assert sr.status_code == 201

        # List diagnostics
        lr = await client.get(
            f"/api/v1/buildings/{building_id}/diagnostics",
            headers=auth_headers,
        )
        assert lr.status_code == 200
        diags = lr.json()
        assert len(diags) >= 1

        # List samples
        slr = await client.get(
            f"/api/v1/diagnostics/{diag_id}/samples",
            headers=auth_headers,
        )
        assert slr.status_code == 200
        assert len(slr.json()) == 3

        # Get single diagnostic
        dgr = await client.get(
            f"/api/v1/diagnostics/{diag_id}",
            headers=auth_headers,
        )
        assert dgr.status_code == 200
        assert len(dgr.json()["samples"]) == 3

        # List buildings
        blr = await client.get("/api/v1/buildings", headers=auth_headers)
        assert blr.status_code == 200


# ===================================================================
# 9. RAPID SUCCESSIVE CALLS
# ===================================================================


class TestRapidSuccessiveCalls:
    """Simulate rapid creation of many resources."""

    async def test_create_10_buildings(self, client, admin_user, auth_headers):
        ids = []
        for i in range(10):
            r = await _create_building(
                client,
                auth_headers,
                {
                    "address": f"Rapid Strasse {i}",
                    "postal_code": f"{1000 + i:04d}",
                    "construction_year": 1960 + i,
                },
            )
            assert r.status_code == 201
            ids.append(r.json()["id"])
        assert len(set(ids)) == 10

    async def test_create_5_diagnostics_per_building(self, client, admin_user, auth_headers):
        br = await _create_building(
            client,
            auth_headers,
            {
                "address": "Multi-Diag Weg 1",
                "postal_code": "3000",
                "city": "Bern",
                "canton": "BE",
            },
        )
        assert br.status_code == 201
        building_id = br.json()["id"]

        diag_ids = []
        types = ["asbestos", "pcb", "lead", "hap", "radon"]
        for i, dtype in enumerate(types):
            r = await _create_diagnostic(
                client,
                auth_headers,
                building_id,
                {
                    "diagnostic_type": dtype,
                    "date_inspection": f"2024-0{i + 1}-15",
                },
            )
            assert r.status_code == 201
            diag_ids.append(r.json()["id"])
        assert len(diag_ids) == 5

        # List all diagnostics for the building
        lr = await client.get(
            f"/api/v1/buildings/{building_id}/diagnostics",
            headers=auth_headers,
        )
        assert lr.status_code == 200
        assert len(lr.json()) == 5


# ===================================================================
# 10. RBAC MATRIX TESTS
# ===================================================================


class TestRBACMatrix:
    """Test every role against key endpoint types."""

    async def test_owner_cannot_create_building(self, client, owner_user, owner_headers):
        r = await _create_building(client, owner_headers)
        assert r.status_code == 403

    async def test_owner_can_list_buildings(self, client, owner_user, owner_headers, sample_building):
        r = await client.get("/api/v1/buildings", headers=owner_headers)
        assert r.status_code == 200

    async def test_owner_can_read_building(self, client, owner_user, owner_headers, sample_building):
        r = await client.get(f"/api/v1/buildings/{sample_building.id}", headers=owner_headers)
        assert r.status_code == 200

    async def test_owner_cannot_delete_building(self, client, owner_user, owner_headers, sample_building):
        r = await client.delete(f"/api/v1/buildings/{sample_building.id}", headers=owner_headers)
        assert r.status_code == 403

    async def test_owner_cannot_create_diagnostic(self, client, owner_user, owner_headers, sample_building):
        r = await _create_diagnostic(client, owner_headers, sample_building.id)
        assert r.status_code == 403

    async def test_owner_can_list_diagnostics(self, client, owner_user, owner_headers, sample_building):
        r = await client.get(
            f"/api/v1/buildings/{sample_building.id}/diagnostics",
            headers=owner_headers,
        )
        assert r.status_code == 200

    async def test_diagnostician_can_create_diagnostic(self, client, diagnostician_user, diag_headers, sample_building):
        r = await _create_diagnostic(client, diag_headers, sample_building.id)
        assert r.status_code == 201

    async def test_diagnostician_cannot_create_building(self, client, diagnostician_user, diag_headers):
        r = await _create_building(client, diag_headers)
        assert r.status_code == 403

    async def test_diagnostician_can_create_sample(
        self, client, admin_user, auth_headers, diagnostician_user, diag_headers, sample_building
    ):
        # Create diagnostic first (as admin or diag)
        dr = await _create_diagnostic(client, diag_headers, sample_building.id)
        assert dr.status_code == 201
        diag_id = dr.json()["id"]
        # Create sample as diagnostician
        r = await _create_sample(client, diag_headers, diag_id)
        assert r.status_code == 201

    async def test_admin_can_list_users(self, client, admin_user, auth_headers):
        r = await client.get("/api/v1/users", headers=auth_headers)
        assert r.status_code == 200

    async def test_owner_cannot_list_users(self, client, owner_user, owner_headers):
        r = await client.get("/api/v1/users", headers=owner_headers)
        assert r.status_code == 403

    async def test_diagnostician_cannot_list_users(self, client, diagnostician_user, diag_headers):
        r = await client.get("/api/v1/users", headers=diag_headers)
        assert r.status_code == 403

    async def test_admin_can_delete_building(self, client, admin_user, auth_headers, sample_building):
        r = await client.delete(f"/api/v1/buildings/{sample_building.id}", headers=auth_headers)
        assert r.status_code == 204

    async def test_owner_cannot_create_event(self, client, owner_user, owner_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={"event_type": "test", "date": "2024-01-01", "title": "Test"},
            headers=owner_headers,
        )
        assert r.status_code == 403

    async def test_diagnostician_can_create_event(self, client, diagnostician_user, diag_headers, sample_building):
        r = await client.post(
            f"/api/v1/buildings/{sample_building.id}/events",
            json={"event_type": "inspection", "date": "2024-06-01", "title": "Visite"},
            headers=diag_headers,
        )
        assert r.status_code == 201


# ===================================================================
# 11. RISK ANALYSIS & SIMULATION
# ===================================================================


class TestRiskAnalysis:
    """Test risk analysis and renovation simulation endpoints."""

    async def test_risk_scores_for_building(self, client, admin_user, auth_headers):
        # Create building via API so risk score is auto-generated
        br = await _create_building(
            client,
            auth_headers,
            {
                "address": "Risk Test Strasse 1",
                "postal_code": "1000",
                "city": "Lausanne",
                "canton": "VD",
                "building_type": "residential",
                "construction_year": 1970,
            },
        )
        assert br.status_code == 201
        building_id = br.json()["id"]

        r = await client.get(
            f"/api/v1/risk-analysis/building/{building_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "overall_risk_level" in data
        assert "asbestos_probability" in data

    async def test_risk_scores_nonexistent(self, client, admin_user, auth_headers):
        fake_id = str(uuid.uuid4())
        r = await client.get(
            f"/api/v1/risk-analysis/building/{fake_id}",
            headers=auth_headers,
        )
        assert r.status_code == 404

    async def test_simulate_renovation(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            "/api/v1/risk-analysis/simulate",
            json={
                "building_id": str(sample_building.id),
                "renovation_type": "full_renovation",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["renovation_type"] == "full_renovation"
        assert "pollutant_risks" in data
        assert "total_estimated_cost_chf" in data

    async def test_simulate_renovation_partial(self, client, admin_user, auth_headers, sample_building):
        r = await client.post(
            "/api/v1/risk-analysis/simulate",
            json={
                "building_id": str(sample_building.id),
                "renovation_type": "bathroom",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200


# ===================================================================
# 12. UPDATE & DELETE OPERATIONS
# ===================================================================


class TestUpdateDeleteOps:
    """Test update and delete operations for various resources."""

    async def test_update_building(self, client, admin_user, auth_headers, sample_building):
        r = await client.put(
            f"/api/v1/buildings/{sample_building.id}",
            json={"address": "Neue Strasse 99", "construction_year": 1980},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["address"] == "Neue Strasse 99"

    async def test_update_diagnostic(self, client, admin_user, auth_headers, sample_building):
        dr = await _create_diagnostic(client, auth_headers, sample_building.id)
        diag_id = dr.json()["id"]
        r = await client.put(
            f"/api/v1/diagnostics/{diag_id}",
            json={"summary": "Mise \u00e0 jour du r\u00e9sum\u00e9", "laboratory": "EMPA"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["summary"] == "Mise \u00e0 jour du r\u00e9sum\u00e9"

    async def test_update_sample(self, client, admin_user, auth_headers, sample_building):
        dr = await _create_diagnostic(client, auth_headers, sample_building.id)
        diag_id = dr.json()["id"]
        sr = await _create_sample(client, auth_headers, diag_id)
        sample_id = sr.json()["id"]
        r = await client.put(
            f"/api/v1/samples/{sample_id}",
            json={"concentration": 99.9, "notes": "Updated"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["concentration"] == pytest.approx(99.9)

    async def test_delete_sample(self, client, admin_user, auth_headers, sample_building):
        dr = await _create_diagnostic(client, auth_headers, sample_building.id)
        diag_id = dr.json()["id"]
        sr = await _create_sample(client, auth_headers, diag_id)
        sample_id = sr.json()["id"]
        r = await client.delete(f"/api/v1/samples/{sample_id}", headers=auth_headers)
        assert r.status_code == 204

    async def test_validate_diagnostic(self, client, admin_user, auth_headers, sample_building):
        dr = await _create_diagnostic(client, auth_headers, sample_building.id)
        diag_id = dr.json()["id"]
        r = await client.patch(
            f"/api/v1/diagnostics/{diag_id}/validate",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "validated"

    async def test_update_nonexistent_building(self, client, admin_user, auth_headers):
        fake_id = str(uuid.uuid4())
        r = await client.put(
            f"/api/v1/buildings/{fake_id}",
            json={"address": "Nowhere"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    async def test_delete_nonexistent_building(self, client, admin_user, auth_headers):
        fake_id = str(uuid.uuid4())
        r = await client.delete(f"/api/v1/buildings/{fake_id}", headers=auth_headers)
        assert r.status_code == 404


# ===================================================================
# 13. BUILDING FILTERS & SEARCH
# ===================================================================


class TestBuildingFilters:
    """Test building list filtering."""

    async def test_filter_by_building_type(self, client, admin_user, auth_headers, sample_building):
        r = await client.get(
            "/api/v1/buildings",
            params={"building_type": "residential"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        items = r.json().get("items", [])
        for item in items:
            assert item["building_type"] == "residential"

    async def test_filter_by_year_range(self, client, admin_user, auth_headers, sample_building):
        r = await client.get(
            "/api/v1/buildings",
            params={"year_from": 1960, "year_to": 1970},
            headers=auth_headers,
        )
        assert r.status_code == 200

    async def test_search_buildings(self, client, admin_user, auth_headers, sample_building):
        r = await client.get(
            "/api/v1/buildings",
            params={"search": "Test"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    async def test_pagination_params(self, client, admin_user, auth_headers, sample_building):
        r = await client.get(
            "/api/v1/buildings",
            params={"page": 1, "size": 5},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["size"] == 5
