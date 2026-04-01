"""Tests for Remediation Module Growth Stack."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _org_id():
    return uuid.uuid4()


def _user_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------


class TestSubscriptionChangeModel:
    def test_subscription_change_table_name(self):
        from app.models.subscription_change import SubscriptionChange

        assert SubscriptionChange.__tablename__ == "subscription_changes"

    def test_subscription_change_columns(self):
        from app.models.subscription_change import SubscriptionChange

        cols = {c.name for c in SubscriptionChange.__table__.columns}
        assert "id" in cols
        assert "subscription_id" in cols
        assert "change_type" in cols
        assert "old_plan" in cols
        assert "new_plan" in cols
        assert "changed_by_user_id" in cols
        assert "reason" in cols
        assert "created_at" in cols


class TestAIExtractionLogModel:
    def test_ai_extraction_log_table_name(self):
        from app.models.ai_extraction_log import AIExtractionLog

        assert AIExtractionLog.__tablename__ == "ai_extraction_logs"

    def test_ai_extraction_log_columns(self):
        from app.models.ai_extraction_log import AIExtractionLog

        cols = {c.name for c in AIExtractionLog.__table__.columns}
        expected = {
            "id",
            "extraction_type",
            "source_document_id",
            "source_filename",
            "input_hash",
            "output_data",
            "confidence_score",
            "ai_model",
            "ambiguous_fields",
            "unknown_fields",
            "status",
            "confirmed_by_user_id",
            "confirmed_at",
            "created_at",
        }
        assert expected.issubset(cols)

    def test_ai_extraction_log_indexes(self):
        from app.models.ai_extraction_log import AIExtractionLog

        idx_names = {idx.name for idx in AIExtractionLog.__table__.indexes}
        assert "idx_ai_extraction_logs_type" in idx_names
        assert "idx_ai_extraction_logs_status" in idx_names
        assert "idx_ai_extraction_logs_hash" in idx_names


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestGrowthStackSchemas:
    def test_subscription_change_read(self):
        from app.schemas.growth_stack import SubscriptionChangeRead

        data = SubscriptionChangeRead(
            id=uuid.uuid4(),
            subscription_id=uuid.uuid4(),
            change_type="plan_changed",
            old_plan="basic",
            new_plan="professional",
            created_at=datetime.now(UTC),
        )
        assert data.change_type == "plan_changed"

    def test_company_eligibility_summary(self):
        from app.schemas.growth_stack import CompanyEligibilitySummary

        s = CompanyEligibilitySummary(
            company_profile_id=uuid.uuid4(),
            verified=True,
            subscription_active=False,
            eligible=False,
            blockers=["no_active_subscription"],
        )
        assert not s.eligible
        assert "no_active_subscription" in s.blockers

    def test_subscription_lifecycle_view(self):
        from app.schemas.growth_stack import SubscriptionLifecycleView

        v = SubscriptionLifecycleView(
            subscription_id=uuid.uuid4(),
            company_profile_id=uuid.uuid4(),
            current_plan="basic",
            current_status="active",
            changes=[],
        )
        assert v.current_plan == "basic"

    def test_quote_extraction_draft(self):
        from app.schemas.growth_stack import QuoteExtractionDraft

        d = QuoteExtractionDraft(
            scope_items=["asbestos_removal"],
            exclusions=["scaffolding"],
            timeline_weeks=4,
            amount_chf=30000,
            confidence_per_field={"scope_items": 0.9},
            ambiguous_fields=[],
            unknown_fields=[],
        )
        assert d.amount_chf == 30000

    def test_completion_extraction_draft(self):
        from app.schemas.growth_stack import CompletionExtractionDraft

        d = CompletionExtractionDraft(
            completed_items=["removal"],
            residual_items=[],
            final_amount_chf=25000,
            confidence_per_field={"completed_items": 0.95},
            ambiguous_fields=[],
            unknown_fields=[],
        )
        assert d.final_amount_chf == 25000

    def test_ai_extraction_read(self):
        from app.schemas.growth_stack import AIExtractionRead

        r = AIExtractionRead(
            id=uuid.uuid4(),
            extraction_type="quote_pdf",
            input_hash="a" * 64,
            status="draft",
            created_at=datetime.now(UTC),
        )
        assert r.status == "draft"

    def test_company_workspace_summary(self):
        from app.schemas.growth_stack import CompanyWorkspaceSummary

        ws = CompanyWorkspaceSummary(
            company_profile_id=uuid.uuid4(),
            company_name="Test Co",
            is_verified=True,
            pending_invitations=3,
            active_rfqs=2,
            draft_quotes=1,
            awards_won=5,
            completions_pending=0,
            reviews_published=4,
        )
        assert ws.awards_won == 5

    def test_operator_remediation_queue(self):
        from app.schemas.growth_stack import OperatorRemediationQueue

        q = OperatorRemediationQueue(
            active_rfqs=2,
            quotes_received=5,
            awards_pending=1,
            completions_awaiting=0,
            post_works_open=1,
        )
        assert q.quotes_received == 5

    def test_quote_comparison_matrix(self):
        from app.schemas.growth_stack import QuoteComparisonMatrix, QuoteComparisonRow

        m = QuoteComparisonMatrix(
            request_id=uuid.uuid4(),
            rows=[
                QuoteComparisonRow(
                    company_name="A Corp",
                    amount_chf=50000,
                    timeline_weeks=8,
                    scope_items=["removal"],
                    exclusions=[],
                    ambiguous_fields=[],
                    submitted_at=datetime.now(UTC),
                ),
            ],
        )
        assert len(m.rows) == 1

    def test_completion_closure_summary(self):
        from app.schemas.growth_stack import CompletionClosureSummary

        s = CompletionClosureSummary(
            completion_id=uuid.uuid4(),
            completion_status="fully_confirmed",
        )
        assert s.completion_status == "fully_confirmed"

    def test_flywheel_metrics(self):
        from app.schemas.growth_stack import FlywheelMetrics

        m = FlywheelMetrics(
            total_extractions=100,
            confirmation_rate=0.7,
            correction_rate=0.2,
            rejection_rate=0.1,
            total_completed_cycles=15,
            total_reviews_published=12,
            knowledge_density=0.05,
        )
        assert m.total_extractions == 100


# ---------------------------------------------------------------------------
# Service tests (DB-backed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_quote_data(db_session):
    from app.services.ai_extraction_service import extract_quote_data

    log, draft = await extract_quote_data(db_session, text="Sample quote text")
    assert log.extraction_type == "quote_pdf"
    assert log.status == "draft"
    assert draft.scope_items
    assert log.input_hash


@pytest.mark.asyncio
async def test_extract_completion_data(db_session):
    from app.services.ai_extraction_service import extract_completion_data

    log, draft = await extract_completion_data(db_session, text="Sample completion report")
    assert log.extraction_type == "completion_report"
    assert draft.completed_items


@pytest.mark.asyncio
async def test_confirm_extraction(db_session):
    from app.services.ai_extraction_service import confirm_extraction, extract_quote_data

    log, _ = await extract_quote_data(db_session, text="confirm test")
    user_id = uuid.uuid4()
    confirmed = await confirm_extraction(db_session, log.id, user_id)
    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_by_user_id == user_id


@pytest.mark.asyncio
async def test_correct_extraction(db_session):
    from app.services.ai_extraction_service import correct_extraction, extract_quote_data

    log, _ = await extract_quote_data(db_session, text="correct test")
    user_id = uuid.uuid4()
    corrected_data = {"scope_items": ["updated"], "amount_chf": 99999}
    result = await correct_extraction(db_session, log.id, corrected_data, user_id, "Fixed scope")
    assert result.status == "corrected"
    assert result.output_data["amount_chf"] == 99999


@pytest.mark.asyncio
async def test_reject_extraction(db_session):
    from app.services.ai_extraction_service import extract_quote_data, reject_extraction

    log, _ = await extract_quote_data(db_session, text="reject test")
    user_id = uuid.uuid4()
    result = await reject_extraction(db_session, log.id, user_id, "Bad data")
    assert result.status == "rejected"


@pytest.mark.asyncio
async def test_extraction_not_found(db_session):
    from app.services.ai_extraction_service import confirm_extraction

    with pytest.raises(ValueError, match="not found"):
        await confirm_extraction(db_session, uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_flywheel_metrics(db_session):
    from app.services.flywheel_metrics_service import get_module_metrics

    metrics = await get_module_metrics(db_session)
    assert metrics.total_extractions >= 0
    assert 0 <= metrics.confirmation_rate <= 1


@pytest.mark.asyncio
async def test_operator_queue(db_session):
    from app.services.remediation_workspace_service import get_operator_queue

    queue = await get_operator_queue(db_session, uuid.uuid4())
    assert queue.active_rfqs >= 0
    assert queue.quotes_received >= 0


@pytest.mark.asyncio
async def test_quote_comparison_matrix_empty(db_session):
    from app.services.remediation_workspace_service import get_quote_comparison_matrix

    matrix = await get_quote_comparison_matrix(db_session, uuid.uuid4())
    assert matrix.rows == []


@pytest.mark.asyncio
async def test_company_workspace_not_found(db_session):
    from app.services.remediation_workspace_service import get_company_workspace

    result = await get_company_workspace(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_completion_closure_not_found(db_session):
    from app.services.remediation_workspace_service import get_completion_closure_summary

    result = await get_completion_closure_summary(db_session, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# API endpoint tests (require router registration in hub file — supervisor merge)
# ---------------------------------------------------------------------------


def _is_router_wired():
    """Check if remediation_workspace router is wired in the main api_router."""
    try:
        from app.api.router import api_router

        for route in api_router.routes:
            path = getattr(route, "path", "")
            if "flywheel" in path or "extractions/quote" in path:
                return True
    except Exception:
        pass
    return False


_skip_no_router = pytest.mark.skipif(not _is_router_wired(), reason="Router not yet registered in hub file")


@_skip_no_router
@pytest.mark.asyncio
async def test_extract_quote_api(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/marketplace/extractions/quote",
        json={"text": "Quote for asbestos removal", "source_filename": "quote.pdf"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["extraction_type"] == "quote_pdf"
    assert data["status"] == "draft"


@_skip_no_router
@pytest.mark.asyncio
async def test_extract_completion_api(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/marketplace/extractions/completion",
        json={"text": "Completion report"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["extraction_type"] == "completion_report"


@_skip_no_router
@pytest.mark.asyncio
async def test_confirm_extraction_api(client: AsyncClient, auth_headers: dict):
    # Create extraction first
    resp = await client.post(
        "/api/v1/marketplace/extractions/quote",
        json={"text": "confirm api test"},
        headers=auth_headers,
    )
    log_id = resp.json()["id"]

    # Confirm it
    resp2 = await client.post(
        f"/api/v1/marketplace/extractions/{log_id}/confirm",
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "confirmed"


@_skip_no_router
@pytest.mark.asyncio
async def test_correct_extraction_api(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/marketplace/extractions/quote",
        json={"text": "correct api test"},
        headers=auth_headers,
    )
    log_id = resp.json()["id"]

    resp2 = await client.post(
        f"/api/v1/marketplace/extractions/{log_id}/correct",
        json={"corrected_data": {"amount_chf": 55000}, "notes": "Fixed amount"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "corrected"


@_skip_no_router
@pytest.mark.asyncio
async def test_reject_extraction_api(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/marketplace/extractions/quote",
        json={"text": "reject api test"},
        headers=auth_headers,
    )
    log_id = resp.json()["id"]

    resp2 = await client.post(
        f"/api/v1/marketplace/extractions/{log_id}/reject",
        json={"reason": "Invalid document"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "rejected"


@_skip_no_router
@pytest.mark.asyncio
async def test_operator_queue_api(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/marketplace/operator/queue",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "active_rfqs" in data
    assert "quotes_received" in data


@_skip_no_router
@pytest.mark.asyncio
async def test_comparison_matrix_api(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/marketplace/requests/{fake_id}/comparison-matrix",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["rows"] == []


@_skip_no_router
@pytest.mark.asyncio
async def test_flywheel_metrics_api(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/admin/remediation/flywheel-metrics",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_extractions" in data
    assert "knowledge_density" in data


@_skip_no_router
@pytest.mark.asyncio
async def test_flywheel_metrics_unauthorized(client: AsyncClient, diag_headers: dict):
    resp = await client.get(
        "/api/v1/admin/remediation/flywheel-metrics",
        headers=diag_headers,
    )
    # diagnostician doesn't have audit_logs read permission
    assert resp.status_code == 403


@_skip_no_router
@pytest.mark.asyncio
async def test_company_workspace_not_found_api(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/marketplace/companies/{fake_id}/workspace",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@_skip_no_router
@pytest.mark.asyncio
async def test_completion_closure_not_found_api(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/marketplace/completions/{fake_id}/closure-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 404
