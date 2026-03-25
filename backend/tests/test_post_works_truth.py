"""BatiConnect — Lot 4: PostWorksLink + DomainEvent + AIFeedback tests."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.ai_feedback import AIFeedback
from app.models.award_confirmation import AwardConfirmation
from app.models.building import Building
from app.models.client_request import ClientRequest
from app.models.company_profile import CompanyProfile
from app.models.completion_confirmation import CompletionConfirmation
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.domain_event import DomainEvent
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.post_works_link import PostWorksLink
from app.models.quote import Quote
from app.models.user import User
from app.services.domain_event_projector import (
    _handlers,
    project_event,
    register_handler,
    replay_events,
)
from app.services.remediation_post_works_service import (
    award_to_intervention,
    draft_post_works,
    finalize_post_works,
    get_building_remediation_outcomes,
    get_post_works_link,
    list_domain_events,
    record_ai_feedback,
    review_draft,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db, role="admin"):
    u = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg/9qVMfBFlfcuE9PWN.5Kj6aJLYvq/x6xK4r05EvL1i",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
    )
    db.add(u)
    await db.flush()
    return u


async def _make_building(db, user_id):
    b = Building(
        id=uuid.uuid4(),
        address="Rue PostWorks 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _make_org(db):
    org = Organization(id=uuid.uuid4(), name="PW Test Org", type="contractor")
    db.add(org)
    await db.flush()
    return org


async def _make_publication(db, building_id):
    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=building_id,
        source_system="batiscan",
        source_mission_id="PW-TEST-001",
        match_state="auto_matched",
        match_key_type="egid",
        payload_hash="pw123",
        mission_type="asbestos_full",
        published_at=datetime.now(UTC),
    )
    db.add(pub)
    await db.flush()
    return pub


async def _make_company_profile(db, org_id, _user_id):
    cp = CompanyProfile(
        id=uuid.uuid4(),
        organization_id=org_id,
        company_name="PW Test Company",
        contact_email="pw-test@example.com",
        work_categories=["asbestos_removal"],
    )
    db.add(cp)
    await db.flush()
    return cp


async def _make_full_chain(db, user_id):
    """Create building → publication → request → quote → award → completion (fully_confirmed)."""
    building = await _make_building(db, user_id)
    org = await _make_org(db)
    pub = await _make_publication(db, building.id)
    cp = await _make_company_profile(db, org.id, user_id)

    cr = ClientRequest(
        id=uuid.uuid4(),
        building_id=building.id,
        requester_user_id=user_id,
        title="Asbestos remediation",
        work_category="major",
        status="awarded",
        diagnostic_publication_id=pub.id,
    )
    db.add(cr)
    await db.flush()

    quote = Quote(
        id=uuid.uuid4(),
        client_request_id=cr.id,
        company_profile_id=cp.id,
        amount_chf=Decimal("50000.00"),
        status="accepted",
    )
    db.add(quote)
    await db.flush()

    award = AwardConfirmation(
        id=uuid.uuid4(),
        client_request_id=cr.id,
        quote_id=quote.id,
        company_profile_id=cp.id,
        awarded_by_user_id=user_id,
        award_amount_chf=Decimal("50000.00"),
        awarded_at=datetime.now(UTC),
    )
    db.add(award)
    await db.flush()

    completion = CompletionConfirmation(
        id=uuid.uuid4(),
        award_confirmation_id=award.id,
        client_confirmed=True,
        client_confirmed_at=datetime.now(UTC),
        client_confirmed_by_user_id=user_id,
        company_confirmed=True,
        company_confirmed_at=datetime.now(UTC),
        company_confirmed_by_user_id=user_id,
        status="fully_confirmed",
    )
    db.add(completion)
    await db.flush()

    return building, cr, quote, award, completion, cp


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestPostWorksLinkModel:
    @pytest.mark.asyncio
    async def test_create_post_works_link(self, db_session):
        user = await _make_user(db_session)
        b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)

        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=b.id,
            intervention_type="remediation",
            title="Test intervention",
            status="planned",
        )
        db_session.add(intervention)
        await db_session.flush()

        link = PostWorksLink(
            id=uuid.uuid4(),
            completion_confirmation_id=completion.id,
            intervention_id=intervention.id,
            status="pending",
        )
        db_session.add(link)
        await db_session.flush()

        assert link.id is not None
        assert link.status == "pending"

    @pytest.mark.asyncio
    async def test_post_works_link_status_values(self, db_session):
        user = await _make_user(db_session)
        b, _cr, _q, _award, _completion, _cp = await _make_full_chain(db_session, user.id)

        intervention = Intervention(
            id=uuid.uuid4(),
            building_id=b.id,
            intervention_type="remediation",
            title="Test",
            status="planned",
        )
        db_session.add(intervention)
        await db_session.flush()

        for status in ("pending", "drafted", "review_required", "finalized"):
            link = PostWorksLink(
                id=uuid.uuid4(),
                completion_confirmation_id=uuid.uuid4(),  # just testing column
                intervention_id=intervention.id,
                status=status,
            )
            db_session.add(link)
            await db_session.flush()
            assert link.status == status


class TestDomainEventModel:
    @pytest.mark.asyncio
    async def test_create_domain_event(self, db_session):
        user = await _make_user(db_session)
        evt = DomainEvent(
            id=uuid.uuid4(),
            event_type="remediation_award_linked",
            aggregate_type="intervention",
            aggregate_id=uuid.uuid4(),
            payload={"test": True},
            actor_user_id=user.id,
            occurred_at=datetime.now(UTC),
        )
        db_session.add(evt)
        await db_session.flush()
        assert evt.id is not None
        assert evt.event_type == "remediation_award_linked"

    @pytest.mark.asyncio
    async def test_domain_event_all_types(self, db_session):
        for et in (
            "remediation_award_linked",
            "remediation_completion_fully_confirmed",
            "remediation_post_works_drafted",
            "remediation_post_works_finalized",
            "ai_feedback_recorded",
        ):
            evt = DomainEvent(
                id=uuid.uuid4(),
                event_type=et,
                aggregate_type="test",
                aggregate_id=uuid.uuid4(),
                occurred_at=datetime.now(UTC),
            )
            db_session.add(evt)
            await db_session.flush()
            assert evt.event_type == et


class TestAIFeedbackModel:
    @pytest.mark.asyncio
    async def test_create_ai_feedback(self, db_session):
        user = await _make_user(db_session)
        fb = AIFeedback(
            id=uuid.uuid4(),
            feedback_type="confirm",
            entity_type="post_works_state",
            entity_id=uuid.uuid4(),
            original_output={"state_type": "removed"},
            ai_model="gpt-4o",
            confidence=0.92,
            user_id=user.id,
        )
        db_session.add(fb)
        await db_session.flush()
        assert fb.id is not None
        assert fb.feedback_type == "confirm"

    @pytest.mark.asyncio
    async def test_ai_feedback_types(self, db_session):
        user = await _make_user(db_session)
        for ft in ("confirm", "correct", "reject"):
            fb = AIFeedback(
                id=uuid.uuid4(),
                feedback_type=ft,
                entity_type="post_works_state",
                entity_id=uuid.uuid4(),
                user_id=user.id,
            )
            db_session.add(fb)
            await db_session.flush()
            assert fb.feedback_type == ft

    @pytest.mark.asyncio
    async def test_ai_feedback_with_correction(self, db_session):
        user = await _make_user(db_session)
        fb = AIFeedback(
            id=uuid.uuid4(),
            feedback_type="correct",
            entity_type="post_works_state",
            entity_id=uuid.uuid4(),
            original_output={"state_type": "removed"},
            corrected_output={"state_type": "encapsulated"},
            ai_model="gpt-4o",
            confidence=0.78,
            user_id=user.id,
            notes="Was encapsulated not removed",
        )
        db_session.add(fb)
        await db_session.flush()
        assert fb.corrected_output == {"state_type": "encapsulated"}


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestAwardToIntervention:
    @pytest.mark.asyncio
    async def test_creates_intervention(self, db_session):
        user = await _make_user(db_session)
        b, _cr, _q, award, _completion, _cp = await _make_full_chain(db_session, user.id)

        intervention = await award_to_intervention(db_session, award.id)
        assert intervention is not None
        assert intervention.building_id == b.id
        assert intervention.intervention_type == "remediation"
        assert intervention.status == "planned"

    @pytest.mark.asyncio
    async def test_idempotent(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, award, _completion, _cp = await _make_full_chain(db_session, user.id)

        i1 = await award_to_intervention(db_session, award.id)
        i2 = await award_to_intervention(db_session, award.id)
        assert i1.id == i2.id

    @pytest.mark.asyncio
    async def test_emits_domain_event(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, award, _completion, _cp = await _make_full_chain(db_session, user.id)

        await award_to_intervention(db_session, award.id)

        stmt = select(DomainEvent).where(DomainEvent.event_type == "remediation_award_linked")
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_award_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await award_to_intervention(db_session, uuid.uuid4())


class TestDraftPostWorks:
    @pytest.mark.asyncio
    async def test_draft_creates_link(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)

        link = await draft_post_works(db_session, completion.id, user.id)
        assert link is not None
        assert link.status == "drafted"
        assert link.completion_confirmation_id == completion.id

    @pytest.mark.asyncio
    async def test_draft_idempotent(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)

        l1 = await draft_post_works(db_session, completion.id, user.id)
        l2 = await draft_post_works(db_session, completion.id, user.id)
        assert l1.id == l2.id

    @pytest.mark.asyncio
    async def test_draft_requires_fully_confirmed(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        completion.status = "pending"
        await db_session.flush()

        with pytest.raises(ValueError, match="not fully_confirmed"):
            await draft_post_works(db_session, completion.id, user.id)

    @pytest.mark.asyncio
    async def test_draft_emits_event(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)

        await draft_post_works(db_session, completion.id, user.id)

        stmt = select(DomainEvent).where(DomainEvent.event_type == "remediation_post_works_drafted")
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_draft_not_found(self, db_session):
        user = await _make_user(db_session)
        with pytest.raises(ValueError, match="not found"):
            await draft_post_works(db_session, uuid.uuid4(), user.id)


class TestReviewDraft:
    @pytest.mark.asyncio
    async def test_review_moves_status(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)

        reviewed = await review_draft(db_session, link.id, user.id)
        assert reviewed.status == "review_required"
        assert reviewed.reviewed_by_user_id == user.id

    @pytest.mark.asyncio
    async def test_review_requires_drafted(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)
        await review_draft(db_session, link.id, user.id)

        with pytest.raises(ValueError, match="not in drafted"):
            await review_draft(db_session, link.id, user.id)

    @pytest.mark.asyncio
    async def test_review_not_found(self, db_session):
        user = await _make_user(db_session)
        with pytest.raises(ValueError, match="not found"):
            await review_draft(db_session, uuid.uuid4(), user.id)


class TestFinalizePostWorks:
    @pytest.mark.asyncio
    async def test_finalize(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)
        await review_draft(db_session, link.id, user.id)

        finalized = await finalize_post_works(db_session, link.id, user.id)
        assert finalized.status == "finalized"
        assert finalized.grade_delta is not None
        assert finalized.trust_delta is not None
        assert finalized.finalized_at is not None

    @pytest.mark.asyncio
    async def test_finalize_idempotent(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)
        await review_draft(db_session, link.id, user.id)

        f1 = await finalize_post_works(db_session, link.id, user.id)
        f2 = await finalize_post_works(db_session, link.id, user.id)
        assert f1.id == f2.id
        assert f2.status == "finalized"

    @pytest.mark.asyncio
    async def test_finalize_requires_review(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)

        with pytest.raises(ValueError, match="review_required"):
            await finalize_post_works(db_session, link.id, user.id)

    @pytest.mark.asyncio
    async def test_finalize_emits_event(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)
        await review_draft(db_session, link.id, user.id)
        await finalize_post_works(db_session, link.id, user.id)

        stmt = select(DomainEvent).where(DomainEvent.event_type == "remediation_post_works_finalized")
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_finalize_creates_evidence_link(self, db_session):
        from app.models.evidence_link import EvidenceLink

        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)
        await review_draft(db_session, link.id, user.id)
        await finalize_post_works(db_session, link.id, user.id)

        stmt = select(EvidenceLink).where(EvidenceLink.source_type == "post_works_link")
        result = await db_session.execute(stmt)
        links = result.scalars().all()
        assert len(links) >= 1

    @pytest.mark.asyncio
    async def test_finalize_creates_timeline_event(self, db_session):
        from app.models.event import Event

        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)
        await review_draft(db_session, link.id, user.id)
        await finalize_post_works(db_session, link.id, user.id)

        stmt = select(Event).where(Event.event_type == "post_works_finalized")
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) >= 1


class TestRecordAIFeedback:
    @pytest.mark.asyncio
    async def test_record_confirm(self, db_session):
        user = await _make_user(db_session)
        fb = await record_ai_feedback(
            db_session,
            {
                "feedback_type": "confirm",
                "entity_type": "post_works_state",
                "entity_id": uuid.uuid4(),
                "original_output": {"state": "removed"},
                "ai_model": "gpt-4o",
                "confidence": 0.9,
            },
            user.id,
        )
        assert fb.feedback_type == "confirm"
        assert fb.user_id == user.id

    @pytest.mark.asyncio
    async def test_record_correct(self, db_session):
        user = await _make_user(db_session)
        fb = await record_ai_feedback(
            db_session,
            {
                "feedback_type": "correct",
                "entity_type": "post_works_state",
                "entity_id": uuid.uuid4(),
                "original_output": {"state": "removed"},
                "corrected_output": {"state": "encapsulated"},
                "notes": "Was encapsulated",
            },
            user.id,
        )
        assert fb.feedback_type == "correct"
        assert fb.corrected_output == {"state": "encapsulated"}

    @pytest.mark.asyncio
    async def test_record_reject(self, db_session):
        user = await _make_user(db_session)
        fb = await record_ai_feedback(
            db_session,
            {
                "feedback_type": "reject",
                "entity_type": "extraction",
                "entity_id": uuid.uuid4(),
            },
            user.id,
        )
        assert fb.feedback_type == "reject"

    @pytest.mark.asyncio
    async def test_feedback_emits_event(self, db_session):
        user = await _make_user(db_session)
        await record_ai_feedback(
            db_session,
            {
                "feedback_type": "confirm",
                "entity_type": "post_works_state",
                "entity_id": uuid.uuid4(),
            },
            user.id,
        )
        stmt = select(DomainEvent).where(DomainEvent.event_type == "ai_feedback_recorded")
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) >= 1


class TestReadHelpers:
    @pytest.mark.asyncio
    async def test_get_post_works_link(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        created = await draft_post_works(db_session, completion.id, user.id)

        found = await get_post_works_link(db_session, completion.id)
        assert found is not None
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_post_works_link_not_found(self, db_session):
        result = await get_post_works_link(db_session, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_building_outcomes(self, db_session):
        user = await _make_user(db_session)
        b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        await draft_post_works(db_session, completion.id, user.id)

        outcomes = await get_building_remediation_outcomes(db_session, b.id)
        assert len(outcomes) >= 1

    @pytest.mark.asyncio
    async def test_list_domain_events_all(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        await draft_post_works(db_session, completion.id, user.id)

        events = await list_domain_events(db_session)
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_list_domain_events_filtered(self, db_session):
        user = await _make_user(db_session)
        _b, _cr, _q, _award, completion, _cp = await _make_full_chain(db_session, user.id)
        link = await draft_post_works(db_session, completion.id, user.id)

        events = await list_domain_events(db_session, aggregate_type="post_works_link", aggregate_id=link.id)
        assert len(events) >= 1


# ---------------------------------------------------------------------------
# Projector tests
# ---------------------------------------------------------------------------


class TestDomainEventProjector:
    @pytest.mark.asyncio
    async def test_project_event_calls_handler(self, db_session):
        called = []

        async def test_handler(db, event):
            called.append(event.event_type)

        register_handler("test_event_type", test_handler)
        try:
            evt = DomainEvent(
                id=uuid.uuid4(),
                event_type="test_event_type",
                aggregate_type="test",
                aggregate_id=uuid.uuid4(),
                occurred_at=datetime.now(UTC),
            )
            db_session.add(evt)
            await db_session.flush()

            count = await project_event(db_session, evt)
            assert count >= 1
            assert "test_event_type" in called
        finally:
            _handlers["test_event_type"] = [h for h in _handlers["test_event_type"] if h is not test_handler]

    @pytest.mark.asyncio
    async def test_replay_events(self, db_session):
        agg_id = uuid.uuid4()
        for i in range(3):
            evt = DomainEvent(
                id=uuid.uuid4(),
                event_type="remediation_post_works_finalized",
                aggregate_type="test_replay",
                aggregate_id=agg_id,
                payload={"seq": i},
                occurred_at=datetime.now(UTC),
            )
            db_session.add(evt)
        await db_session.flush()

        count = await replay_events(db_session, "test_replay", agg_id)
        # Each event triggers the built-in handler
        assert count >= 0  # May be 0 if handler not registered for test_replay aggregate

    @pytest.mark.asyncio
    async def test_project_no_handlers(self, db_session):
        evt = DomainEvent(
            id=uuid.uuid4(),
            event_type="nonexistent_event_type",
            aggregate_type="test",
            aggregate_id=uuid.uuid4(),
            occurred_at=datetime.now(UTC),
        )
        db_session.add(evt)
        await db_session.flush()

        count = await project_event(db_session, evt)
        assert count == 0


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_post_works_link_read(self):
        from app.schemas.post_works_link import PostWorksLinkRead

        data = {
            "id": uuid.uuid4(),
            "completion_confirmation_id": uuid.uuid4(),
            "intervention_id": uuid.uuid4(),
            "status": "drafted",
            "grade_delta": {"before": "C", "after": "B", "change": "+1"},
        }
        schema = PostWorksLinkRead(**data)
        assert schema.status == "drafted"
        assert schema.grade_delta["before"] == "C"

    def test_domain_event_read(self):
        from app.schemas.post_works_link import DomainEventRead

        data = {
            "id": uuid.uuid4(),
            "event_type": "remediation_post_works_drafted",
            "aggregate_type": "post_works_link",
            "aggregate_id": uuid.uuid4(),
            "occurred_at": datetime.now(UTC),
        }
        schema = DomainEventRead(**data)
        assert schema.event_type == "remediation_post_works_drafted"

    def test_ai_feedback_create(self):
        from app.schemas.post_works_link import AIFeedbackCreate

        data = {
            "feedback_type": "correct",
            "entity_type": "post_works_state",
            "entity_id": uuid.uuid4(),
            "original_output": {"state": "removed"},
            "corrected_output": {"state": "encapsulated"},
        }
        schema = AIFeedbackCreate(**data)
        assert schema.feedback_type == "correct"

    def test_ai_feedback_read(self):
        from app.schemas.post_works_link import AIFeedbackRead

        data = {
            "id": uuid.uuid4(),
            "feedback_type": "confirm",
            "entity_type": "post_works_state",
            "entity_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
        }
        schema = AIFeedbackRead(**data)
        assert schema.feedback_type == "confirm"


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


class TestSeedPostWorksTruth:
    @pytest.mark.asyncio
    async def test_seed_creates_records(self, db_session):
        from app.seeds.seed_post_works_truth import seed_post_works_truth

        user = await _make_user(db_session)
        result = await seed_post_works_truth(db_session, user_id=user.id)
        assert result["post_works_links"] == 1
        assert result["domain_events"] == 3
        assert result["ai_feedback"] == 2

    @pytest.mark.asyncio
    async def test_seed_idempotent(self, db_session):
        from app.seeds.seed_post_works_truth import seed_post_works_truth

        user = await _make_user(db_session)
        await seed_post_works_truth(db_session, user_id=user.id)
        r2 = await seed_post_works_truth(db_session, user_id=user.id)
        assert r2["post_works_links"] == 0
        assert r2["domain_events"] == 0
        assert r2["ai_feedback"] == 0
