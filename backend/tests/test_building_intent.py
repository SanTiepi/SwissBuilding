"""Tests for Building Intent, Question, DecisionContext, SafeToXState models and service."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_intent import (
    INTENT_TYPES,
    QUESTION_TYPES,
    SAFE_TO_TYPES,
    VERDICT_VALUES,
    BuildingIntent,
    BuildingQuestion,
    DecisionContext,
    SafeToXState,
)
from app.models.user import User
from app.services.intent_service import (
    _INTENT_TO_QUESTIONS,
    _QUESTION_TO_SAFE_TO,
    _default_question_text,
    ask_question,
    create_intent,
    evaluate_question,
    get_building_intents,
    get_safe_to_x_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(db_session, *, email=None, **kwargs):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    defaults = {
        "id": uuid.uuid4(),
        "email": email or f"test-{uuid.uuid4().hex[:8]}@test.ch",
        "password_hash": pwd_context.hash("test123"),
        "first_name": "Test",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db_session.add(user)
    return user


def _make_building(db_session, user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(**defaults)
    db_session.add(building)
    return building


# ---------------------------------------------------------------------------
# Model constants tests
# ---------------------------------------------------------------------------


class TestIntentConstants:
    def test_intent_types_not_empty(self):
        assert len(INTENT_TYPES) >= 13

    def test_question_types_not_empty(self):
        assert len(QUESTION_TYPES) >= 16

    def test_safe_to_types_not_empty(self):
        assert len(SAFE_TO_TYPES) >= 10

    def test_verdict_values(self):
        assert set(VERDICT_VALUES) == {"clear", "conditional", "blocked", "unknown"}


# ---------------------------------------------------------------------------
# Intent→Question mapping
# ---------------------------------------------------------------------------


class TestIntentToQuestionMapping:
    def test_sell_generates_safe_to_sell(self):
        assert "safe_to_sell" in _INTENT_TO_QUESTIONS["sell"]

    def test_renovate_generates_safe_to_start(self):
        assert "safe_to_start" in _INTENT_TO_QUESTIONS["renovate"]

    def test_insure_generates_safe_to_insure(self):
        assert "safe_to_insure" in _INTENT_TO_QUESTIONS["insure"]

    def test_other_generates_nothing(self):
        assert _INTENT_TO_QUESTIONS["other"] == []

    def test_all_intent_types_have_mapping(self):
        for it in INTENT_TYPES:
            assert it in _INTENT_TO_QUESTIONS


class TestQuestionToSafeToMapping:
    def test_safe_to_start_maps_to_start(self):
        assert _QUESTION_TO_SAFE_TO["safe_to_start"] == "start"

    def test_safe_to_sell_maps_to_sell(self):
        assert _QUESTION_TO_SAFE_TO["safe_to_sell"] == "sell"

    def test_analytical_questions_not_mapped(self):
        for qt in ("what_blocks", "what_missing", "what_contradicts", "custom"):
            assert qt not in _QUESTION_TO_SAFE_TO


# ---------------------------------------------------------------------------
# Default question text
# ---------------------------------------------------------------------------


class TestDefaultQuestionText:
    def test_known_types_return_human_text(self):
        for qt in QUESTION_TYPES:
            text = _default_question_text(qt)
            assert len(text) > 10
            assert "building" in text.lower() or "renovation" in text.lower() or "tender" in text.lower()

    def test_unknown_type_returns_fallback(self):
        text = _default_question_text("nonexistent")
        assert "nonexistent" in text


# ---------------------------------------------------------------------------
# Model creation tests
# ---------------------------------------------------------------------------


class TestBuildingIntentModel:
    @pytest.mark.asyncio
    async def test_create_intent_model(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        intent = BuildingIntent(
            building_id=building.id,
            created_by_id=user.id,
            intent_type="sell",
            title="Sell the building",
            status="open",
        )
        db_session.add(intent)
        await db_session.flush()
        assert intent.id is not None
        assert intent.intent_type == "sell"

    @pytest.mark.asyncio
    async def test_create_question_model(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = BuildingQuestion(
            building_id=building.id,
            asked_by_id=user.id,
            question_type="safe_to_sell",
            question_text="Is this building safe to sell?",
            status="pending",
        )
        db_session.add(question)
        await db_session.flush()
        assert question.id is not None
        assert question.status == "pending"

    @pytest.mark.asyncio
    async def test_create_decision_context_model(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = BuildingQuestion(
            building_id=building.id,
            asked_by_id=user.id,
            question_type="what_blocks",
            question_text="What blocks?",
            status="pending",
        )
        db_session.add(question)
        await db_session.flush()

        dc = DecisionContext(
            question_id=question.id,
            building_id=building.id,
            blockers=[{"description": "Missing diagnostic"}],
            overall_confidence=0.5,
            data_freshness="current",
            coverage_assessment="partial",
        )
        db_session.add(dc)
        await db_session.flush()
        assert dc.id is not None
        assert dc.overall_confidence == 0.5

    @pytest.mark.asyncio
    async def test_create_safe_to_x_state_model(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = BuildingQuestion(
            building_id=building.id,
            asked_by_id=user.id,
            question_type="safe_to_sell",
            question_text="Safe to sell?",
            status="pending",
        )
        db_session.add(question)
        await db_session.flush()

        stx = SafeToXState(
            question_id=question.id,
            building_id=building.id,
            safe_to_type="sell",
            verdict="blocked",
            verdict_summary="Not ready for sale",
            evaluated_by="system",
            confidence=0.3,
        )
        db_session.add(stx)
        await db_session.flush()
        assert stx.id is not None
        assert stx.verdict == "blocked"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestCreateIntentService:
    @pytest.mark.asyncio
    async def test_create_intent_auto_generates_questions(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        intent = await create_intent(
            db_session,
            building_id=building.id,
            intent_type="sell",
            created_by_id=user.id,
            title="Sell building",
        )
        assert intent.id is not None
        assert intent.intent_type == "sell"
        assert intent.status == "open"

        # Should have auto-generated questions
        from sqlalchemy import select

        result = await db_session.execute(select(BuildingQuestion).where(BuildingQuestion.intent_id == intent.id))
        questions = list(result.scalars().all())
        expected_count = len(_INTENT_TO_QUESTIONS["sell"])
        assert len(questions) == expected_count

    @pytest.mark.asyncio
    async def test_create_intent_invalid_type_raises(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        with pytest.raises(ValueError, match="Unknown intent_type"):
            await create_intent(
                db_session,
                building_id=building.id,
                intent_type="nonexistent",
                created_by_id=user.id,
                title="Bad intent",
            )

    @pytest.mark.asyncio
    async def test_create_intent_building_not_found_raises(self, db_session):
        user = _make_user(db_session)
        await db_session.flush()

        with pytest.raises(ValueError, match="not found"):
            await create_intent(
                db_session,
                building_id=uuid.uuid4(),
                intent_type="sell",
                created_by_id=user.id,
                title="Bad intent",
            )

    @pytest.mark.asyncio
    async def test_create_intent_other_no_questions(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        intent = await create_intent(
            db_session,
            building_id=building.id,
            intent_type="other",
            created_by_id=user.id,
            title="Other intent",
        )

        from sqlalchemy import select

        result = await db_session.execute(select(BuildingQuestion).where(BuildingQuestion.intent_id == intent.id))
        questions = list(result.scalars().all())
        assert len(questions) == 0


class TestAskQuestionService:
    @pytest.mark.asyncio
    async def test_ask_question_with_default_text(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = await ask_question(
            db_session,
            building_id=building.id,
            question_type="safe_to_sell",
            asked_by_id=user.id,
        )
        assert question.question_type == "safe_to_sell"
        assert "sold" in question.question_text.lower() or "sell" in question.question_text.lower()
        assert question.status == "pending"

    @pytest.mark.asyncio
    async def test_ask_question_with_custom_text(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = await ask_question(
            db_session,
            building_id=building.id,
            question_type="custom",
            asked_by_id=user.id,
            question_text="Can we build a pool?",
        )
        assert question.question_text == "Can we build a pool?"

    @pytest.mark.asyncio
    async def test_ask_question_invalid_type_raises(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        with pytest.raises(ValueError, match="Unknown question_type"):
            await ask_question(
                db_session,
                building_id=building.id,
                question_type="nonexistent",
                asked_by_id=user.id,
            )


class TestGetBuildingIntents:
    @pytest.mark.asyncio
    async def test_list_intents_empty(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        intents = await get_building_intents(db_session, building.id)
        assert intents == []

    @pytest.mark.asyncio
    async def test_list_intents_returns_created(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        await create_intent(
            db_session,
            building_id=building.id,
            intent_type="sell",
            created_by_id=user.id,
            title="Sell",
        )
        await create_intent(
            db_session,
            building_id=building.id,
            intent_type="insure",
            created_by_id=user.id,
            title="Insure",
        )

        intents = await get_building_intents(db_session, building.id)
        assert len(intents) == 2

    @pytest.mark.asyncio
    async def test_list_intents_filter_by_status(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        await create_intent(
            db_session,
            building_id=building.id,
            intent_type="sell",
            created_by_id=user.id,
            title="Sell",
        )

        open_intents = await get_building_intents(db_session, building.id, status="open")
        assert len(open_intents) == 1

        closed_intents = await get_building_intents(db_session, building.id, status="closed")
        assert len(closed_intents) == 0


class TestEvaluateQuestion:
    @pytest.mark.asyncio
    async def test_evaluate_analytical_question(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = await ask_question(
            db_session,
            building_id=building.id,
            question_type="what_blocks",
            asked_by_id=user.id,
        )

        evaluated = await evaluate_question(db_session, question.id)
        assert evaluated.status == "answered"
        assert evaluated.answered_at is not None

    @pytest.mark.asyncio
    async def test_evaluate_safe_to_question(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        question = await ask_question(
            db_session,
            building_id=building.id,
            question_type="safe_to_start",
            asked_by_id=user.id,
        )

        evaluated = await evaluate_question(db_session, question.id)
        assert evaluated.status == "answered"

    @pytest.mark.asyncio
    async def test_evaluate_nonexistent_question_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await evaluate_question(db_session, uuid.uuid4())


class TestGetSafeToXSummary:
    @pytest.mark.asyncio
    async def test_summary_returns_verdicts(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        summary = await get_safe_to_x_summary(db_session, building.id)
        assert "building_id" in summary
        assert "verdicts" in summary
        assert "evaluated_at" in summary
        # Should have some verdicts from both readiness reasoner and transaction readiness
        assert len(summary["verdicts"]) > 0

    @pytest.mark.asyncio
    async def test_summary_verdict_structure(self, db_session):
        user = _make_user(db_session)
        building = _make_building(db_session, user)
        await db_session.flush()

        summary = await get_safe_to_x_summary(db_session, building.id)
        for v in summary["verdicts"]:
            assert "safe_to_type" in v
            assert "verdict" in v
            assert v["verdict"] in VERDICT_VALUES
            assert "verdict_summary" in v
            assert "evaluated_by" in v
