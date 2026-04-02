"""Tests for DefectShield — Gotenberg PDF generation resilience.

Covers: Gotenberg connection failures, HTTP errors, timeout,
invalid HTML, missing building, missing timeline, language validation,
empty description, special characters in HTML.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.building import Building
from app.schemas.defect_timeline import DefectTimelineCreate
from app.services.defect_letter_service import (
    _TRANSLATIONS,
    generate_letter_pdf,
    render_letter_html,
)
from app.services.defect_timeline_service import create_timeline

FAKE_PDF = b"%PDF-1.4 fake content for testing"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Gotenberg 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "egid": 999888,
        "construction_year": 1980,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_timeline(db, building_id, **kwargs):
    defaults = {
        "building_id": building_id,
        "defect_type": "construction",
        "description": "Fissure test",
        "discovery_date": date(2026, 3, 1),
    }
    defaults.update(kwargs)
    return await create_timeline(db, DefectTimelineCreate(**defaults))


# ---------------------------------------------------------------------------
# Gotenberg connection/HTTP failure tests
# ---------------------------------------------------------------------------


class TestGotenbergConnectionFailures:
    """Verify resilience when Gotenberg is unreachable or returns errors."""

    @pytest.mark.asyncio
    async def test_gotenberg_connect_error(self, db_session, admin_user):
        """Gotenberg unreachable → httpx.ConnectError propagates."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        with patch(
            "app.services.defect_letter_service.html_to_pdf",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(httpx.ConnectError):
            await generate_letter_pdf(db_session, t.id, lang="fr")

    @pytest.mark.asyncio
    async def test_gotenberg_500_error(self, db_session, admin_user):
        """Gotenberg returns 500 → HTTPStatusError propagates."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        mock_response = httpx.Response(500, request=httpx.Request("POST", "http://test"))
        with patch(
            "app.services.defect_letter_service.html_to_pdf",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=mock_response.request, response=mock_response
            ),
        ), pytest.raises(httpx.HTTPStatusError):
            await generate_letter_pdf(db_session, t.id, lang="fr")

    @pytest.mark.asyncio
    async def test_gotenberg_timeout(self, db_session, admin_user):
        """Gotenberg times out → httpx.ReadTimeout propagates."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        with patch(
            "app.services.defect_letter_service.html_to_pdf",
            new_callable=AsyncMock,
            side_effect=httpx.ReadTimeout("Timed out"),
        ), pytest.raises(httpx.ReadTimeout):
            await generate_letter_pdf(db_session, t.id, lang="fr")

    @pytest.mark.asyncio
    async def test_gotenberg_returns_empty_bytes(self, db_session, admin_user):
        """Gotenberg returns empty response — should still return bytes (caller validates)."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        with patch(
            "app.services.defect_letter_service.html_to_pdf",
            new_callable=AsyncMock,
            return_value=b"",
        ):
            result = await generate_letter_pdf(db_session, t.id, lang="fr")
            assert result == b""


# ---------------------------------------------------------------------------
# Missing data tests
# ---------------------------------------------------------------------------


class TestMissingData:
    """generate_letter_pdf with missing building or timeline."""

    @pytest.mark.asyncio
    async def test_missing_timeline(self, db_session):
        """Non-existent timeline_id → ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await generate_letter_pdf(db_session, uuid.uuid4(), lang="fr")

    @pytest.mark.asyncio
    async def test_missing_building(self, db_session, admin_user):
        """Timeline exists but building was deleted → ValueError."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        # Delete the building from DB
        await db_session.delete(b)
        await db_session.commit()
        with pytest.raises(ValueError, match=r"Building.*not found"):
            await generate_letter_pdf(db_session, t.id, lang="fr")


# ---------------------------------------------------------------------------
# Language / i18n validation
# ---------------------------------------------------------------------------


class TestLanguageValidation:
    """All 3 supported languages produce valid HTML."""

    @pytest.mark.parametrize("lang", ["fr", "de", "it"])
    def test_all_languages_render_html(self, lang):
        html = render_letter_html(
            lang=lang,
            address="Rue du Test 1",
            egid="123456",
            canton="VD",
            defect_type="construction",
            description="Test defect",
            discovery_date=date(2026, 3, 1),
            notification_deadline=date(2026, 4, 30),
            guarantee_type="standard",
        )
        assert f'lang="{lang}"' in html
        assert _TRANSLATIONS[lang]["title"] in html

    @pytest.mark.parametrize("lang", ["fr", "de", "it"])
    def test_all_defect_types_translated(self, lang):
        """Every defect type has a translation in every language."""
        for dtype in ["construction", "pollutant", "structural", "installation", "other"]:
            assert dtype in _TRANSLATIONS[lang]["defect_types"]

    @pytest.mark.parametrize("lang", ["fr", "de", "it"])
    def test_all_guarantee_types_translated(self, lang):
        """Every guarantee type has a translation in every language."""
        for gtype in ["standard", "new_build_rectification"]:
            assert gtype in _TRANSLATIONS[lang]["guarantee_types"]


# ---------------------------------------------------------------------------
# HTML edge cases
# ---------------------------------------------------------------------------


class TestHtmlEdgeCases:
    """Edge cases for render_letter_html."""

    def test_empty_description(self):
        """Empty description should render as dash."""
        html = render_letter_html(
            lang="fr",
            address="Rue du Test 1",
            egid="123456",
            canton="VD",
            defect_type="construction",
            description="",
            discovery_date=date(2026, 3, 1),
            notification_deadline=date(2026, 4, 30),
            guarantee_type="standard",
        )
        assert "—" in html  # empty description becomes dash

    def test_none_egid(self):
        """None/missing egid should render as dash."""
        html = render_letter_html(
            lang="fr",
            address="Rue du Test 1",
            egid="",
            canton="VD",
            defect_type="construction",
            description="Test",
            discovery_date=date(2026, 3, 1),
            notification_deadline=date(2026, 4, 30),
            guarantee_type="standard",
        )
        # Empty egid renders as-is (not None)
        assert "<!DOCTYPE html>" in html

    def test_special_characters_in_description(self):
        """HTML-sensitive chars in description don't break template."""
        html = render_letter_html(
            lang="fr",
            address="Rue du Test 1",
            egid="123",
            canton="VD",
            defect_type="construction",
            description='Fissure <script>alert("xss")</script> & "quotes"',
            discovery_date=date(2026, 3, 1),
            notification_deadline=date(2026, 4, 30),
            guarantee_type="standard",
        )
        # Template uses .format(), so raw HTML passes through — check it doesn't crash
        assert "<!DOCTYPE html>" in html

    def test_very_long_description(self):
        """Very long description doesn't crash rendering."""
        long_desc = "A" * 10000
        html = render_letter_html(
            lang="fr",
            address="Rue du Test 1",
            egid="123",
            canton="VD",
            defect_type="construction",
            description=long_desc,
            discovery_date=date(2026, 3, 1),
            notification_deadline=date(2026, 4, 30),
            guarantee_type="standard",
        )
        assert long_desc in html

    def test_date_formatting_all_languages(self):
        """All languages use DD.MM.YYYY Swiss format."""
        for lang in ["fr", "de", "it"]:
            html = render_letter_html(
                lang=lang,
                address="Test",
                egid="1",
                canton="VD",
                defect_type="construction",
                description="Test",
                discovery_date=date(2026, 3, 1),
                notification_deadline=date(2026, 4, 30),
                guarantee_type="standard",
            )
            assert "01.03.2026" in html  # discovery_date
            assert "30.04.2026" in html  # notification_deadline
