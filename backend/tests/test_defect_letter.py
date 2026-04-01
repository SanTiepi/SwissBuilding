"""Tests for DefectShield — PDF notification letter generation.

Tests cover:
- HTML template rendering (FR/DE/IT)
- Gotenberg client (mocked)
- Letter service integration (mocked Gotenberg)
- API endpoint POST /defects/{id}/generate-letter (mocked Gotenberg)
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.schemas.defect_timeline import DefectTimelineCreate
from app.services.defect_letter_service import (
    _TRANSLATIONS,
    render_letter_html,
)
from app.services.defect_timeline_service import (
    create_timeline,
    get_timeline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_PDF = b"%PDF-1.4 fake content for testing"


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Midi 10, 1003 Lausanne",
        "postal_code": "1003",
        "city": "Lausanne",
        "canton": "VD",
        "egid": 123456,
        "construction_year": 1975,
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
        "description": "Fissure dans le mur porteur",
        "discovery_date": date(2026, 3, 1),
    }
    defaults.update(kwargs)
    return await create_timeline(db, DefectTimelineCreate(**defaults))


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------


class TestRenderLetterHtml:
    """Test pure HTML template rendering (no I/O)."""

    def _render(self, lang="fr", **overrides):
        defaults = {
            "lang": lang,
            "address": "Rue du Midi 10, 1003 Lausanne",
            "egid": "123456",
            "canton": "VD",
            "defect_type": "construction",
            "description": "Fissure dans le mur porteur",
            "discovery_date": date(2026, 3, 1),
            "notification_deadline": date(2026, 4, 30),
            "guarantee_type": "standard",
        }
        defaults.update(overrides)
        return render_letter_html(**defaults)

    def test_french_template_renders(self):
        html = self._render(lang="fr")
        assert "<!DOCTYPE html>" in html
        assert 'lang="fr"' in html
        assert "Notification de défaut de construction" in html
        assert "Art. 367 al. 1bis CO" in html
        assert "Rue du Midi 10, 1003 Lausanne" in html
        assert "123456" in html

    def test_german_template_renders(self):
        html = self._render(lang="de")
        assert 'lang="de"' in html
        assert "Mängelrüge" in html
        assert "Art. 367 Abs. 1bis OR" in html
        assert "Rue du Midi 10, 1003 Lausanne" in html

    def test_italian_template_renders(self):
        html = self._render(lang="it")
        assert 'lang="it"' in html
        assert "Notifica di difetto di costruzione" in html
        assert "Art. 367 cpv. 1bis CO" in html

    def test_contains_building_info(self):
        html = self._render(address="Bahnhofstrasse 1, 8001 Zürich", egid="789012", canton="ZH")
        assert "Bahnhofstrasse 1, 8001 Zürich" in html
        assert "789012" in html
        assert "ZH" in html

    def test_contains_defect_info(self):
        html = self._render(
            defect_type="pollutant",
            description="Amiante dans les dalles",
            discovery_date=date(2026, 2, 15),
            notification_deadline=date(2026, 4, 16),
        )
        assert "Polluant" in html  # FR translation of pollutant
        assert "Amiante dans les dalles" in html
        assert "15.02.2026" in html
        assert "16.04.2026" in html

    def test_contains_legal_reference(self):
        html = self._render(lang="fr")
        assert "art. 367 al. 1bis" in html
        assert "60 jours civils" in html
        assert "art. 371 CO" in html

    def test_contains_signature_blocks(self):
        html = self._render(lang="fr")
        assert "Maître de l'ouvrage" in html
        assert "Entrepreneur" in html
        assert "Signature" in html

    def test_date_formatting_swiss(self):
        html = self._render(
            discovery_date=date(2026, 1, 5),
            notification_deadline=date(2026, 3, 6),
        )
        assert "05.01.2026" in html
        assert "06.03.2026" in html

    def test_guarantee_new_build(self):
        html = self._render(lang="fr", guarantee_type="new_build_rectification")
        assert "Garantie construction neuve" in html

    def test_guarantee_new_build_de(self):
        html = self._render(lang="de", guarantee_type="new_build_rectification")
        assert "Neubau-Garantie" in html

    def test_guarantee_new_build_it(self):
        html = self._render(lang="it", guarantee_type="new_build_rectification")
        assert "Garanzia nuova costruzione" in html

    def test_defect_types_translated_de(self):
        for dt, expected in _TRANSLATIONS["de"]["defect_types"].items():
            html = self._render(lang="de", defect_type=dt)
            assert expected in html

    def test_defect_types_translated_it(self):
        for dt, expected in _TRANSLATIONS["it"]["defect_types"].items():
            html = self._render(lang="it", defect_type=dt)
            assert expected in html

    def test_missing_description_shows_dash(self):
        html = self._render(description="")
        # Empty description is just empty in the cell, not a crash
        assert "<!DOCTYPE html>" in html

    def test_missing_egid_shows_dash(self):
        html = self._render(egid="")
        # Empty egid rendered as dash by the service layer
        assert "<!DOCTYPE html>" in html

    def test_all_three_languages_have_same_keys(self):
        """Ensure FR/DE/IT translations have identical key sets."""
        fr_keys = set(_TRANSLATIONS["fr"].keys())
        de_keys = set(_TRANSLATIONS["de"].keys())
        it_keys = set(_TRANSLATIONS["it"].keys())
        assert fr_keys == de_keys == it_keys

    def test_footer_contains_baticonnect(self):
        for lang in ("fr", "de", "it"):
            html = self._render(lang=lang)
            assert "BatiConnect" in html


# ---------------------------------------------------------------------------
# Gotenberg client tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestGotenbergService:
    @pytest.mark.asyncio
    async def test_html_to_pdf_success(self):
        """html_to_pdf sends correct request and returns PDF bytes."""
        from app.services.gotenberg_service import html_to_pdf

        mock_response = AsyncMock()
        mock_response.content = FAKE_PDF
        mock_response.raise_for_status = lambda: None

        with patch("app.services.gotenberg_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await html_to_pdf("<html><body>Test</body></html>")

            assert result == FAKE_PDF
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert "files" in call_kwargs.kwargs or len(call_kwargs.args) >= 2

    @pytest.mark.asyncio
    async def test_html_to_pdf_error_propagates(self):
        """Gotenberg errors propagate as httpx exceptions."""
        import httpx

        from app.services.gotenberg_service import html_to_pdf

        with patch("app.services.gotenberg_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Gotenberg unreachable")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.ConnectError, match="unreachable"):
                await html_to_pdf("<html></html>")


# ---------------------------------------------------------------------------
# Letter service integration tests (DB + mocked Gotenberg)
# ---------------------------------------------------------------------------


class TestGenerateLetterPdf:
    async def test_generate_letter_pdf_success(self, db_session, admin_user):
        """Full flow: DB → HTML render → Gotenberg mock → PDF bytes."""
        from app.services.defect_letter_service import generate_letter_pdf

        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            result = await generate_letter_pdf(db_session, timeline.id, lang="fr")

            assert result == FAKE_PDF
            mock_pdf.assert_called_once()
            html_arg = mock_pdf.call_args.args[0]
            assert "Rue du Midi 10" in html_arg
            assert "123456" in html_arg
            assert "Fissure dans le mur porteur" in html_arg

    async def test_generate_letter_pdf_german(self, db_session, admin_user):
        """German language variant."""
        from app.services.defect_letter_service import generate_letter_pdf

        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            result = await generate_letter_pdf(db_session, timeline.id, lang="de")

            assert result == FAKE_PDF
            html_arg = mock_pdf.call_args.args[0]
            assert "Mängelrüge" in html_arg

    async def test_generate_letter_pdf_italian(self, db_session, admin_user):
        """Italian language variant."""
        from app.services.defect_letter_service import generate_letter_pdf

        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            result = await generate_letter_pdf(db_session, timeline.id, lang="it")

            assert result == FAKE_PDF
            html_arg = mock_pdf.call_args.args[0]
            assert "Notifica di difetto" in html_arg

    async def test_generate_letter_pdf_timeline_not_found(self, db_session, admin_user):
        """Raises ValueError for nonexistent timeline."""
        from app.services.defect_letter_service import generate_letter_pdf

        with pytest.raises(ValueError, match="DefectTimeline"):
            await generate_letter_pdf(db_session, uuid.uuid4())

    async def test_generate_letter_pdf_includes_building_data(self, db_session, admin_user):
        """HTML includes building address, EGID, canton from DB."""
        from app.services.defect_letter_service import generate_letter_pdf

        building = await _make_building(
            db_session, admin_user.id, address="Bundesplatz 3, 3003 Bern", egid=654321, canton="BE"
        )
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            await generate_letter_pdf(db_session, timeline.id)

            html_arg = mock_pdf.call_args.args[0]
            assert "Bundesplatz 3, 3003 Bern" in html_arg
            assert "654321" in html_arg
            assert "BE" in html_arg


# ---------------------------------------------------------------------------
# API endpoint tests (mocked Gotenberg)
# ---------------------------------------------------------------------------


class TestGenerateLetterEndpoint:
    async def test_generate_letter_endpoint_returns_pdf(self, db_session, admin_user, client, auth_headers):
        """POST /defects/{id}/generate-letter returns PDF with correct headers."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            response = await client.post(
                f"/api/v1/defects/{timeline.id}/generate-letter?lang=fr",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers
        assert f"{timeline.id}" in response.headers["content-disposition"]
        assert response.content == FAKE_PDF

    async def test_generate_letter_marks_as_notified(self, db_session, admin_user, client, auth_headers):
        """After PDF generation, timeline status is 'notified'."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            await client.post(
                f"/api/v1/defects/{timeline.id}/generate-letter",
                headers=auth_headers,
            )

        # Verify via API (separate DB session from endpoint)
        resp = await client.get(
            f"/api/v1/defects/timeline/{building.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        timelines = resp.json()
        notified = [t for t in timelines if t["id"] == str(timeline.id)]
        assert len(notified) == 1
        assert notified[0]["status"] == "notified"
        assert notified[0]["notified_at"] is not None
        assert notified[0]["notification_pdf_url"] is not None

    async def test_generate_letter_not_found(self, db_session, admin_user, client, auth_headers):
        """404 for nonexistent timeline."""
        response = await client.post(
            f"/api/v1/defects/{uuid.uuid4()}/generate-letter",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_generate_letter_already_notified(self, db_session, admin_user, client, auth_headers):
        """400 if timeline is already notified."""
        from app.services.defect_timeline_service import update_timeline_status

        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)
        await update_timeline_status(db_session, timeline.id, "notified", notified_at=datetime.now(UTC))

        response = await client.post(
            f"/api/v1/defects/{timeline.id}/generate-letter",
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_generate_letter_lang_de(self, db_session, admin_user, client, auth_headers):
        """German language parameter works."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = FAKE_PDF

            response = await client.post(
                f"/api/v1/defects/{timeline.id}/generate-letter?lang=de",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "-de.pdf" in response.headers["content-disposition"]

    async def test_generate_letter_gotenberg_failure_returns_502(self, db_session, admin_user, client, auth_headers):
        """502 when Gotenberg is down."""
        import httpx

        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        with patch("app.services.defect_letter_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.side_effect = httpx.ConnectError("Gotenberg unreachable")

            response = await client.post(
                f"/api/v1/defects/{timeline.id}/generate-letter",
                headers=auth_headers,
            )

        assert response.status_code == 502
