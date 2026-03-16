"""Tests for the Meilisearch search service and API."""

import uuid
from unittest.mock import MagicMock, patch

from app.services import search_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client():
    """Return a MagicMock that behaves like meilisearch.Client."""
    client = MagicMock()
    index_mock = MagicMock()
    index_mock.search.return_value = {"hits": []}
    index_mock.add_documents.return_value = None
    index_mock.delete_document.return_value = None
    client.index.return_value = index_mock
    client.create_index.return_value = None
    return client


def _fake_building():
    """Return a fake building-like object."""
    b = MagicMock()
    b.id = uuid.uuid4()
    b.address = "Rue du Test 42"
    b.city = "Lausanne"
    b.postal_code = "1000"
    b.egid = 12345
    b.building_type = "residential"
    b.construction_year = 1970
    b.status = "active"
    b.risk_scores = None
    return b


def _fake_diagnostic():
    """Return a fake diagnostic-like object."""
    d = MagicMock()
    d.id = uuid.uuid4()
    d.building_id = uuid.uuid4()
    d.diagnostic_type = "asbestos"
    d.status = "completed"
    d.date_inspection = None
    building = MagicMock()
    building.address = "Rue du Test 42"
    d.building = building
    diagnostician = MagicMock()
    diagnostician.first_name = "Jean"
    diagnostician.last_name = "Muller"
    d.diagnostician = diagnostician
    sample = MagicMock()
    sample.pollutant_type = "asbestos"
    d.samples = [sample]
    return d


def _fake_document():
    """Return a fake document-like object."""
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.building_id = uuid.uuid4()
    doc.file_name = "report.pdf"
    doc.document_type = "diagnostic_report"
    doc.description = "Asbestos diagnostic report"
    building = MagicMock()
    building.address = "Rue du Test 42"
    doc.building = building
    return doc


# ---------------------------------------------------------------------------
# Unit tests — search_service functions
# ---------------------------------------------------------------------------


class TestBuildingToDoc:
    def test_converts_building_fields(self):
        b = _fake_building()
        doc = search_service._building_to_doc(b)
        assert doc["id"] == str(b.id)
        assert doc["address"] == "Rue du Test 42"
        assert doc["city"] == "Lausanne"
        assert doc["egid"] == "12345"
        assert doc["construction_year"] == 1970

    def test_handles_none_egid(self):
        b = _fake_building()
        b.egid = None
        doc = search_service._building_to_doc(b)
        assert doc["egid"] is None


class TestDiagnosticToDoc:
    def test_converts_diagnostic_fields(self):
        d = _fake_diagnostic()
        doc = search_service._diagnostic_to_doc(d)
        assert doc["id"] == str(d.id)
        assert doc["diagnostic_type"] == "asbestos"
        assert doc["diagnostician_name"] == "Jean Muller"
        assert "asbestos" in doc["pollutants_found"]

    def test_handles_no_diagnostician(self):
        d = _fake_diagnostic()
        d.diagnostician = None
        doc = search_service._diagnostic_to_doc(d)
        assert doc["diagnostician_name"] is None


class TestDocumentToDoc:
    def test_converts_document_fields(self):
        doc_obj = _fake_document()
        doc = search_service._document_to_doc(doc_obj)
        assert doc["id"] == str(doc_obj.id)
        assert doc["title"] == "Asbestos diagnostic report"
        assert doc["file_name"] == "report.pdf"

    def test_falls_back_to_filename_when_no_description(self):
        doc_obj = _fake_document()
        doc_obj.description = None
        doc = search_service._document_to_doc(doc_obj)
        assert doc["title"] == "report.pdf"


