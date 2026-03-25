"""
BatiConnect — Canonical Cycle Seed

Creates ONE complete diagnostic → dossier → RFQ → works → confirmation →
post-works truth → passport update → pack → exchange → acknowledgement cycle.

Demonstrates the FULL LOOP on a single Lausanne building.
Idempotent: can be run multiple times safely (uses stable UUIDs).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact_version import ArtifactVersion
from app.models.audience_pack import AudiencePack
from app.models.award_confirmation import AwardConfirmation
from app.models.building import Building
from app.models.client_request import ClientRequest
from app.models.company_profile import CompanyProfile
from app.models.completion_confirmation import CompletionConfirmation
from app.models.custody_event import CustodyEvent
from app.models.demo_scenario import DemoRunbookStep, DemoScenario
from app.models.diagnostic import Diagnostic
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep
from app.models.pilot_scorecard import PilotMetric, PilotScorecard
from app.models.post_works_link import PostWorksLink
from app.models.proof_delivery import ProofDelivery
from app.models.quote import Quote
from app.models.request_invitation import RequestInvitation
from app.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stable UUIDs for idempotency
# ---------------------------------------------------------------------------
_NS = uuid.UUID("cc000000-1111-2222-3333-444455556666")


def _id(label: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"canonical-cycle-{label}")


# Pre-computed IDs
_BUILDING_ID = _id("building")
_USER_ID = _id("user")
_ORG_ID = _id("org")
_CONTRACTOR_ORG_ID = _id("contractor-org")
_CONTRACTOR_USER_ID = _id("contractor-user")
_COMPANY_PROFILE_ID = _id("company-profile")
_DIAGNOSTIC_ID = _id("diagnostic")
_DIAG_PUB_ID = _id("diag-pub")
_PROCEDURE_ID = _id("procedure")
_CLIENT_REQUEST_ID = _id("client-request")
_INVITATION_ID = _id("invitation")
_QUOTE_ID = _id("quote")
_AWARD_ID = _id("award")
_COMPLETION_ID = _id("completion")
_INTERVENTION_ID = _id("intervention")
_POST_WORKS_ID = _id("post-works")
_PROOF_AUTH_ID = _id("proof-auth")
_PROOF_INSURER_ID = _id("proof-insurer")
_PACK_INSURER_ID = _id("pack-insurer")
_PACK_AUTHORITY_ID = _id("pack-authority")
_AV1_ID = _id("artifact-version-1")
_AV2_ID = _id("artifact-version-2")
_CE1_ID = _id("custody-event-1")
_CE2_ID = _id("custody-event-2")
_CE3_ID = _id("custody-event-3")
_CE4_ID = _id("custody-event-4")
_OBL_COMPLETED_ID = _id("obligation-completed")
_OBL_UPCOMING_ID = _id("obligation-upcoming")
_SCENARIO_ID = _id("demo-scenario")
_SCORECARD_ID = _id("pilot-scorecard")

_STEP_IDS = [_id(f"step-{i}") for i in range(4)]
_RUNBOOK_IDS = [_id(f"runbook-{i}") for i in range(5)]
_METRIC_IDS = [_id(f"metric-{i}") for i in range(4)]

_NOW = datetime.now(UTC)
_30_DAYS_AGO = _NOW - timedelta(days=30)
_60_DAYS_AGO = _NOW - timedelta(days=60)
_90_DAYS_AGO = _NOW - timedelta(days=90)
_7_DAYS_AGO = _NOW - timedelta(days=7)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def _upsert(db: AsyncSession, model_class, id_value: uuid.UUID, **kwargs):
    """Insert or update by primary key."""
    existing = await db.get(model_class, id_value)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        return existing
    obj = model_class(id=id_value, **kwargs)
    db.add(obj)
    return obj


async def seed_canonical_cycle(db: AsyncSession) -> dict:
    """Seed the canonical cycle. Returns summary dict."""
    logger.info("Seeding canonical cycle...")

    # ── 1. User + Org ──────────────────────────────────────────────
    await _upsert(
        db,
        User,
        _USER_ID,
        email="canonical@baticonnect.ch",
        password_hash="$2b$12$LJ3m4ys3Lk0YRqH2B8Hf5OgzA3HK7euGFN/QEbYV5x0HJQK1Vmq6",
        first_name="Canonical",
        last_name="Demo",
        role="admin",
        is_active=True,
        language="fr",
    )

    await _upsert(
        db,
        Organization,
        _ORG_ID,
        name="Régie Canonique SA",
        type="property_management",
        city="Lausanne",
        canton="VD",
    )

    await _upsert(
        db,
        Organization,
        _CONTRACTOR_ORG_ID,
        name="SanaTech Assainissement SA",
        type="contractor",
        city="Lausanne",
        canton="VD",
    )

    await _upsert(
        db,
        User,
        _CONTRACTOR_USER_ID,
        email="contractor@sanatech.ch",
        password_hash="$2b$12$LJ3m4ys3Lk0YRqH2B8Hf5OgzA3HK7euGFN/QEbYV5x0HJQK1Vmq6",
        first_name="Marc",
        last_name="Contractor",
        role="contractor",
        is_active=True,
        language="fr",
        organization_id=_CONTRACTOR_ORG_ID,
    )

    await _upsert(
        db,
        CompanyProfile,
        _COMPANY_PROFILE_ID,
        organization_id=_CONTRACTOR_ORG_ID,
        company_name="SanaTech Assainissement SA",
        contact_email="contractor@sanatech.ch",
        work_categories=["major"],
        canton="VD",
        city="Lausanne",
    )

    await db.flush()

    # ── 2. Building (Lausanne, with EGID) ──────────────────────────
    await _upsert(
        db,
        Building,
        _BUILDING_ID,
        address="Rue du Grand-Pont 12",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        egid=999001,
        construction_year=1965,
        building_type="residential",
        floors_above=6,
        surface_area_m2=1200.0,
        created_by=_USER_ID,
        organization_id=_ORG_ID,
    )
    await db.flush()

    # ── 3. Diagnostic + Publication ────────────────────────────────
    await _upsert(
        db,
        Diagnostic,
        _DIAGNOSTIC_ID,
        building_id=_BUILDING_ID,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=date.today() - timedelta(days=90),
        diagnostician_id=_USER_ID,
    )

    await _upsert(
        db,
        DiagnosticReportPublication,
        _DIAG_PUB_ID,
        building_id=_BUILDING_ID,
        source_system="batiscan",
        source_mission_id="CANON-2026-001",
        match_state="auto_matched",
        match_key_type="egid",
        match_key="999001",
        mission_type="asbestos_full",
        payload_hash=_sha("canonical-diag-pub"),
        published_at=_90_DAYS_AGO,
        structured_summary={
            "pollutant": "asbestos",
            "positive_samples": 3,
            "negative_samples": 12,
            "zones_affected": ["sous-sol", "cage-escalier"],
            "risk_level": "high",
            "recommendation": "Assainissement complet recommandé",
        },
    )
    await db.flush()

    # ── 4. Permit Procedure (approved, 4 steps completed) ─────────
    await _upsert(
        db,
        PermitProcedure,
        _PROCEDURE_ID,
        building_id=_BUILDING_ID,
        procedure_type="suva_notification",
        title="Notification SUVA — Assainissement amiante Grand-Pont 12",
        authority_name="SUVA Lausanne",
        authority_type="federal",
        status="approved",
        submitted_at=_60_DAYS_AGO,
        approved_at=_30_DAYS_AGO,
        reference_number="SUVA-2026-CC-001",
        assigned_org_id=_ORG_ID,
        assigned_user_id=_USER_ID,
    )
    await db.flush()

    step_defs = [
        ("submission", "Soumission du dossier", "completed"),
        ("review", "Examen par la SUVA", "completed"),
        ("complement_response", "Complément fourni", "completed"),
        ("decision", "Décision favorable", "completed"),
    ]
    for i, (stype, title, status) in enumerate(step_defs):
        await _upsert(
            db,
            PermitStep,
            _STEP_IDS[i],
            procedure_id=_PROCEDURE_ID,
            step_type=stype,
            title=title,
            status=status,
            step_order=i + 1,
            completed_at=_60_DAYS_AGO + timedelta(days=i * 7),
        )
    await db.flush()

    # ── 5. RFQ cycle: ClientRequest → Quote → Award ───────────────
    await _upsert(
        db,
        ClientRequest,
        _CLIENT_REQUEST_ID,
        building_id=_BUILDING_ID,
        requester_user_id=_USER_ID,
        requester_org_id=_ORG_ID,
        title="Assainissement amiante — Grand-Pont 12",
        description="Retrait complet de l'amiante dans sous-sol et cage d'escalier",
        pollutant_types=["asbestos"],
        work_category="major",
        estimated_area_m2=350.0,
        status="awarded",
        diagnostic_publication_id=_DIAG_PUB_ID,
        budget_indication="50k_100k",
        published_at=_60_DAYS_AGO,
    )

    await _upsert(
        db,
        RequestInvitation,
        _INVITATION_ID,
        client_request_id=_CLIENT_REQUEST_ID,
        company_profile_id=_COMPANY_PROFILE_ID,
        status="accepted",
        sent_at=_60_DAYS_AGO,
        viewed_at=_60_DAYS_AGO + timedelta(hours=2),
        responded_at=_60_DAYS_AGO + timedelta(days=1),
    )

    await _upsert(
        db,
        Quote,
        _QUOTE_ID,
        client_request_id=_CLIENT_REQUEST_ID,
        company_profile_id=_COMPANY_PROFILE_ID,
        invitation_id=_INVITATION_ID,
        amount_chf=75000,
        validity_days=30,
        description="Offre pour assainissement complet",
        work_plan="Phase 1: Confinement. Phase 2: Retrait. Phase 3: Décontamination.",
        timeline_weeks=6,
        includes=["mobilization", "waste_disposal", "air_monitoring", "final_report"],
        status="awarded",
        submitted_at=_60_DAYS_AGO + timedelta(days=3),
        content_hash=_sha("canonical-quote"),
    )

    await _upsert(
        db,
        AwardConfirmation,
        _AWARD_ID,
        client_request_id=_CLIENT_REQUEST_ID,
        quote_id=_QUOTE_ID,
        company_profile_id=_COMPANY_PROFILE_ID,
        awarded_by_user_id=_USER_ID,
        award_amount_chf=75000,
        conditions="Début des travaux dans les 2 semaines",
        content_hash=_sha("canonical-award"),
        awarded_at=_60_DAYS_AGO + timedelta(days=5),
    )
    await db.flush()

    # ── 6. CompletionConfirmation (fully confirmed) ────────────────
    await _upsert(
        db,
        CompletionConfirmation,
        _COMPLETION_ID,
        award_confirmation_id=_AWARD_ID,
        client_confirmed=True,
        client_confirmed_at=_7_DAYS_AGO,
        client_confirmed_by_user_id=_USER_ID,
        company_confirmed=True,
        company_confirmed_at=_7_DAYS_AGO - timedelta(hours=4),
        company_confirmed_by_user_id=_CONTRACTOR_USER_ID,
        status="fully_confirmed",
        completion_notes="Travaux terminés. Mesures d'air conformes.",
        final_amount_chf=72500,
        content_hash=_sha("canonical-completion"),
    )
    await db.flush()

    # ── 7. Intervention (completed) ────────────────────────────────
    await _upsert(
        db,
        Intervention,
        _INTERVENTION_ID,
        building_id=_BUILDING_ID,
        intervention_type="asbestos_removal",
        title="Retrait amiante sous-sol et cage d'escalier",
        description="Assainissement complet amiante — 350 m²",
        status="completed",
        date_start=date.today() - timedelta(days=42),
        date_end=date.today() - timedelta(days=7),
        contractor_name="SanaTech Assainissement SA",
        contractor_id=_CONTRACTOR_USER_ID,
        cost_chf=72500.0,
        zones_affected=["sous-sol", "cage-escalier"],
        created_by=_USER_ID,
    )
    await db.flush()

    # ── 8. PostWorksLink (finalized, with grade delta) ─────────────
    await _upsert(
        db,
        PostWorksLink,
        _POST_WORKS_ID,
        completion_confirmation_id=_COMPLETION_ID,
        intervention_id=_INTERVENTION_ID,
        status="finalized",
        grade_delta={"before": "D", "after": "B", "improvement": 2},
        trust_delta={"before": 0.35, "after": 0.72},
        completeness_delta={"before": 0.45, "after": 0.82},
        residual_risks=[{"type": "asbestos", "location": "toiture", "severity": "low"}],
        finalized_at=_7_DAYS_AGO + timedelta(hours=2),
        reviewed_by_user_id=_USER_ID,
        reviewed_at=_7_DAYS_AGO + timedelta(hours=3),
    )
    await db.flush()

    # ── 9. Proof Deliveries ────────────────────────────────────────
    await _upsert(
        db,
        ProofDelivery,
        _PROOF_AUTH_ID,
        building_id=_BUILDING_ID,
        target_type="authority_pack",
        target_id=_PACK_AUTHORITY_ID,
        audience="authority",
        delivery_method="email",
        status="acknowledged",
        sent_at=_7_DAYS_AGO,
        delivered_at=_7_DAYS_AGO + timedelta(hours=1),
        acknowledged_at=_7_DAYS_AGO + timedelta(days=1),
        content_hash=_sha("canonical-proof-auth"),
    )

    await _upsert(
        db,
        ProofDelivery,
        _PROOF_INSURER_ID,
        building_id=_BUILDING_ID,
        target_type="audience_pack",
        target_id=_PACK_INSURER_ID,
        audience="insurer",
        delivery_method="download",
        status="delivered",
        sent_at=_7_DAYS_AGO + timedelta(hours=6),
        delivered_at=_7_DAYS_AGO + timedelta(hours=7),
        content_hash=_sha("canonical-proof-insurer"),
    )
    await db.flush()

    # ── 10. Audience Packs ─────────────────────────────────────────
    await _upsert(
        db,
        AudiencePack,
        _PACK_INSURER_ID,
        building_id=_BUILDING_ID,
        pack_type="insurer",
        pack_version=1,
        status="ready",
        generated_by_user_id=_USER_ID,
        sections={
            "building_identity": {"address": "Rue du Grand-Pont 12", "city": "Lausanne"},
            "diagnostics_summary": {"asbestos": "positive", "remediation": "completed"},
            "obligations": {"count": 2},
            "risk_assessment": {"residual": "low"},
        },
        unknowns_summary=[],
        contradictions_summary=[],
        residual_risk_summary=[
            {"risk_type": "asbestos_residual", "description": "Toiture", "mitigation": "Monitoring"}
        ],
        trust_refs=[{"entity_type": "diagnostic", "entity_id": str(_DIAGNOSTIC_ID), "confidence": 0.95}],
        proof_refs=[{"document_id": str(_DIAG_PUB_ID), "label": "Rapport diagnostic", "version": 1}],
        content_hash=_sha("canonical-pack-insurer"),
        generated_at=_7_DAYS_AGO,
    )

    await _upsert(
        db,
        AudiencePack,
        _PACK_AUTHORITY_ID,
        building_id=_BUILDING_ID,
        pack_type="authority",
        pack_version=1,
        status="ready",
        generated_by_user_id=_USER_ID,
        sections={
            "building_identity": {"address": "Rue du Grand-Pont 12", "city": "Lausanne"},
            "diagnostics_summary": {"asbestos": "positive", "remediation": "completed"},
            "permit_history": {"suva": "approved"},
            "post_works": {"grade_delta": "D→B"},
        },
        unknowns_summary=[],
        contradictions_summary=[],
        residual_risk_summary=[],
        trust_refs=[{"entity_type": "diagnostic", "entity_id": str(_DIAGNOSTIC_ID), "confidence": 0.95}],
        proof_refs=[
            {"document_id": str(_DIAG_PUB_ID), "label": "Rapport diagnostic", "version": 1},
            {"document_id": str(_POST_WORKS_ID), "label": "Post-works truth", "version": 1},
        ],
        content_hash=_sha("canonical-pack-authority"),
        generated_at=_7_DAYS_AGO + timedelta(hours=1),
    )
    await db.flush()

    # ── 11. Artifact Versions + Custody Events ─────────────────────
    await _upsert(
        db,
        ArtifactVersion,
        _AV1_ID,
        artifact_type="audience_pack",
        artifact_id=_PACK_INSURER_ID,
        version_number=1,
        content_hash=_sha("canonical-pack-insurer"),
        status="current",
        created_by_user_id=_USER_ID,
        created_at=_7_DAYS_AGO,
    )

    await _upsert(
        db,
        ArtifactVersion,
        _AV2_ID,
        artifact_type="audience_pack",
        artifact_id=_PACK_AUTHORITY_ID,
        version_number=1,
        content_hash=_sha("canonical-pack-authority"),
        status="current",
        created_by_user_id=_USER_ID,
        created_at=_7_DAYS_AGO + timedelta(hours=1),
    )
    await db.flush()

    custody_defs = [
        (_CE1_ID, _AV1_ID, "created", "system", _7_DAYS_AGO),
        (_CE2_ID, _AV1_ID, "delivered", "system", _7_DAYS_AGO + timedelta(hours=6)),
        (_CE3_ID, _AV2_ID, "created", "system", _7_DAYS_AGO + timedelta(hours=1)),
        (_CE4_ID, _AV2_ID, "acknowledged", "authority", _7_DAYS_AGO + timedelta(days=1)),
    ]
    for ce_id, av_id, etype, actor, ts in custody_defs:
        await _upsert(
            db,
            CustodyEvent,
            ce_id,
            artifact_version_id=av_id,
            event_type=etype,
            actor_type=actor,
            occurred_at=ts,
        )
    await db.flush()

    # ── 12. Obligations ────────────────────────────────────────────
    await _upsert(
        db,
        Obligation,
        _OBL_COMPLETED_ID,
        building_id=_BUILDING_ID,
        title="Mesure d'air post-assainissement",
        obligation_type="regulatory_inspection",
        due_date=date.today() - timedelta(days=5),
        status="completed",
        priority="high",
        completed_at=_7_DAYS_AGO,
        responsible_org_id=_CONTRACTOR_ORG_ID,
    )

    await _upsert(
        db,
        Obligation,
        _OBL_UPCOMING_ID,
        building_id=_BUILDING_ID,
        title="Contrôle de suivi amiante — 6 mois",
        obligation_type="diagnostic_followup",
        due_date=date.today() + timedelta(days=180),
        status="upcoming",
        priority="medium",
        recurrence="semi_annual",
    )
    await db.flush()

    # ── 13. Demo Scenario + Runbook ────────────────────────────────
    await _upsert(
        db,
        DemoScenario,
        _SCENARIO_ID,
        scenario_code="canonical_cycle",
        title="Cycle canonique complet — Diagnostic à décision",
        persona_target="property_manager",
        starting_state_description=(
            "Un immeuble à Lausanne avec diagnostic amiante positif, "
            "assainissement complété, et dossier prêt pour échange."
        ),
        reveal_surfaces=["DecisionView", "ControlTower", "PassportCard", "AudiencePack"],
        proof_moment="Post-works grade delta D→B visible in proof chain",
        action_moment="Generate insurer pack from decision view",
        seed_key="canonical_cycle",
        is_active=True,
    )
    await db.flush()

    runbook_defs = [
        ("Ouvrir le Decision View", "Vue unifiée décision — grade B, 0 blocker"),
        ("Vérifier la proof chain", "4 items: diag pub, post-works, 2 deliveries"),
        ("Consulter Audience Readiness → Insurer", "Pack insurer v1 ready, 0 unknowns"),
        ("Consulter Audience Readiness → Authority", "Pack authority v1 ready, acknowledged"),
        ("Vérifier le ROI inline", "Heures économisées, blockers days saved visibles"),
    ]
    for i, (title, desc) in enumerate(runbook_defs):
        await _upsert(
            db,
            DemoRunbookStep,
            _RUNBOOK_IDS[i],
            scenario_id=_SCENARIO_ID,
            step_order=i + 1,
            title=title,
            description=desc,
            expected_ui_state=f"Step {i + 1} visible",
        )
    await db.flush()

    # ── 14. Pilot Scorecard + Metrics ──────────────────────────────
    await _upsert(
        db,
        PilotScorecard,
        _SCORECARD_ID,
        pilot_name="Canonical Cycle Pilot — Lausanne VD",
        pilot_code="canonical_cycle_vd",
        status="active",
        start_date=date.today() - timedelta(days=90),
        target_buildings=1,
        target_users=3,
    )
    await db.flush()

    metric_defs = [
        ("recurring_usage", 5.0, 3.0, "Login frequency over 30 days"),
        ("blocker_clarity", 1.0, 1.0, "All blockers visible in decision view"),
        ("proof_reuse", 3.0, 2.0, "Pack + delivery count"),
        ("trust_gained", 0.72, 0.60, "Trust score after remediation"),
    ]
    for i, (dim, target, current, notes) in enumerate(metric_defs):
        await _upsert(
            db,
            PilotMetric,
            _METRIC_IDS[i],
            scorecard_id=_SCORECARD_ID,
            dimension=dim,
            target_value=target,
            current_value=current,
            notes=notes,
            measured_at=_NOW,
        )

    await db.commit()

    summary = {
        "building_id": str(_BUILDING_ID),
        "building": "Rue du Grand-Pont 12, 1003 Lausanne",
        "diagnostic_publication": str(_DIAG_PUB_ID),
        "permit_procedure": str(_PROCEDURE_ID),
        "client_request": str(_CLIENT_REQUEST_ID),
        "quote": str(_QUOTE_ID),
        "award": str(_AWARD_ID),
        "completion": str(_COMPLETION_ID),
        "intervention": str(_INTERVENTION_ID),
        "post_works_link": str(_POST_WORKS_ID),
        "proof_deliveries": [str(_PROOF_AUTH_ID), str(_PROOF_INSURER_ID)],
        "audience_packs": [str(_PACK_INSURER_ID), str(_PACK_AUTHORITY_ID)],
        "artifact_versions": [str(_AV1_ID), str(_AV2_ID)],
        "custody_events": 4,
        "obligations": [str(_OBL_COMPLETED_ID), str(_OBL_UPCOMING_ID)],
        "demo_scenario": str(_SCENARIO_ID),
        "pilot_scorecard": str(_SCORECARD_ID),
    }
    logger.info("Canonical cycle seeded: %s", summary)
    return summary
