"""Diagnostic Integration — seed demo publications + mission orders.

Run: python -m app.seeds.seed_diagnostic_integration

Creates:
- 1 publication auto_matched (asbestos, Lausanne building with egid)
- 1 publication needs_review (PCB, ambiguous address)
- 1 mission order acknowledged (asbestos_full)
- 1 mission order failed (lead)
- 2 publication versions for the matched publication

Idempotent: uses UUID5 deterministic IDs.
"""

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.diagnostic_mission_order import DiagnosticMissionOrder
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.diagnostic_publication_version import DiagnosticPublicationVersion
from app.models.user import User

# Stable namespace for idempotent IDs
_DI_NS = uuid.UUID("d1a9c0e4-7b3f-4a82-9e15-f8c6d2b04a71")


def _sid(name: str) -> uuid.UUID:
    """Stable UUID5 from a seed-internal name."""
    return uuid.uuid5(_DI_NS, name)


def _hash(content: str) -> str:
    """Deterministic SHA-256 for payload_hash."""
    return hashlib.sha256(content.encode()).hexdigest()


# ── Pre-computed stable IDs ────────────────────────────────────────
ID_PUB_MATCHED = _sid("pub-asbestos-matched")
ID_PUB_REVIEW = _sid("pub-pcb-needs-review")
ID_ORDER_ACK = _sid("order-asbestos-acknowledged")
ID_ORDER_FAILED = _sid("order-lead-failed")
ID_VERSION_1 = _sid("pub-asbestos-version-1")
ID_VERSION_2 = _sid("pub-asbestos-version-2")


