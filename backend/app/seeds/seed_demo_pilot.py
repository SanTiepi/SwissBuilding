"""BatiConnect — Idempotent seed for Demo Scenarios, Pilot Scorecards, and Case Study Templates.

Seeds:
- 2 DemoScenarios with 4-5 runbook steps each
- 1 PilotScorecard with 4 metrics
- 3 CaseStudyTemplates
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case_study_template import CaseStudyTemplate
from app.models.demo_scenario import DemoRunbookStep, DemoScenario
from app.models.pilot_scorecard import PilotMetric, PilotScorecard

logger = logging.getLogger(__name__)

# Stable UUIDs for idempotency
_NS = uuid.UUID("d1e2f3a4-b5c6-7890-abcd-ef9876543210")

_SCENARIO_IDS = {
    "property_manager_flow": uuid.uuid5(_NS, "demo-scenario-pm-flow"),
    "authority_ready_flow": uuid.uuid5(_NS, "demo-scenario-authority-ready"),
}

_SCORECARD_ID = uuid.uuid5(_NS, "pilot-vd-q2-2026")

_TEMPLATE_IDS = {
    "understand_building": uuid.uuid5(_NS, "case-study-understand-building"),
    "produce_dossier": uuid.uuid5(_NS, "case-study-produce-dossier"),
    "handle_complement": uuid.uuid5(_NS, "case-study-handle-complement"),
}


async def seed_demo_pilot(db: AsyncSession) -> None:
    """Seed demo/pilot data idempotently."""
    await _seed_demo_scenarios(db)
    await _seed_pilot_scorecard(db)
    await _seed_case_study_templates(db)
    await db.commit()
    logger.info("seed_demo_pilot: seeded demo scenarios, pilot scorecard, case study templates")


async def _seed_demo_scenarios(db: AsyncSession) -> None:
    # ---- Scenario 1: Property Manager Flow ----
    scenario_id = _SCENARIO_IDS["property_manager_flow"]
    existing = await db.execute(select(DemoScenario).where(DemoScenario.id == scenario_id))
    if existing.scalar_one_or_none() is None:
        scenario = DemoScenario(
            id=scenario_id,
            scenario_code="pm-daily-flow",
            title="Property Manager Daily Workflow",
            persona_target="property_manager",
            starting_state_description=(
                "A property manager manages 12 buildings across Lausanne. "
                "One building has an upcoming SUVA inspection deadline, two have expiring leases, "
                "and a complement request arrived from the cantonal authority."
            ),
            reveal_surfaces=["ControlTower", "ProcedureCard", "PassportCard"],
            proof_moment="The manager sees all blockers on the Control Tower and resolves the complement in 2 clicks.",
            action_moment="Open Control Tower → click complement request → attach proof → submit response.",
            seed_key="seed_demo_authority",
            is_active=True,
        )
        db.add(scenario)

        steps = [
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "pm-flow-step-1"),
                scenario_id=scenario_id,
                step_order=1,
                title="Open Control Tower",
                description="Show the unified dashboard with all buildings and their status signals.",
                expected_ui_state="Control Tower with 12 buildings, 3 flagged",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "pm-flow-step-2"),
                scenario_id=scenario_id,
                step_order=2,
                title="Review complement request",
                description="Click on the building with the complement request to see the authority demand.",
                expected_ui_state="ProcedureCard showing complement_requested status",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "pm-flow-step-3"),
                scenario_id=scenario_id,
                step_order=3,
                title="Attach existing proof",
                description="Show that the required document already exists in the vault — reuse it.",
                expected_ui_state="Document picker with matching proof highlighted",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "pm-flow-step-4"),
                scenario_id=scenario_id,
                step_order=4,
                title="Submit response to authority",
                description="One-click submit the response with attached proof.",
                expected_ui_state="Procedure status changes to under_review",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "pm-flow-step-5"),
                scenario_id=scenario_id,
                step_order=5,
                title="Check building passport grade",
                description="Show the passport card with updated completeness after proof submission.",
                expected_ui_state="PassportCard with grade B, completeness 92%",
                fallback_notes="If passport not computed, show completeness tab instead.",
            ),
        ]
        db.add_all(steps)

    # ---- Scenario 2: Authority-Ready Flow ----
    scenario_id = _SCENARIO_IDS["authority_ready_flow"]
    existing = await db.execute(select(DemoScenario).where(DemoScenario.id == scenario_id))
    if existing.scalar_one_or_none() is None:
        scenario = DemoScenario(
            id=scenario_id,
            scenario_code="authority-ready-flow",
            title="Authority-Ready Dossier Assembly",
            persona_target="owner",
            starting_state_description=(
                "A building owner needs to submit a renovation dossier to the cantonal authority. "
                "The building has completed diagnostics but the dossier has gaps: "
                "missing waste disposal plan and incomplete SUVA notification."
            ),
            reveal_surfaces=["PassportCard", "AuthorityRoom", "ProcedureCard", "ControlTower"],
            proof_moment="The owner sees the passport grade jump from D to B after filling the last gap.",
            action_moment="Open Passport → identify gaps → upload waste plan → submit SUVA notification.",
            seed_key="seed_demo_authority",
            is_active=True,
        )
        db.add(scenario)

        steps = [
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "authority-flow-step-1"),
                scenario_id=scenario_id,
                step_order=1,
                title="Open Building Passport",
                description="Show the current passport grade (D) with identified gaps.",
                expected_ui_state="PassportCard grade D, 2 gaps highlighted in red",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "authority-flow-step-2"),
                scenario_id=scenario_id,
                step_order=2,
                title="Upload waste disposal plan",
                description="Upload the waste plan document and link it to the intervention.",
                expected_ui_state="Document uploaded, gap 1 resolved",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "authority-flow-step-3"),
                scenario_id=scenario_id,
                step_order=3,
                title="Complete SUVA notification",
                description="Fill in the SUVA notification form using pre-populated diagnostic data.",
                expected_ui_state="SUVA notification form with auto-filled fields",
            ),
            DemoRunbookStep(
                id=uuid.uuid5(_NS, "authority-flow-step-4"),
                scenario_id=scenario_id,
                step_order=4,
                title="Submit dossier to authority",
                description="Generate the authority pack and submit it.",
                expected_ui_state="Passport grade now B, completeness 95%",
            ),
        ]
        db.add_all(steps)


async def _seed_pilot_scorecard(db: AsyncSession) -> None:
    existing = await db.execute(select(PilotScorecard).where(PilotScorecard.id == _SCORECARD_ID))
    if existing.scalar_one_or_none() is not None:
        return

    scorecard = PilotScorecard(
        id=_SCORECARD_ID,
        pilot_name="Vaud Pilot Q2 2026",
        pilot_code="vd-pilot-q2-2026",
        status="active",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 30),
        target_buildings=20,
        target_users=8,
    )
    db.add(scorecard)

    now = datetime.now(UTC)
    metrics = [
        PilotMetric(
            id=uuid.uuid5(_NS, "pilot-metric-recurring-usage"),
            scorecard_id=_SCORECARD_ID,
            dimension="recurring_usage",
            target_value=80.0,
            current_value=0.0,
            evidence_source="login_events + page_views",
            notes="% of users logging in at least 3x/week",
            measured_at=now,
        ),
        PilotMetric(
            id=uuid.uuid5(_NS, "pilot-metric-blocker-clarity"),
            scorecard_id=_SCORECARD_ID,
            dimension="blocker_clarity",
            target_value=90.0,
            current_value=0.0,
            evidence_source="control_tower + obligation status",
            notes="% of buildings with all blockers visible on Control Tower",
            measured_at=now,
        ),
        PilotMetric(
            id=uuid.uuid5(_NS, "pilot-metric-proof-reuse"),
            scorecard_id=_SCORECARD_ID,
            dimension="proof_reuse",
            target_value=50.0,
            current_value=0.0,
            evidence_source="proof_deliveries",
            notes="% of proof deliveries that reuse existing documents",
            measured_at=now,
        ),
        PilotMetric(
            id=uuid.uuid5(_NS, "pilot-metric-trust-gained"),
            scorecard_id=_SCORECARD_ID,
            dimension="trust_gained",
            target_value=70.0,
            current_value=0.0,
            evidence_source="trust_scores",
            notes="% of buildings with trust score >= 0.7",
            measured_at=now,
        ),
    ]
    db.add_all(metrics)


async def _seed_case_study_templates(db: AsyncSession) -> None:
    templates = [
        {
            "id": _TEMPLATE_IDS["understand_building"],
            "template_code": "cs-understand-building",
            "title": "Comprendre l'etat d'un batiment en 10 minutes",
            "persona_target": "property_manager",
            "workflow_type": "understand_building",
            "narrative_structure": {
                "before": "Le gerant recoit un nouveau mandat pour un immeuble de 1965. Aucune info structuree.",
                "trigger": "Il ouvre BatiConnect et importe les documents existants (rapports diagnostic, plans).",
                "after": "En 10 minutes, il a un passeport batiment grade C avec les zones a risque identifiees.",
                "proof_points": [
                    "Passeport genere automatiquement",
                    "Zones amiante identifiees sur plan",
                    "Score de confiance 0.6 (donnees declarees)",
                ],
            },
            "evidence_requirements": [
                {"type": "diagnostic_report", "source": "documents", "required": True},
                {"type": "building_passport", "source": "passport_service", "required": True},
                {"type": "trust_score", "source": "trust_scores", "required": False},
            ],
            "is_active": True,
        },
        {
            "id": _TEMPLATE_IDS["produce_dossier"],
            "template_code": "cs-produce-dossier",
            "title": "Assembler un dossier autorite en 2 heures",
            "persona_target": "owner",
            "workflow_type": "produce_dossier",
            "narrative_structure": {
                "before": "Le proprietaire doit soumettre un dossier SUVA pour des travaux de desamiantage.",
                "trigger": "Il utilise BatiConnect pour assembler le pack autorite a partir des preuves existantes.",
                "after": "Le dossier est complet, signe et soumis en 2h au lieu de 2 semaines.",
                "proof_points": [
                    "Pack autorite genere avec toutes les pieces",
                    "Notification SUVA pre-remplie",
                    "Historique d'evidence complete et tracable",
                ],
            },
            "evidence_requirements": [
                {"type": "diagnostic_report", "source": "documents", "required": True},
                {"type": "suva_notification", "source": "compliance_artefacts", "required": True},
                {"type": "waste_plan", "source": "documents", "required": True},
                {"type": "authority_pack", "source": "evidence_packs", "required": True},
            ],
            "is_active": True,
        },
        {
            "id": _TEMPLATE_IDS["handle_complement"],
            "template_code": "cs-handle-complement",
            "title": "Repondre a un complement d'autorite en 30 minutes",
            "persona_target": "property_manager",
            "workflow_type": "handle_complement",
            "narrative_structure": {
                "before": "L'autorite cantonale demande un complement: rapport d'analyse PCB manquant.",
                "trigger": "Le gerant ouvre la demande dans BatiConnect, voit que le rapport existe deja dans le vault.",
                "after": "Il attache le document existant et repond en 30 minutes au lieu de relancer le diagnostiqueur.",
                "proof_points": [
                    "Complement identifie automatiquement",
                    "Document existant retrouve dans le vault",
                    "Reponse tracee avec preuve de livraison",
                ],
            },
            "evidence_requirements": [
                {"type": "authority_request", "source": "authority_requests", "required": True},
                {"type": "existing_document", "source": "documents", "required": True},
                {"type": "proof_delivery", "source": "proof_deliveries", "required": True},
            ],
            "is_active": True,
        },
    ]

    for tpl_data in templates:
        existing = await db.execute(select(CaseStudyTemplate).where(CaseStudyTemplate.id == tpl_data["id"]))
        if existing.scalar_one_or_none() is None:
            db.add(CaseStudyTemplate(**tpl_data))
