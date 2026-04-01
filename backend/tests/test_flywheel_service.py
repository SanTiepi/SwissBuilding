"""Tests for flywheel learning loop — classification & extraction feedback."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.document import Document
from app.models.user import User
from app.services.flywheel_service import (
    get_classification_accuracy,
    get_extraction_accuracy,
    get_flywheel_dashboard,
    get_learning_rules,
    record_classification_feedback,
    record_extraction_feedback,
)


@pytest.fixture
async def fw_user(db_session: AsyncSession, admin_user: User):
    return admin_user


@pytest.fixture
async def fw_building(db_session: AsyncSession, admin_user: User):
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Flywheel 10",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def fw_document(db_session: AsyncSession, fw_building: Building):
    doc = Document(
        id=uuid.uuid4(),
        building_id=fw_building.id,
        file_path="/docs/test.pdf",
        file_name="rapport_amiante.pdf",
        document_type="unclassified",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Classification feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_classification_feedback_correction(
    db_session: AsyncSession, fw_document: Document, fw_user: User
):
    result = await record_classification_feedback(
        db_session,
        document_id=fw_document.id,
        predicted_type="lead_report",
        corrected_type="asbestos_report",
        user_id=fw_user.id,
    )
    await db_session.commit()

    assert result["feedback_type"] == "correct"
    assert result["is_correct"] is False
    assert result["predicted_type"] == "lead_report"
    assert result["corrected_type"] == "asbestos_report"


@pytest.mark.asyncio
async def test_record_classification_feedback_confirm(db_session: AsyncSession, fw_document: Document, fw_user: User):
    result = await record_classification_feedback(
        db_session,
        document_id=fw_document.id,
        predicted_type="asbestos_report",
        corrected_type="asbestos_report",
        user_id=fw_user.id,
    )
    await db_session.commit()

    assert result["feedback_type"] == "confirm"
    assert result["is_correct"] is True


# ---------------------------------------------------------------------------
# Extraction feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_extraction_feedback_accepted(db_session: AsyncSession, fw_document: Document, fw_user: User):
    result = await record_extraction_feedback(
        db_session,
        document_id=fw_document.id,
        field_name="dates",
        predicted_value="15.03.2026",
        corrected_value=None,
        accepted=True,
        user_id=fw_user.id,
    )
    await db_session.commit()

    assert result["feedback_type"] == "confirm"
    assert result["accepted"] is True


@pytest.mark.asyncio
async def test_record_extraction_feedback_corrected(db_session: AsyncSession, fw_document: Document, fw_user: User):
    result = await record_extraction_feedback(
        db_session,
        document_id=fw_document.id,
        field_name="amounts",
        predicted_value="CHF 1000",
        corrected_value="CHF 1200",
        accepted=False,
        user_id=fw_user.id,
    )
    await db_session.commit()

    assert result["feedback_type"] == "correct"
    assert result["accepted"] is False
    assert result["corrected_value"] == "CHF 1200"


@pytest.mark.asyncio
async def test_record_extraction_feedback_rejected(db_session: AsyncSession, fw_document: Document, fw_user: User):
    result = await record_extraction_feedback(
        db_session,
        document_id=fw_document.id,
        field_name="parcels",
        predicted_value="123/A",
        corrected_value=None,
        accepted=False,
        user_id=fw_user.id,
    )
    await db_session.commit()

    assert result["feedback_type"] == "reject"


# ---------------------------------------------------------------------------
# Accuracy metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classification_accuracy_with_feedbacks(db_session: AsyncSession, fw_document: Document, fw_user: User):
    # 3 correct, 1 wrong
    for _ in range(3):
        await record_classification_feedback(
            db_session, fw_document.id, "asbestos_report", "asbestos_report", fw_user.id
        )
    await record_classification_feedback(db_session, fw_document.id, "asbestos_report", "lead_report", fw_user.id)
    await db_session.commit()

    metrics = await get_classification_accuracy(db_session)

    assert metrics["total_predictions"] == 4
    assert metrics["total_corrections"] == 1
    assert metrics["overall_accuracy"] == 0.75
    assert "asbestos_report" in metrics["per_type_accuracy"]
    assert len(metrics["confusion_matrix"]) == 1
    assert metrics["confusion_matrix"][0]["predicted"] == "asbestos_report"
    assert metrics["confusion_matrix"][0]["actual"] == "lead_report"


@pytest.mark.asyncio
async def test_extraction_accuracy_with_feedbacks(db_session: AsyncSession, fw_document: Document, fw_user: User):
    # 2 confirmed, 1 corrected
    await record_extraction_feedback(db_session, fw_document.id, "dates", "01.01.2026", None, True, fw_user.id)
    await record_extraction_feedback(db_session, fw_document.id, "dates", "15.03.2026", None, True, fw_user.id)
    await record_extraction_feedback(db_session, fw_document.id, "amounts", "CHF 500", "CHF 600", False, fw_user.id)
    await db_session.commit()

    metrics = await get_extraction_accuracy(db_session)

    assert metrics["total_extractions"] == 3
    assert metrics["total_corrections"] == 1
    assert metrics["overall_accuracy"] == pytest.approx(0.667, abs=0.01)


# ---------------------------------------------------------------------------
# Learned rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_learned_rules_emerge_after_threshold(db_session: AsyncSession, fw_document: Document, fw_user: User):
    # Create 6 corrections of same pattern (threshold is 5)
    for _ in range(6):
        await record_classification_feedback(db_session, fw_document.id, "pcb_report", "lead_report", fw_user.id)
    await db_session.commit()

    rules = await get_learning_rules(db_session)

    assert len(rules) == 1
    assert rules[0]["predicted_type"] == "pcb_report"
    assert rules[0]["corrected_type"] == "lead_report"
    assert rules[0]["occurrence_count"] == 6
    assert rules[0]["confidence"] > 0


@pytest.mark.asyncio
async def test_learned_rules_below_threshold(db_session: AsyncSession, fw_document: Document, fw_user: User):
    # Only 3 corrections (below threshold of 5)
    for _ in range(3):
        await record_classification_feedback(db_session, fw_document.id, "pcb_report", "lead_report", fw_user.id)
    await db_session.commit()

    rules = await get_learning_rules(db_session)
    assert len(rules) == 0


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_aggregation(db_session: AsyncSession, fw_document: Document, fw_user: User):
    # Some classification feedback
    await record_classification_feedback(db_session, fw_document.id, "asbestos_report", "asbestos_report", fw_user.id)
    await record_classification_feedback(db_session, fw_document.id, "lead_report", "pcb_report", fw_user.id)
    # Some extraction feedback
    await record_extraction_feedback(db_session, fw_document.id, "dates", "01.01.2026", None, True, fw_user.id)
    await db_session.commit()

    dashboard = await get_flywheel_dashboard(db_session)

    assert dashboard["total_documents_processed"] == 3
    assert dashboard["total_corrections"] == 1
    assert dashboard["classification_accuracy"] == 0.5
    assert dashboard["extraction_accuracy"] == 1.0
    assert "improvement_trend" in dashboard


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_state(db_session: AsyncSession):
    metrics = await get_classification_accuracy(db_session)
    assert metrics["total_predictions"] == 0
    assert metrics["overall_accuracy"] == 0.0

    ext_metrics = await get_extraction_accuracy(db_session)
    assert ext_metrics["total_extractions"] == 0

    dashboard = await get_flywheel_dashboard(db_session)
    assert dashboard["total_documents_processed"] == 0
    assert dashboard["learned_rules_count"] == 0