async def seed():
    async with AsyncSessionLocal() as db:
        # ── Lookup existing admin + buildings ──────────────────────────
        result = await db.execute(
            select(User).where(User.email == "admin@swissbuildingos.ch")
        )
        admin = result.scalar_one_or_none()
        if not admin:
            print("Diagnostic Integration seed: admin not found — run seed_data first.")
            return

        org_id = admin.organization_id

        # Lausanne building (has address, will set egid for matching)
        bld_lau = (
            await db.execute(
                select(Building).where(Building.address == "Chemin des Pâquerettes 12")
            )
        ).scalar_one_or_none()

        # Geneva building (for mission orders)
        bld_ge = (
            await db.execute(
                select(Building).where(Building.address == "Quai du Rhône 45")
            )
        ).scalar_one_or_none()

        if not all([bld_lau, bld_ge]):
            print("Diagnostic Integration seed: buildings not found — run seed_data first.")
            return

        # ── 1. Publication: auto_matched (asbestos, Lausanne) ──────────
        existing = (
            await db.execute(
                select(DiagnosticReportPublication).where(
                    DiagnosticReportPublication.id == ID_PUB_MATCHED
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(
                DiagnosticReportPublication(
                    id=ID_PUB_MATCHED,
                    building_id=bld_lau.id,
                    source_system="batiscan",
                    source_mission_id="BAT-2025-LAU-0042",
                    current_version=2,
                    match_state="auto_matched",
                    match_key=str(bld_lau.egid) if bld_lau.egid else "1004-pâquerettes-12",
                    match_key_type="egid" if bld_lau.egid else "address",
                    report_pdf_url="/reports/batiscan/BAT-2025-LAU-0042/rapport-amiante-v2.pdf",
                    structured_summary={
                        "pollutants_found": ["asbestos"],
                        "fach_urgency": "medium",
                        "zones": [
                            {
                                "name": "Sous-sol — local technique",
                                "floor": -1,
                                "materials": [
                                    {
                                        "type": "flocage",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 12.5,
                                        "condition": "bon",
                                        "surface_m2": 45.0,
                                    }
                                ],
                            },
                            {
                                "name": "Cage d'escalier — paliers 1-6",
                                "floor": 0,
                                "materials": [
                                    {
                                        "type": "dalles de sol vinyle-amiante",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 8.0,
                                        "condition": "usé",
                                        "surface_m2": 120.0,
                                    }
                                ],
                            },
                            {
                                "name": "Toiture — étanchéité",
                                "floor": 7,
                                "materials": [
                                    {
                                        "type": "membrane bitumineuse",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 5.0,
                                        "condition": "bon",
                                        "surface_m2": 380.0,
                                    }
                                ],
                            },
                        ],
                        "sample_count": 14,
                        "positive_sample_count": 6,
                        "lab": "Suva Luzern",
                        "diagnostician": "Jean-Pierre Müller",
                        "inspection_date": "2025-02-15",
                    },
                    annexes=[
                        {
                            "name": "Plan repérage sous-sol.pdf",
                            "url": "/reports/batiscan/BAT-2025-LAU-0042/annexe-plan-ss.pdf",
                            "type": "plan",
                        },
                        {
                            "name": "Résultats analyses laboratoire.pdf",
                            "url": "/reports/batiscan/BAT-2025-LAU-0042/annexe-labo.pdf",
                            "type": "lab_results",
                        },
                    ],
                    payload_hash=_hash("bat-2025-lau-0042-v2"),
                    mission_type="asbestos_full",
                    published_at=datetime(2025, 3, 10, 14, 30, 0, tzinfo=UTC),
                    source_type="import",
                    confidence="verified",
                    source_ref="batiscan-webhook-2025-03-10",
                )
            )

        # ── 2. Publication: needs_review (PCB, ambiguous address) ──────
        existing = (
            await db.execute(
                select(DiagnosticReportPublication).where(
                    DiagnosticReportPublication.id == ID_PUB_REVIEW
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(
                DiagnosticReportPublication(
                    id=ID_PUB_REVIEW,
                    building_id=None,  # not matched yet
                    source_system="batiscan",
                    source_mission_id="BAT-2025-GE-0107",
                    current_version=1,
                    match_state="needs_review",
                    match_key="1204-quai-rhone-45-47",
                    match_key_type="address",
                    report_pdf_url="/reports/batiscan/BAT-2025-GE-0107/rapport-pcb.pdf",
                    structured_summary={
                        "pollutants_found": ["pcb"],
                        "fach_urgency": "high",
                        "zones": [
                            {
                                "name": "Joints fenêtres — façade nord",
                                "floor": 0,
                                "materials": [
                                    {
                                        "type": "mastic d'étanchéité",
                                        "pcb_concentration_mg_kg": 1250.0,
                                        "threshold_mg_kg": 50.0,
                                        "status": "above_threshold",
                                    }
                                ],
                            },
                            {
                                "name": "Joints fenêtres — façade sud",
                                "floor": 0,
                                "materials": [
                                    {
                                        "type": "mastic d'étanchéité",
                                        "pcb_concentration_mg_kg": 870.0,
                                        "threshold_mg_kg": 50.0,
                                        "status": "above_threshold",
                                    }
                                ],
                            },
                        ],
                        "sample_count": 8,
                        "positive_sample_count": 5,
                        "lab": "EMPA Dübendorf",
                        "diagnostician": "Marc Fontaine",
                        "inspection_date": "2025-03-05",
                        "review_reason": "Address matches two adjacent buildings (45 and 47). Manual EGID confirmation required.",
                    },
                    annexes=None,
                    payload_hash=_hash("bat-2025-ge-0107-v1"),
                    mission_type="pcb",
                    published_at=datetime(2025, 3, 12, 9, 15, 0, tzinfo=UTC),
                    source_type="import",
                    confidence="declared",
                    source_ref="batiscan-webhook-2025-03-12",
                )
            )

        await db.flush()

        # ── 3. Mission order: acknowledged (asbestos_full) ─────────────
        existing = (
            await db.execute(
                select(DiagnosticMissionOrder).where(
                    DiagnosticMissionOrder.id == ID_ORDER_ACK
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(
                DiagnosticMissionOrder(
                    id=ID_ORDER_ACK,
                    building_id=bld_lau.id,
                    requester_org_id=org_id,
                    mission_type="asbestos_full",
                    status="acknowledged",
                    context_notes=(
                        "Diagnostic complet amiante requis avant rénovation "
                        "de la cage d'escalier et remplacement des dalles de sol. "
                        "Bâtiment construit en 1962, dernière rénovation 1988."
                    ),
                    attachments=[
                        {
                            "name": "Cahier des charges travaux.pdf",
                            "url": "/documents/mission-orders/BAT-DEMO-001/cahier-charges.pdf",
                            "type": "specifications",
                        }
                    ],
                    building_identifiers={
                        "egid": str(bld_lau.egid) if bld_lau.egid else None,
                        "egrid": None,
                        "official_id": bld_lau.official_id,
                        "address": "Chemin des Pâquerettes 12, 1004 Lausanne",
                    },
                    external_mission_id="BAT-DEMO-001",
                    source_type="manual",
                    confidence="verified",
                )
            )

        # ── 4. Mission order: failed (lead) ────────────────────────────
        existing = (
            await db.execute(
                select(DiagnosticMissionOrder).where(
                    DiagnosticMissionOrder.id == ID_ORDER_FAILED
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(
                DiagnosticMissionOrder(
                    id=ID_ORDER_FAILED,
                    building_id=bld_ge.id,
                    requester_org_id=org_id,
                    mission_type="lead",
                    status="failed",
                    last_error="Connection refused: Batiscan API unreachable",
                    context_notes=(
                        "Diagnostic plomb requis — peintures anciennes "
                        "dans appartements 2e et 3e étage. "
                        "Bâtiment 1955, jamais rénové."
                    ),
                    attachments=None,
                    building_identifiers={
                        "egid": str(bld_ge.egid) if bld_ge.egid else None,
                        "egrid": None,
                        "official_id": bld_ge.official_id,
                        "address": "Quai du Rhône 45, 1204 Genève",
                    },
                    external_mission_id=None,
                    source_type="manual",
                    confidence="declared",
                )
            )

        await db.flush()

        # ── 5. Publication versions (2 versions for matched pub) ───────
        existing_v1 = (
            await db.execute(
                select(DiagnosticPublicationVersion).where(
                    DiagnosticPublicationVersion.id == ID_VERSION_1
                )
            )
        ).scalar_one_or_none()
        if not existing_v1:
            db.add(
                DiagnosticPublicationVersion(
                    id=ID_VERSION_1,
                    publication_id=ID_PUB_MATCHED,
                    version=1,
                    published_at=datetime(2025, 2, 20, 16, 0, 0, tzinfo=UTC),
                    payload_hash=_hash("bat-2025-lau-0042-v1"),
                    report_pdf_url="/reports/batiscan/BAT-2025-LAU-0042/rapport-amiante-v1.pdf",
                    structured_summary={
                        "pollutants_found": ["asbestos"],
                        "fach_urgency": "low",
                        "zones": [
                            {
                                "name": "Sous-sol — local technique",
                                "floor": -1,
                                "materials": [
                                    {
                                        "type": "flocage",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 12.5,
                                        "condition": "bon",
                                        "surface_m2": 45.0,
                                    }
                                ],
                            },
                        ],
                        "sample_count": 6,
                        "positive_sample_count": 2,
                        "lab": "Suva Luzern",
                        "diagnostician": "Jean-Pierre Müller",
                        "inspection_date": "2025-02-15",
                    },
                    annexes=[
                        {
                            "name": "Plan repérage sous-sol.pdf",
                            "url": "/reports/batiscan/BAT-2025-LAU-0042/annexe-plan-ss.pdf",
                            "type": "plan",
                        },
                    ],
                )
            )

        existing_v2 = (
            await db.execute(
                select(DiagnosticPublicationVersion).where(
                    DiagnosticPublicationVersion.id == ID_VERSION_2
                )
            )
        ).scalar_one_or_none()
        if not existing_v2:
            db.add(
                DiagnosticPublicationVersion(
                    id=ID_VERSION_2,
                    publication_id=ID_PUB_MATCHED,
                    version=2,
                    published_at=datetime(2025, 3, 10, 14, 30, 0, tzinfo=UTC),
                    payload_hash=_hash("bat-2025-lau-0042-v2"),
                    report_pdf_url="/reports/batiscan/BAT-2025-LAU-0042/rapport-amiante-v2.pdf",
                    structured_summary={
                        "pollutants_found": ["asbestos"],
                        "fach_urgency": "medium",
                        "zones": [
                            {
                                "name": "Sous-sol — local technique",
                                "floor": -1,
                                "materials": [
                                    {
                                        "type": "flocage",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 12.5,
                                        "condition": "bon",
                                        "surface_m2": 45.0,
                                    }
                                ],
                            },
                            {
                                "name": "Cage d'escalier — paliers 1-6",
                                "floor": 0,
                                "materials": [
                                    {
                                        "type": "dalles de sol vinyle-amiante",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 8.0,
                                        "condition": "usé",
                                        "surface_m2": 120.0,
                                    }
                                ],
                            },
                            {
                                "name": "Toiture — étanchéité",
                                "floor": 7,
                                "materials": [
                                    {
                                        "type": "membrane bitumineuse",
                                        "asbestos_type": "chrysotile",
                                        "concentration_pct": 5.0,
                                        "condition": "bon",
                                        "surface_m2": 380.0,
                                    }
                                ],
                            },
                        ],
                        "sample_count": 14,
                        "positive_sample_count": 6,
                        "lab": "Suva Luzern",
                        "diagnostician": "Jean-Pierre Müller",
                        "inspection_date": "2025-02-15",
                        "update_note": "8 échantillons supplémentaires prélevés (cage d'escalier + toiture). Urgence relevée de low à medium.",
                    },
                    annexes=[
                        {
                            "name": "Plan repérage sous-sol.pdf",
                            "url": "/reports/batiscan/BAT-2025-LAU-0042/annexe-plan-ss.pdf",
                            "type": "plan",
                        },
                        {
                            "name": "Résultats analyses laboratoire.pdf",
                            "url": "/reports/batiscan/BAT-2025-LAU-0042/annexe-labo.pdf",
                            "type": "lab_results",
                        },
                    ],
                )
            )

        await db.commit()

        print("Diagnostic Integration seed complete:")
        print(f"  Lausanne: {bld_lau.address} ({bld_lau.id})")
        print(f"  Genève:   {bld_ge.address} ({bld_ge.id})")
        print("  Publications: 2 (1 auto_matched, 1 needs_review)")
        print("  Mission orders: 2 (1 acknowledged, 1 failed)")
        print("  Publication versions: 2 (for matched publication)")


if __name__ == "__main__":
    asyncio.run(seed())