class TestIndexOperations:
    @patch("app.services.search_service._get_client")
    def test_index_building_calls_add_documents(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        b = _fake_building()
        search_service.index_building(b)
        client.index.assert_called_with("buildings")
        client.index("buildings").add_documents.assert_called_once()

    @patch("app.services.search_service._get_client")
    def test_index_building_noop_when_disabled(self, mock_get_client):
        mock_get_client.return_value = None
        b = _fake_building()
        # Should not raise
        search_service.index_building(b)

    @patch("app.services.search_service._get_client")
    def test_index_building_handles_error(self, mock_get_client):
        client = _mock_client()
        client.index.side_effect = Exception("Connection refused")
        mock_get_client.return_value = client
        b = _fake_building()
        # Should not raise
        search_service.index_building(b)

    @patch("app.services.search_service._get_client")
    def test_delete_building_calls_delete_document(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        search_service.delete_building("some-id")
        client.index("buildings").delete_document.assert_called_once_with("some-id")

    @patch("app.services.search_service._get_client")
    def test_index_diagnostic(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        d = _fake_diagnostic()
        search_service.index_diagnostic(d)
        client.index.assert_called_with("diagnostics")

    @patch("app.services.search_service._get_client")
    def test_index_document(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        doc = _fake_document()
        search_service.index_document(doc)
        client.index.assert_called_with("documents")


class TestSearchAll:
    @patch("app.services.search_service._get_client")
    def test_returns_empty_when_disabled(self, mock_get_client):
        mock_get_client.return_value = None
        result = search_service.search_all("test")
        assert result["query"] == "test"
        assert result["results"] == []
        assert result["total"] == 0

    @patch("app.services.search_service._get_client")
    def test_searches_all_indexes(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        bid = str(uuid.uuid4())
        client.index("buildings").search.return_value = {
            "hits": [
                {"id": bid, "address": "Rue du Test", "postal_code": "1000", "city": "Lausanne", "_rankingScore": 0.9}
            ]
        }
        client.index("diagnostics").search.return_value = {"hits": []}
        client.index("documents").search.return_value = {"hits": []}

        # Make index() return different mocks per index name
        indexes = {}
        for name in ("buildings", "diagnostics", "documents"):
            idx = MagicMock()
            idx.search.return_value = {"hits": []}
            indexes[name] = idx
        indexes["buildings"].search.return_value = {
            "hits": [
                {"id": bid, "address": "Rue du Test", "postal_code": "1000", "city": "Lausanne", "_rankingScore": 0.9}
            ]
        }
        client.index.side_effect = lambda name: indexes.get(name, MagicMock())

        result = search_service.search_all("test")
        assert result["total"] == 1
        assert result["results"][0]["index"] == "buildings"
        assert result["results"][0]["id"] == bid
        assert result["results"][0]["url"] == f"/buildings/{bid}"

    @patch("app.services.search_service._get_client")
    def test_search_with_type_filter(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        did = str(uuid.uuid4())
        idx = MagicMock()
        idx.search.return_value = {
            "hits": [
                {
                    "id": did,
                    "diagnostic_type": "asbestos",
                    "building_address": "Rue Test",
                    "diagnostician_name": "Jean",
                    "status": "completed",
                    "_rankingScore": 0.8,
                }
            ]
        }
        client.index.side_effect = lambda name: idx if name == "diagnostics" else MagicMock()

        result = search_service.search_all("asbestos", index_filter="diagnostics")
        assert result["total"] == 1
        assert result["results"][0]["index"] == "diagnostics"

    @patch("app.services.search_service._get_client")
    def test_search_limits_results(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        hits = [
            {"id": str(uuid.uuid4()), "address": f"Addr {i}", "postal_code": "1000", "city": "X", "_rankingScore": 0.5}
            for i in range(10)
        ]
        idx = MagicMock()
        idx.search.return_value = {"hits": hits}
        client.index.side_effect = lambda name: idx

        result = search_service.search_all("test", limit=3)
        assert len(result["results"]) <= 3

    @patch("app.services.search_service._get_client")
    def test_search_handles_index_error_gracefully(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        idx = MagicMock()
        idx.search.side_effect = Exception("Index not found")
        client.index.side_effect = lambda name: idx

        result = search_service.search_all("test")
        assert result["results"] == []
        assert result["total"] == 0


class TestInitIndexes:
    @patch("app.services.search_service._get_client")
    def test_creates_all_indexes(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client
        search_service.init_indexes()
        assert client.create_index.call_count == 3

    @patch("app.services.search_service._get_client")
    def test_noop_when_disabled(self, mock_get_client):
        mock_get_client.return_value = None
        # Should not raise
        search_service.init_indexes()


class TestHitToResult:
    def test_building_hit(self):
        hit = {"id": "abc", "address": "Rue Test 1", "postal_code": "1000", "city": "Lausanne", "_rankingScore": 0.95}
        result = search_service._hit_to_result("buildings", hit)
        assert result["url"] == "/buildings/abc"
        assert result["title"] == "Rue Test 1"
        assert result["subtitle"] == "1000 Lausanne"
        assert result["score"] == 0.95

    def test_diagnostic_hit(self):
        hit = {
            "id": "def",
            "diagnostic_type": "pcb",
            "building_address": "Rue Test 2",
            "diagnostician_name": "Max",
            "status": "draft",
            "_rankingScore": 0.8,
        }
        result = search_service._hit_to_result("diagnostics", hit)
        assert result["url"] == "/diagnostics/def"
        assert "pcb" in result["title"]

    def test_document_hit(self):
        hit = {
            "id": "ghi",
            "title": "Report Q3",
            "file_name": "report.pdf",
            "building_address": "Rue Test 3",
            "document_type": "report",
            "_rankingScore": 0.7,
        }
        result = search_service._hit_to_result("documents", hit)
        assert result["url"] == "/documents/ghi/download"
        assert result["title"] == "Report Q3"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestSearchAPI:
    async def test_search_requires_auth(self, client):
        response = await client.get("/api/v1/search?q=test")
        assert response.status_code == 403

    @patch("app.services.search_service.search_all")
    async def test_search_returns_results(self, mock_search_all, client, admin_user, auth_headers):
        mock_search_all.return_value = {
            "query": "lausanne",
            "results": [
                {
                    "index": "buildings",
                    "id": str(uuid.uuid4()),
                    "title": "Rue du Test 42",
                    "subtitle": "1000 Lausanne",
                    "url": "/buildings/abc",
                    "score": 0.95,
                }
            ],
            "total": 1,
        }
        response = await client.get("/api/v1/search?q=lausanne", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "lausanne"
        assert data["total"] == 1
        assert data["results"][0]["index"] == "buildings"

    @patch("app.services.search_service.search_all")
    async def test_search_with_type_filter(self, mock_search_all, client, admin_user, auth_headers):
        mock_search_all.return_value = {"query": "report", "results": [], "total": 0}
        response = await client.get("/api/v1/search?q=report&type=documents", headers=auth_headers)
        assert response.status_code == 200
        mock_search_all.assert_called_once_with(query="report", index_filter="documents", limit=20)

    @patch("app.services.search_service.search_all")
    async def test_search_with_limit(self, mock_search_all, client, admin_user, auth_headers):
        mock_search_all.return_value = {"query": "test", "results": [], "total": 0}
        response = await client.get("/api/v1/search?q=test&limit=5", headers=auth_headers)
        assert response.status_code == 200
        mock_search_all.assert_called_once_with(query="test", index_filter=None, limit=5)

    async def test_search_empty_query_rejected(self, client, admin_user, auth_headers):
        response = await client.get("/api/v1/search?q=", headers=auth_headers)
        assert response.status_code == 422
