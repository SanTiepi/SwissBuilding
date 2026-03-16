"""Tests for the Decision Replay service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.user import User
from app.schemas.decision_replay import DecisionRecordCreate, DecisionRecordUpdate
from app.services.decision_replay_service import (
    get_decision_context,
    get_decision_detail,
    get_decision_impact,
    get_decision_patterns,
    get_decision_timeline,
    record_decision,
    search_decisions,
    update_decision_outcome,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db, role="admin", first_name="Admin", last_name="Test", email=None):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=email or f"{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building(db, user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


def _make_create_data(building_id, **kwargs):
    defaults = {
        "building_id": building_id,
        "decision_type": "diagnostic_ordered",
        "title": "Order full asbestos diagnostic",
        "rationale": "Building constructed in 1965, high likelihood of asbestos",
        "entity_type": "diagnostic",
    }
    defaults.update(kwargs)
    return DecisionRecordCreate(**defaults)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestRecordDecision:
    async def test_record_decision_basic(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        data = _make_create_data(building.id)

        record = await record_decision(db_session, user.id, data)

        assert record.id is not None
        assert record.building_id == building.id
        assert record.decision_type == "diagnostic_ordered"
        assert record.decided_by == user.id
        assert record.rationale == "Building constructed in 1965, high likelihood of asbestos"

    async def test_record_decision_auto_context_capture(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        data = _make_create_data(building.id)

        record = await record_decision(db_session, user.id, data)

        assert record.context_snapshot is not None
        assert "risk_level" in record.context_snapshot
        assert "open_actions_count" in record.context_snapshot

    async def test_record_decision_custom_context(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        custom_ctx = {"risk_level": "high", "grade": "C", "trust_score": 0.6}
        data = _make_create_data(building.id, context_snapshot=custom_ctx)

        record = await record_decision(db_session, user.id, data)

        assert record.context_snapshot == custom_ctx

    async def test_record_decision_with_entity_id(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        entity_id = uuid.uuid4()
        data = _make_create_data(building.id, entity_type="intervention", entity_id=entity_id)

        record = await record_decision(db_session, user.id, data)

        assert record.entity_type == "intervention"
        assert record.entity_id == entity_id


class TestGetDecisionTimeline:
    async def test_timeline_chronological_order(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        for i in range(3):
            data = _make_create_data(building.id, title=f"Decision {i}")
            await record_decision(db_session, user.id, data)

        timeline = await get_decision_timeline(db_session, building.id)

        assert timeline.total_decisions == 3
        assert len(timeline.decisions) == 3
        # Desc order
        for i in range(len(timeline.decisions) - 1):
            assert timeline.decisions[i].decided_at >= timeline.decisions[i + 1].decided_at

    async def test_timeline_filter_by_type(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        await record_decision(db_session, user.id, _make_create_data(building.id, decision_type="diagnostic_ordered"))
        await record_decision(
            db_session, user.id, _make_create_data(building.id, decision_type="intervention_approved")
        )

        timeline = await get_decision_timeline(db_session, building.id, decision_type="diagnostic_ordered")

        assert timeline.total_decisions == 1
        assert timeline.decisions[0].decision_type == "diagnostic_ordered"

    async def test_timeline_empty_building(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        timeline = await get_decision_timeline(db_session, building.id)

        assert timeline.total_decisions == 0
        assert timeline.decisions == []


class TestGetDecisionDetail:
    async def test_detail_with_decided_by_name(self, db_session):
        user = await _create_user(db_session, first_name="Jean", last_name="Muller")
        building = await _create_building(db_session, user)
        data = _make_create_data(building.id)
        record = await record_decision(db_session, user.id, data)

        detail = await get_decision_detail(db_session, record.id)

        assert detail is not None
        assert detail.decided_by_name == "Jean Muller"

    async def test_detail_not_found(self, db_session):
        detail = await get_decision_detail(db_session, uuid.uuid4())
        assert detail is None


class TestUpdateDecisionOutcome:
    async def test_update_outcome(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        record = await record_decision(db_session, user.id, _make_create_data(building.id))

        update = DecisionRecordUpdate(outcome="positive", outcome_notes="Asbestos found, remediation planned")
        updated = await update_decision_outcome(db_session, record.id, update)

        assert updated is not None
        assert updated.outcome == "positive"
        assert updated.outcome_notes == "Asbestos found, remediation planned"

    async def test_update_rationale(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        record = await record_decision(db_session, user.id, _make_create_data(building.id))

        update = DecisionRecordUpdate(rationale="Updated rationale after review")
        updated = await update_decision_outcome(db_session, record.id, update)

        assert updated.rationale == "Updated rationale after review"

    async def test_update_not_found(self, db_session):
        update = DecisionRecordUpdate(outcome="negative")
        result = await update_decision_outcome(db_session, uuid.uuid4(), update)
        assert result is None


class TestDecisionPatterns:
    async def test_patterns_analysis(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        # Create multiple decisions of same type
        for _ in range(3):
            data = _make_create_data(building.id, decision_type="diagnostic_ordered")
            await record_decision(db_session, user.id, data)

        data = _make_create_data(building.id, decision_type="intervention_approved")
        record = await record_decision(db_session, user.id, data)
        record.outcome = "positive"
        await db_session.commit()

        patterns = await get_decision_patterns(db_session, building.id)

        assert len(patterns) == 2
        type_map = {p.decision_type: p for p in patterns}
        assert type_map["diagnostic_ordered"].count == 3
        assert type_map["intervention_approved"].count == 1

    async def test_patterns_empty(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        patterns = await get_decision_patterns(db_session, building.id)
        assert patterns == []


class TestDecisionContext:
    async def test_context_comparison(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        data = _make_create_data(building.id)
        record = await record_decision(db_session, user.id, data)

        ctx = await get_decision_context(db_session, record.id)

        assert ctx is not None
        assert ctx.building_id == building.id
        assert "risk_level" in ctx.at_decision_time
        assert "risk_level" in ctx.current_state
        assert isinstance(ctx.state_changed, bool)

    async def test_context_not_found(self, db_session):
        ctx = await get_decision_context(db_session, uuid.uuid4())
        assert ctx is None


class TestDecisionImpact:
    async def test_impact_analysis(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)
        data = _make_create_data(building.id)
        record = await record_decision(db_session, user.id, data)

        impacts = await get_decision_impact(db_session, building.id)

        assert len(impacts) == 1
        assert impacts[0].decision_id == record.id
        assert impacts[0].days_since_decision >= 0
        assert impacts[0].before_state is not None


class TestSearchDecisions:
    async def test_search_by_type(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        await record_decision(db_session, user.id, _make_create_data(building.id, decision_type="diagnostic_ordered"))
        await record_decision(db_session, user.id, _make_create_data(building.id, decision_type="risk_accepted"))

        results = await search_decisions(db_session, decision_type="risk_accepted")

        assert len(results) == 1
        assert results[0].decision_type == "risk_accepted"

    async def test_search_by_user(self, db_session):
        user1 = await _create_user(db_session, first_name="Alice")
        user2 = await _create_user(db_session, first_name="Bob")
        building = await _create_building(db_session, user1)

        await record_decision(db_session, user1.id, _make_create_data(building.id))
        await record_decision(db_session, user2.id, _make_create_data(building.id))

        results = await search_decisions(db_session, decided_by=user1.id)

        assert len(results) == 1
        assert results[0].decided_by == user1.id

    async def test_search_by_date_range(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        await record_decision(db_session, user.id, _make_create_data(building.id))

        # Search with future date_from should return nothing
        future = datetime.now(UTC) + timedelta(days=1)
        results = await search_decisions(db_session, date_from=future)
        assert len(results) == 0

    async def test_search_by_building(self, db_session):
        user = await _create_user(db_session)
        b1 = await _create_building(db_session, user)
        b2 = await _create_building(db_session, user)

        await record_decision(db_session, user.id, _make_create_data(b1.id))
        await record_decision(db_session, user.id, _make_create_data(b2.id))

        results = await search_decisions(db_session, building_id=b1.id)

        assert len(results) == 1
        assert results[0].building_id == b1.id


class TestMultipleDecisionTypes:
    async def test_multiple_types_same_building(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user)

        types = [
            "diagnostic_ordered",
            "intervention_approved",
            "risk_accepted",
            "action_deferred",
            "grade_override",
        ]
        for dt in types:
            await record_decision(db_session, user.id, _make_create_data(building.id, decision_type=dt))

        timeline = await get_decision_timeline(db_session, building.id)
        assert timeline.total_decisions == 5
        result_types = {d.decision_type for d in timeline.decisions}
        assert result_types == set(types)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestDecisionReplayAPI:
    async def test_create_decision_api(self, client, auth_headers, sample_building):
        payload = {
            "building_id": str(sample_building.id),
            "decision_type": "diagnostic_ordered",
            "title": "Order PCB diagnostic",
            "rationale": "PCB suspected due to 1965 construction year",
            "entity_type": "diagnostic",
        }
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/decisions",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["decision_type"] == "diagnostic_ordered"
        assert data["decided_by_name"] is not None

    async def test_list_decisions_api(self, client, auth_headers, sample_building):
        # Create a decision first
        payload = {
            "building_id": str(sample_building.id),
            "decision_type": "diagnostic_ordered",
            "title": "Order diagnostic",
            "rationale": "Needed",
            "entity_type": "diagnostic",
        }
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/decisions",
            json=payload,
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/decisions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_decisions"] == 1
        assert len(data["decisions"]) == 1

    async def test_get_decision_detail_api(self, client, auth_headers, sample_building):
        payload = {
            "building_id": str(sample_building.id),
            "decision_type": "risk_accepted",
            "title": "Accept low risk",
            "rationale": "Risk is low based on lab results",
            "entity_type": "building",
        }
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/decisions",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/decisions/{decision_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == decision_id

    async def test_update_outcome_api(self, client, auth_headers, sample_building):
        payload = {
            "building_id": str(sample_building.id),
            "decision_type": "intervention_approved",
            "title": "Approve intervention",
            "rationale": "Urgent remediation needed",
            "entity_type": "intervention",
        }
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/decisions",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/decisions/{decision_id}/outcome",
            json={"outcome": "positive", "outcome_notes": "Intervention successful"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["outcome"] == "positive"

    async def test_patterns_api(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/decisions/patterns",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_404_missing_building(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/decisions",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_404_missing_decision(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/decisions/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_search_api(self, client, auth_headers, sample_building):
        resp = await client.get(
            "/api/v1/decisions/search",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_context_api(self, client, auth_headers, sample_building):
        payload = {
            "building_id": str(sample_building.id),
            "decision_type": "diagnostic_ordered",
            "title": "Test context",
            "rationale": "Testing",
            "entity_type": "building",
        }
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/decisions",
            json=payload,
            headers=auth_headers,
        )
        decision_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/decisions/{decision_id}/context",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "at_decision_time" in data
        assert "current_state" in data

    async def test_impact_api(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/decisions/impact",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
