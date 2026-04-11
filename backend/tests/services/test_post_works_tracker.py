"""Tests for post-works truth tracker service."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.building import Building
from app.models.post_work_item import PostWorkItem, WorksCompletionCertificate
from app.models.user import User
from app.services.post_works_tracker_service import (
    REVIEW_THRESHOLD,
    _compute_verification_score,
    complete_post_work_item,
    get_completion_status,
    get_or_create_certificate,
    list_post_work_items,
)


@pytest.fixture
async def contractor(db_session):
    u = User(
        email="contractor@test.ch",
        password_hash="x",
        first_name="Test",
        last_name="Contractor",
        role="contractor",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def building(db_session):
    b = Building(
        egrid="CH123456789012",
        address="1 Rue du Test",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="house",
        created_by=uuid4(),
    )
    db_session.add(b)
    await db_session.flush()
    return b


@pytest.fixture
async def post_work_item(db_session, building, contractor):
    item = PostWorkItem(
        building_id=building.id,
        contractor_id=contractor.id,
        completion_status="pending",
        notes="Initial item",
    )
    db_session.add(item)
    await db_session.flush()
    return item


class TestPostWorkItemModel:
    async def test_create_with_required_fields(self, db_session, building, contractor):
        item = PostWorkItem(
            building_id=building.id,
            contractor_id=contractor.id,
        )
        db_session.add(item)
        await db_session.flush()

        assert item.id is not None
        assert item.building_id == building.id
        assert item.contractor_id == contractor.id
        assert item.completion_status == "pending"

    async def test_default_values(self, db_session, building, contractor):
        item = PostWorkItem(
            building_id=building.id,
            contractor_id=contractor.id,
        )
        db_session.add(item)
        await db_session.flush()

        assert item.verification_score == 0.0
        assert item.flagged_for_review is False
        assert item.ai_generated is False

    async def test_tablename(self):
        assert PostWorkItem.__tablename__ == "post_work_items"

    async def test_certificate_tablename(self):
        assert WorksCompletionCertificate.__tablename__ == "works_completion_certificates"


class TestVerificationScore:
    def test_no_photos_zero_score(self):
        item = PostWorkItem(created_at=datetime.now(UTC))
        score = _compute_verification_score([], None, item)
        assert score == 0.0 + 15.0  # only timestamp bonus

    def test_one_photo_minimum(self):
        item = PostWorkItem(created_at=datetime.now(UTC))
        score = _compute_verification_score(["photo1.jpg"], None, item)
        assert score >= 40.0  # photo + timestamp

    def test_three_photos_bonus(self):
        item = PostWorkItem(created_at=datetime.now(UTC))
        score = _compute_verification_score(["p1.jpg", "p2.jpg", "p3.jpg"], None, item)
        assert score >= 50.0  # 40 base + 10 bonus + 15 timestamp

    def test_before_after_pairs_bonus(self):
        item = PostWorkItem(created_at=datetime.now(UTC))
        score = _compute_verification_score(
            ["p1.jpg"],
            [{"before_photo_id": "a", "after_photo_id": "b"}],
            item,
        )
        assert (
            score >= 65.0
        )  # 40 photo + 25 pairs + 15 timestamp (at minimum -- notes would be 0 since item.notes is None)
        # Actually: 40 + 25 + 15 = 80

    def test_full_score_with_notes(self):
        item = PostWorkItem(created_at=datetime.now(UTC), notes="Detailed notes about the completion work done")
        score = _compute_verification_score(
            ["p1.jpg", "p2.jpg", "p3.jpg"],
            [{"before_photo_id": "a", "after_photo_id": "b"}],
            item,
        )
        assert score == 100.0

    def test_flagged_below_threshold(self):
        item = PostWorkItem(created_at=datetime.now(UTC))
        score = _compute_verification_score(["p1.jpg"], None, item)
        assert score < REVIEW_THRESHOLD  # 40 + 15 = 55 < 80


class TestListPostWorkItems:
    async def test_list_empty(self, db_session, building):
        result = await list_post_work_items(db_session, building.id)
        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_with_items(self, db_session, building, contractor):
        for i in range(3):
            db_session.add(
                PostWorkItem(
                    building_id=building.id,
                    contractor_id=contractor.id,
                    notes=f"Item {i}",
                )
            )
        await db_session.flush()

        result = await list_post_work_items(db_session, building.id)
        assert result["total"] == 3
        assert len(result["items"]) == 3

    async def test_list_filter_by_status(self, db_session, building, contractor):
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="pending",
            )
        )
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="completed",
            )
        )
        await db_session.flush()

        result = await list_post_work_items(db_session, building.id, status="completed")
        assert result["total"] == 1


class TestCompletePostWorkItem:
    async def test_complete_sets_status(self, db_session, post_work_item):
        result = await complete_post_work_item(db_session, post_work_item, ["photo1.jpg"])
        assert result.completion_status == "completed"
        assert result.completion_date is not None

    async def test_complete_stores_photos(self, db_session, post_work_item):
        photos = ["photo1.jpg", "photo2.jpg"]
        result = await complete_post_work_item(db_session, post_work_item, photos)
        assert result.photo_uris == photos

    async def test_complete_flags_low_score(self, db_session, post_work_item):
        result = await complete_post_work_item(db_session, post_work_item, ["photo1.jpg"])
        assert result.flagged_for_review is True
        assert result.verification_score < REVIEW_THRESHOLD


class TestCompletionStatus:
    async def test_empty_building(self, db_session, building):
        status = await get_completion_status(db_session, building.id)
        assert status["total_items"] == 0
        assert status["completion_percentage"] == 0.0

    async def test_partial_completion(self, db_session, building, contractor):
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="completed",
            )
        )
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="pending",
            )
        )
        await db_session.flush()

        status = await get_completion_status(db_session, building.id)
        assert status["total_items"] == 2
        assert status["completed_items"] == 1
        assert status["completion_percentage"] == 50.0

    async def test_full_completion(self, db_session, building, contractor):
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="verified",
            )
        )
        await db_session.flush()

        status = await get_completion_status(db_session, building.id)
        assert status["completion_percentage"] == 100.0


class TestCertificate:
    async def test_certificate_not_issued_if_incomplete(self, db_session, building, contractor):
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="pending",
            )
        )
        await db_session.flush()

        cert = await get_or_create_certificate(db_session, building.id)
        assert cert is None

    async def test_certificate_issued_at_100_percent(self, db_session, building, contractor):
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="verified",
            )
        )
        await db_session.flush()

        cert = await get_or_create_certificate(db_session, building.id)
        assert cert is not None
        assert cert.completion_percentage == 100.0
        assert cert.pdf_uri.startswith("s3://")

    async def test_certificate_idempotent(self, db_session, building, contractor):
        db_session.add(
            PostWorkItem(
                building_id=building.id,
                contractor_id=contractor.id,
                completion_status="verified",
            )
        )
        await db_session.flush()

        cert1 = await get_or_create_certificate(db_session, building.id)
        cert2 = await get_or_create_certificate(db_session, building.id)
        assert cert1.id == cert2.id
