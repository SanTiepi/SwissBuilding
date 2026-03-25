"""BatiConnect — Intelligence Stack tests.

Tests: AI provider adapter, extraction lifecycle, pattern learning, readiness advisor,
passport narrative, quote comparison, remediation benchmark, flywheel trends, learning overview.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.ai_feedback import AIFeedback
from app.models.ai_rule_pattern import AIRulePattern
from app.models.compliance_artefact import ComplianceArtefact
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.unknown_issue import UnknownIssue

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org Intelligence",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()
    return org


# ---------------------------------------------------------------------------
# AIRulePattern model
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_ai_rule_pattern(db_session):
    pattern = AIRulePattern(
        id=uuid.uuid4(),
        pattern_type="extraction_rule",
        source_entity_type="extraction",
        rule_key="extraction:confirm:stub-v0",
        rule_definition={"confidence_threshold": 0.8},
        sample_count=5,
        is_active=True,
    )
    db_session.add(pattern)
    await db_session.commit()

    result = await db_session.execute(select(AIRulePattern).where(AIRulePattern.id == pattern.id))
    fetched = result.scalar_one()
    assert fetched.pattern_type == "extraction_rule"
    assert fetched.sample_count == 5
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_ai_rule_pattern_types(db_session):
    for pt in ["extraction_rule", "contradiction_signal", "remediation_outcome", "readiness_hint"]:
        p = AIRulePattern(
            id=uuid.uuid4(),
            pattern_type=pt,
            source_entity_type="test",
            rule_key=f"test:{pt}",
            sample_count=1,
            is_active=True,
        )
        db_session.add(p)
    await db_session.commit()

    result = await db_session.execute(select(AIRulePattern))
    patterns = result.scalars().all()
    assert len(patterns) == 4


# ---------------------------------------------------------------------------
# AI Provider Adapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stub_provider_extract():
    from app.services.ai_provider import StubAIProvider

    provider = StubAIProvider()
    assert provider.provider_name == "stub"
    assert provider.model_version == "stub-v0"

    result = await provider.extract("test input", "quote_pdf")
    assert "fields" in result
    assert "confidence" in result
    assert "ambiguous" in result
    assert "unknown" in result
    assert result["confidence"] > 0


@pytest.mark.asyncio
async def test_stub_provider_completion():
    from app.services.ai_provider import StubAIProvider

    provider = StubAIProvider()
    result = await provider.extract("completion report text", "completion_report")
    assert "completed_items" in result["fields"]
    assert result["confidence"] > 0


@pytest.mark.asyncio
async def test_stub_provider_certificate():
    from app.services.ai_provider import StubAIProvider

    provider = StubAIProvider()
    result = await provider.extract("certificate text", "certificate")
    assert "certificate_type" in result["fields"]
    assert result["confidence"] == 0.90


@pytest.mark.asyncio
async def test_get_ai_provider_returns_stub():
    """Without OPENAI_API_KEY, should return StubAIProvider."""
    import os

    from app.services.ai_provider import get_ai_provider

    old = os.environ.pop("OPENAI_API_KEY", None)
    try:
        provider = get_ai_provider()
        assert provider.provider_name == "stub"
    finally:
        if old:
            os.environ["OPENAI_API_KEY"] = old


# ---------------------------------------------------------------------------
# AI Extraction Service (provider-backed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_quote_data(db_session):
    from app.services.ai_extraction_service import extract_quote_data

    log, draft = await extract_quote_data(db_session, text="Sample quote text")
    assert log.status == "draft"
    assert log.provider_name == "stub"
    assert log.model_version == "stub-v0"
    assert log.prompt_version is not None
    assert log.latency_ms is not None
    assert log.error_message is None
    assert draft.scope_items


@pytest.mark.asyncio
async def test_extract_completion_data(db_session):
    from app.services.ai_extraction_service import extract_completion_data

    log, draft = await extract_completion_data(db_session, text="Completion report text")
    assert log.status == "draft"
    assert log.provider_name == "stub"
    assert draft.completed_items


@pytest.mark.asyncio
async def test_extract_certificate_data(db_session):
    from app.services.ai_extraction_service import extract_certificate_data

    log, _draft = await extract_certificate_data(db_session, input_text="Certificate text")
    assert log.status == "draft"
    assert log.extraction_type == "certificate"
    assert log.provider_name == "stub"


@pytest.mark.asyncio
async def test_extraction_confirm_creates_feedback(db_session, admin_user):
    from app.services.ai_extraction_service import confirm_extraction, extract_quote_data

    log, _ = await extract_quote_data(db_session, text="Quote to confirm")
    confirmed = await confirm_extraction(db_session, log.id, admin_user.id)
    assert confirmed.status == "confirmed"

    fb_result = await db_session.execute(select(AIFeedback).where(AIFeedback.entity_id == log.id))
    feedback = fb_result.scalar_one()
    assert feedback.feedback_type == "confirm"


@pytest.mark.asyncio
async def test_extraction_correct_creates_feedback(db_session, admin_user):
    from app.services.ai_extraction_service import correct_extraction, extract_quote_data

    log, _ = await extract_quote_data(db_session, text="Quote to correct")
    corrected = await correct_extraction(
        db_session, log.id, {"scope_items": ["modified"]}, admin_user.id, notes="Fixed scope"
    )
    assert corrected.status == "corrected"
    assert corrected.output_data == {"scope_items": ["modified"]}


@pytest.mark.asyncio
async def test_extraction_reject(db_session, admin_user):
    from app.services.ai_extraction_service import extract_quote_data, reject_extraction

    log, _ = await extract_quote_data(db_session, text="Quote to reject")
    rejected = await reject_extraction(db_session, log.id, admin_user.id, reason="Bad data")
    assert rejected.status == "rejected"


@pytest.mark.asyncio
async def test_extraction_log_has_provider_columns(db_session):
    from app.services.ai_extraction_service import extract_quote_data

    log, _ = await extract_quote_data(db_session, text="Test provider columns")
    assert hasattr(log, "provider_name")
    assert hasattr(log, "model_version")
    assert hasattr(log, "prompt_version")
    assert hasattr(log, "latency_ms")
    assert hasattr(log, "error_message")


# ---------------------------------------------------------------------------
# Pattern Learning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_pattern_from_confirm(db_session, admin_user):
    from app.services.pattern_learning_service import record_pattern

    fb = AIFeedback(
        id=uuid.uuid4(),
        feedback_type="confirm",
        entity_type="extraction",
        entity_id=uuid.uuid4(),
        ai_model="stub-v0",
        confidence=0.85,
        user_id=admin_user.id,
    )
    db_session.add(fb)
    await db_session.flush()

    pattern = await record_pattern(db_session, fb.id)
    assert pattern is not None
    assert pattern.pattern_type == "extraction_rule"
    assert pattern.sample_count == 1


@pytest.mark.asyncio
async def test_record_pattern_upserts(db_session, admin_user):
    from app.services.pattern_learning_service import record_pattern

    fb1 = AIFeedback(
        id=uuid.uuid4(),
        feedback_type="confirm",
        entity_type="extraction",
        entity_id=uuid.uuid4(),
        ai_model="stub-v0",
        confidence=0.85,
        user_id=admin_user.id,
    )
    db_session.add(fb1)
    await db_session.flush()
    p1 = await record_pattern(db_session, fb1.id)

    fb2 = AIFeedback(
        id=uuid.uuid4(),
        feedback_type="confirm",
        entity_type="extraction",
        entity_id=uuid.uuid4(),
        ai_model="stub-v0",
        confidence=0.90,
        user_id=admin_user.id,
    )
    db_session.add(fb2)
    await db_session.flush()
    p2 = await record_pattern(db_session, fb2.id)

    assert p2.id == p1.id
    assert p2.sample_count == 2


@pytest.mark.asyncio
async def test_record_pattern_from_correct(db_session, admin_user):
    from app.services.pattern_learning_service import record_pattern

    fb = AIFeedback(
        id=uuid.uuid4(),
        feedback_type="correct",
        entity_type="extraction",
        entity_id=uuid.uuid4(),
        original_output={"scope_items": ["a"]},
        corrected_output={"scope_items": ["b"]},
        ai_model="stub-v0",
        confidence=0.7,
        user_id=admin_user.id,
    )
    db_session.add(fb)
    await db_session.flush()

    pattern = await record_pattern(db_session, fb.id)
    assert pattern is not None
    assert "corrections" in (pattern.rule_definition or {})


@pytest.mark.asyncio
async def test_record_pattern_ignores_reject(db_session, admin_user):
    from app.services.pattern_learning_service import record_pattern

    fb = AIFeedback(
        id=uuid.uuid4(),
        feedback_type="reject",
        entity_type="extraction",
        entity_id=uuid.uuid4(),
        ai_model="stub-v0",
        confidence=0.3,
        user_id=admin_user.id,
    )
    db_session.add(fb)
    await db_session.flush()

    pattern = await record_pattern(db_session, fb.id)
    assert pattern is None


@pytest.mark.asyncio
async def test_get_patterns(db_session):
    from app.services.pattern_learning_service import get_patterns

    for i in range(3):
        db_session.add(
            AIRulePattern(
                id=uuid.uuid4(),
                pattern_type="extraction_rule",
                source_entity_type="extraction",
                rule_key=f"test:pattern:{i}",
                sample_count=i + 1,
                is_active=True,
            )
        )
    await db_session.flush()

    patterns = await get_patterns(db_session, pattern_type_filter="extraction_rule")
    assert len(patterns) == 3
    assert patterns[0].sample_count >= patterns[1].sample_count


@pytest.mark.asyncio
async def test_get_pattern_stats(db_session):
    from app.services.pattern_learning_service import get_pattern_stats

    db_session.add(
        AIRulePattern(
            id=uuid.uuid4(),
            pattern_type="extraction_rule",
            source_entity_type="test",
            rule_key="stats:test",
            sample_count=10,
            is_active=True,
        )
    )
    await db_session.flush()

    stats = await get_pattern_stats(db_session)
    assert stats["total_patterns"] >= 1
    assert "by_type" in stats
    assert stats["avg_sample_count"] > 0


# ---------------------------------------------------------------------------
# Readiness Advisor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readiness_advisor_no_building(db_session):
    from app.services.readiness_advisor_service import get_suggestions

    suggestions = await get_suggestions(db_session, uuid.uuid4())
    assert suggestions == []


@pytest.mark.asyncio
async def test_readiness_advisor_with_unknowns(db_session, sample_building):
    from app.services.readiness_advisor_service import get_suggestions

    db_session.add(
        UnknownIssue(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            unknown_type="missing_sample",
            title="Missing sample data",
            description="Test unknown",
            status="open",
        )
    )
    await db_session.flush()

    suggestions = await get_suggestions(db_session, sample_building.id)
    blockers = [s for s in suggestions if s.type == "blocker"]
    assert len(blockers) >= 1


@pytest.mark.asyncio
async def test_readiness_advisor_missing_pollutants(db_session, admin_user):
    """Building with no diagnostics should show 5 missing pollutant suggestions."""
    from app.models.building import Building
    from app.services.readiness_advisor_service import get_suggestions

    bld = Building(
        id=uuid.uuid4(),
        address="Rue Intelligence 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()

    suggestions = await get_suggestions(db_session, bld.id)
    missing = [s for s in suggestions if s.type == "missing_pollutant"]
    assert len(missing) == 5


@pytest.mark.asyncio
async def test_readiness_advisor_proof_gaps(db_session, sample_building):
    from app.services.readiness_advisor_service import get_suggestions

    db_session.add(
        ComplianceArtefact(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            artefact_type="clearance_certificate",
            title="Test artefact",
            status="draft",
        )
    )
    await db_session.flush()

    suggestions = await get_suggestions(db_session, sample_building.id)
    proof_gaps = [s for s in suggestions if s.type == "proof_gap"]
    assert len(proof_gaps) >= 1


# ---------------------------------------------------------------------------
# Passport Narrative
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_passport_narrative_building_not_found(db_session):
    from app.services.passport_narrative_service import generate_narrative

    result = await generate_narrative(db_session, uuid.uuid4(), "owner")
    assert result.sections[0].title == "Building Not Found"


@pytest.mark.asyncio
async def test_passport_narrative_owner(db_session, admin_user):
    from app.models.building import Building
    from app.services.passport_narrative_service import generate_narrative

    bld = Building(
        id=uuid.uuid4(),
        address="Rue Narrative 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()

    result = await generate_narrative(db_session, bld.id, "owner")
    assert result.audience == "owner"
    assert len(result.sections) >= 4
    assert any("Identity" in s.title for s in result.sections)


@pytest.mark.asyncio
async def test_passport_narrative_authority(db_session, admin_user):
    from app.models.building import Building
    from app.services.passport_narrative_service import generate_narrative

    bld = Building(
        id=uuid.uuid4(),
        address="Rue Auth 1",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=1980,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()

    result = await generate_narrative(db_session, bld.id, "authority")
    assert result.audience == "authority"
    diag_section = [s for s in result.sections if "Diagnostic" in s.title]
    assert len(diag_section) >= 1


@pytest.mark.asyncio
async def test_passport_narrative_contractor(db_session, admin_user):
    from app.models.building import Building
    from app.services.passport_narrative_service import generate_narrative

    bld = Building(
        id=uuid.uuid4(),
        address="Rue Contractor 1",
        postal_code="3000",
        city="Bern",
        canton="BE",
        construction_year=1960,
        building_type="industrial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()

    result = await generate_narrative(db_session, bld.id, "contractor")
    assert result.audience == "contractor"


@pytest.mark.asyncio
async def test_passport_narrative_invalid_audience_defaults(db_session, admin_user):
    from app.models.building import Building
    from app.services.passport_narrative_service import generate_narrative

    bld = Building(
        id=uuid.uuid4(),
        address="Rue Default 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()

    result = await generate_narrative(db_session, bld.id, "invalid")
    assert result.audience == "owner"


# ---------------------------------------------------------------------------
# Quote Intelligence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_comparison_no_quotes(db_session):
    from app.services.quote_intelligence_service import get_comparison_insights

    result = await get_comparison_insights(db_session, uuid.uuid4())
    assert result.quote_count == 0
    assert result.scope_coverage_matrix == []


# ---------------------------------------------------------------------------
# Remediation Intelligence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_benchmark_no_buildings(db_session):
    from app.services.remediation_intelligence_service import get_benchmark

    result = await get_benchmark(db_session, uuid.uuid4())
    assert result.overall_avg_cost_chf == 0.0
    assert result.benchmarks == []


@pytest.mark.asyncio
async def test_benchmark_with_interventions(db_session, admin_user):
    from app.services.remediation_intelligence_service import get_benchmark

    org = await _make_org(db_session)

    from app.models.building import Building

    bld = Building(
        id=uuid.uuid4(),
        address="Rue Bench 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        organization_id=org.id,
        status="active",
    )
    db_session.add(bld)
    await db_session.flush()

    for i in range(3):
        db_session.add(
            Intervention(
                id=uuid.uuid4(),
                building_id=bld.id,
                intervention_type="asbestos_removal",
                title=f"Test intervention {i}",
                description=f"Test intervention {i}",
                status="completed" if i < 2 else "planned",
                cost_chf=10000 + i * 5000,
            )
        )
    await db_session.flush()

    result = await get_benchmark(db_session, org.id)
    assert len(result.benchmarks) >= 1
    assert result.overall_completion_rate > 0


@pytest.mark.asyncio
async def test_knowledge_density(db_session):
    from app.services.remediation_intelligence_service import get_knowledge_density

    density = await get_knowledge_density(db_session, uuid.uuid4())
    assert isinstance(density, float)
    assert density == 0.0


@pytest.mark.asyncio
async def test_flywheel_trends(db_session):
    from app.services.remediation_intelligence_service import get_flywheel_trends

    trends = await get_flywheel_trends(db_session, uuid.uuid4(), days=90)
    assert isinstance(trends, list)


@pytest.mark.asyncio
async def test_learning_overview(db_session):
    from app.services.remediation_intelligence_service import get_learning_overview

    overview = await get_learning_overview(db_session)
    assert overview.total_patterns >= 0
    assert 0 <= overview.extraction_success_rate <= 1
    assert overview.total_extractions >= 0


# ---------------------------------------------------------------------------
# Domain Event Projector handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_projector_ai_feedback_handler(db_session, admin_user):
    from app.models.domain_event import DomainEvent
    from app.services.domain_event_projector import project_event

    fb = AIFeedback(
        id=uuid.uuid4(),
        feedback_type="confirm",
        entity_type="extraction",
        entity_id=uuid.uuid4(),
        ai_model="stub-v0",
        confidence=0.85,
        user_id=admin_user.id,
    )
    db_session.add(fb)
    await db_session.flush()

    from datetime import UTC, datetime

    event = DomainEvent(
        id=uuid.uuid4(),
        event_type="ai_feedback_recorded",
        aggregate_type="ai_feedback",
        aggregate_id=fb.id,
        payload={"feedback_id": str(fb.id)},
        occurred_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.flush()

    count = await project_event(db_session, event)
    assert count >= 1

    result = await db_session.execute(select(AIRulePattern))
    patterns = result.scalars().all()
    assert len(patterns) >= 1


@pytest.mark.asyncio
async def test_projector_post_works_finalized_creates_pattern(db_session):
    from app.models.domain_event import DomainEvent
    from app.services.domain_event_projector import project_event

    intv_id = uuid.uuid4()
    from datetime import UTC, datetime

    event = DomainEvent(
        id=uuid.uuid4(),
        event_type="remediation_post_works_finalized",
        aggregate_type="intervention",
        aggregate_id=intv_id,
        payload={"intervention_id": str(intv_id), "verification_rate": 0.95},
        occurred_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.flush()

    count = await project_event(db_session, event)
    assert count >= 2

    result = await db_session.execute(select(AIRulePattern).where(AIRulePattern.pattern_type == "remediation_outcome"))
    patterns = result.scalars().all()
    assert len(patterns) >= 1


# ---------------------------------------------------------------------------
# API endpoints (smoke tests)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_extract_quote(client, auth_headers):
    resp = await client.post(
        "/api/v1/extractions/quote",
        json={"text": "Test quote"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["extraction_type"] == "quote_pdf"
    assert data["provider_name"] == "stub"


@pytest.mark.asyncio
async def test_api_extract_completion(client, auth_headers):
    resp = await client.post(
        "/api/v1/extractions/completion",
        json={"text": "Completion report"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["extraction_type"] == "completion_report"


@pytest.mark.asyncio
async def test_api_extract_certificate(client, auth_headers):
    resp = await client.post(
        "/api/v1/extractions/certificate",
        json={"text": "Certificate text"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["extraction_type"] == "certificate"


@pytest.mark.asyncio
async def test_api_list_patterns(client, auth_headers):
    resp = await client.get("/api/v1/ai-patterns", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_pattern_stats(client, auth_headers):
    resp = await client.get("/api/v1/ai-patterns/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_patterns" in data


@pytest.mark.asyncio
async def test_api_readiness_advisor(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/readiness-advisor",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data


@pytest.mark.asyncio
async def test_api_passport_narrative(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/passport-narrative?audience=owner",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "sections" in data
    assert data["audience"] == "owner"


@pytest.mark.asyncio
async def test_api_comparison_insights(client, auth_headers):
    rid = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/marketplace/requests/{rid}/comparison-insights",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["quote_count"] == 0


@pytest.mark.asyncio
async def test_api_remediation_benchmark(client, auth_headers):
    oid = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/organizations/{oid}/remediation-benchmark",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "benchmarks" in data


@pytest.mark.asyncio
async def test_api_flywheel_trends(client, auth_headers):
    oid = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/organizations/{oid}/flywheel-trends",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_learning_overview(client, auth_headers):
    resp = await client.get("/api/v1/admin/module-learning-overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_patterns" in data
