import uuid

from app.api.change_signals import router as change_signals_router
from app.main import app

app.include_router(change_signals_router, prefix="/api/v1")

SIGNAL_PAYLOAD = {
    "signal_type": "regulation_change",
    "severity": "warning",
    "title": "New asbestos threshold effective 2026-01-01",
    "description": "ORRChim Annex 2.15 updated thresholds",
    "source": "regulation_update",
}


class TestPortfolioChangeSignals:
    async def test_portfolio_returns_signals_from_multiple_buildings(
        self, client, admin_user, auth_headers, sample_building, db_session
    ):
        """Portfolio endpoint returns signals from multiple buildings."""
        # Create a second building
        from app.models.building import Building

        building2 = Building(
            id=uuid.uuid4(),
            address="Avenue Test 2",
            postal_code="1200",
            city="Geneve",
            canton="GE",
            construction_year=1970,
            building_type="commercial",
            created_by=admin_user.id,
            status="active",
        )
        db_session.add(building2)
        await db_session.commit()
        await db_session.refresh(building2)

        # Create signals on both buildings
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{building2.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "title": "PCB threshold update"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/portfolio/change-signals",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        # Signals from different buildings
        building_ids = {item["building_id"] for item in data["items"]}
        assert len(building_ids) == 2

    async def test_portfolio_filter_by_severity(self, client, admin_user, auth_headers, sample_building):
        """Filter by severity works."""
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "severity": "critical", "title": "Critical signal"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "severity": "info", "title": "Info signal"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/portfolio/change-signals",
            params={"severity": "critical"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "critical"

    async def test_portfolio_filter_by_status(self, client, admin_user, auth_headers, sample_building):
        """Filter by status works."""
        # Create a signal (default status=active)
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json=SIGNAL_PAYLOAD,
            headers=auth_headers,
        )
        signal_id = create_resp.json()["id"]

        # Acknowledge it (change status)
        await client.put(
            f"/api/v1/buildings/{sample_building.id}/change-signals/{signal_id}",
            json={"status": "acknowledged"},
            headers=auth_headers,
        )

        # Create another active signal
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/change-signals",
            json={**SIGNAL_PAYLOAD, "title": "Still active"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/portfolio/change-signals",
            params={"status": "active"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "active"

    async def test_portfolio_pagination(self, client, admin_user, auth_headers, sample_building):
        """Pagination works."""
        # Create 3 signals
        for i in range(3):
            await client.post(
                f"/api/v1/buildings/{sample_building.id}/change-signals",
                json={**SIGNAL_PAYLOAD, "title": f"Signal {i}"},
                headers=auth_headers,
            )

        # Request page 1, size 2
        response = await client.get(
            "/api/v1/portfolio/change-signals",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 2

        # Request page 2
        response = await client.get(
            "/api/v1/portfolio/change-signals",
            params={"page": 2, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    async def test_portfolio_empty_result(self, client, admin_user, auth_headers):
        """Empty result for no signals."""
        response = await client.get(
            "/api/v1/portfolio/change-signals",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pages"] == 0
