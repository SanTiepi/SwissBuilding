"""
SwissBuildingOS - Remediation Cost Reference Seed
Idempotent seed script with Swiss market averages (2024-2025).

Usage:
    python -m app.seeds.seed_cost_references
"""

import asyncio
import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.remediation_cost_reference import RemediationCostReference

# ---------------------------------------------------------------------------
# Stable UUIDs for idempotent upserts (UUID5 namespace)
# ---------------------------------------------------------------------------
_NS = uuid.UUID("c05t0000-0000-4000-a000-000000000001")

COST_REFERENCES = [
    # ── Asbestos ──────────────────────────────────────────────────────
    {
        "id": uuid.uuid5(_NS, "asbestos-flocage-degrade-depose"),
        "pollutant_type": "asbestos",
        "material_type": "flocage",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 150,
        "cost_per_m2_median": 250,
        "cost_per_m2_max": 350,
        "is_forfait": False,
        "duration_days_estimate": 30,
        "complexity": "complexe",
        "description": "Dépose de flocage amianté — intervention lourde, confinement requis",
    },
    {
        "id": uuid.uuid5(_NS, "asbestos-dalle_vinyle-degrade-depose"),
        "pollutant_type": "asbestos",
        "material_type": "dalle_vinyle",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 50,
        "cost_per_m2_median": 85,
        "cost_per_m2_max": 120,
        "is_forfait": False,
        "duration_days_estimate": 10,
        "complexity": "moyenne",
        "description": "Dépose de dalles vinyle amiantées — retrait mécanique",
    },
    {
        "id": uuid.uuid5(_NS, "asbestos-joint-degrade-depose"),
        "pollutant_type": "asbestos",
        "material_type": "joint",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 80,
        "cost_per_m2_median": 140,
        "cost_per_m2_max": 200,
        "is_forfait": False,
        "duration_days_estimate": 7,
        "complexity": "moyenne",
        "description": "Dépose de joints amiantés — fenêtres, sanitaire, façade",
    },
    {
        "id": uuid.uuid5(_NS, "asbestos-colle-degrade-depose"),
        "pollutant_type": "asbestos",
        "material_type": "colle",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 60,
        "cost_per_m2_median": 100,
        "cost_per_m2_max": 150,
        "is_forfait": False,
        "duration_days_estimate": 10,
        "complexity": "moyenne",
        "description": "Dépose de colle amiantée — carrelage, revêtement de sol",
    },
    {
        "id": uuid.uuid5(_NS, "asbestos-isolation-degrade-depose"),
        "pollutant_type": "asbestos",
        "material_type": "isolation",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 100,
        "cost_per_m2_median": 175,
        "cost_per_m2_max": 250,
        "is_forfait": False,
        "duration_days_estimate": 22,
        "complexity": "complexe",
        "description": "Dépose d'isolation amiantée — calorifuge, gaine technique",
    },
    # ── PCB ───────────────────────────────────────────────────────────
    {
        "id": uuid.uuid5(_NS, "pcb-joint-degrade-depose"),
        "pollutant_type": "pcb",
        "material_type": "joint",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 100,
        "cost_per_m2_median": 175,
        "cost_per_m2_max": 250,
        "is_forfait": False,
        "duration_days_estimate": 15,
        "complexity": "moyenne",
        "description": "Dépose de joints PCB — élastiques de façade, fenêtres",
    },
    {
        "id": uuid.uuid5(_NS, "pcb-peinture-degrade-decapage"),
        "pollutant_type": "pcb",
        "material_type": "peinture",
        "condition": "degrade",
        "method": "decapage",
        "cost_per_m2_min": 80,
        "cost_per_m2_median": 130,
        "cost_per_m2_max": 180,
        "is_forfait": False,
        "duration_days_estimate": 12,
        "complexity": "moyenne",
        "description": "Décapage de peinture contenant des PCB",
    },
    # ── Lead ──────────────────────────────────────────────────────────
    {
        "id": uuid.uuid5(_NS, "lead-peinture-degrade-decapage"),
        "pollutant_type": "lead",
        "material_type": "peinture",
        "condition": "degrade",
        "method": "decapage",
        "cost_per_m2_min": 60,
        "cost_per_m2_median": 105,
        "cost_per_m2_max": 150,
        "is_forfait": False,
        "duration_days_estimate": 7,
        "complexity": "simple",
        "description": "Décapage de peinture au plomb — surfaces intérieures",
    },
    {
        "id": uuid.uuid5(_NS, "lead-enduit-degrade-depose"),
        "pollutant_type": "lead",
        "material_type": "enduit",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 70,
        "cost_per_m2_median": 120,
        "cost_per_m2_max": 170,
        "is_forfait": False,
        "duration_days_estimate": 12,
        "complexity": "moyenne",
        "description": "Dépose d'enduit contenant du plomb",
    },
    # ── HAP ───────────────────────────────────────────────────────────
    {
        "id": uuid.uuid5(_NS, "hap-revetement-degrade-depose"),
        "pollutant_type": "hap",
        "material_type": "revetement",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 80,
        "cost_per_m2_median": 140,
        "cost_per_m2_max": 200,
        "is_forfait": False,
        "duration_days_estimate": 15,
        "complexity": "moyenne",
        "description": "Dépose de revêtement contenant des HAP — étanchéité, bitume",
    },
    # ── Radon ─────────────────────────────────────────────────────────
    {
        "id": uuid.uuid5(_NS, "radon-other-bon-ventilation"),
        "pollutant_type": "radon",
        "material_type": "other",
        "condition": "bon",
        "method": "ventilation",
        "cost_per_m2_min": None,
        "cost_per_m2_median": None,
        "cost_per_m2_max": None,
        "is_forfait": True,
        "forfait_min": 5000,
        "forfait_median": 10000,
        "forfait_max": 15000,
        "duration_days_estimate": 5,
        "complexity": "simple",
        "description": "Installation d'un système de ventilation anti-radon — forfait par bâtiment",
    },
    # ── PFAS ──────────────────────────────────────────────────────────
    {
        "id": uuid.uuid5(_NS, "pfas-other-degrade-depose"),
        "pollutant_type": "pfas",
        "material_type": "other",
        "condition": "degrade",
        "method": "depose",
        "cost_per_m2_min": 100,
        "cost_per_m2_median": 200,
        "cost_per_m2_max": 300,
        "is_forfait": False,
        "duration_days_estimate": 22,
        "complexity": "complexe",
        "description": "Assainissement PFAS — protocole émergent, coûts variables",
    },
]


async def seed_cost_references():
    """Idempotent seed: insert or skip remediation cost references."""
    async with AsyncSessionLocal() as session:
        for ref_data in COST_REFERENCES:
            ref_id = ref_data["id"]
            existing = await session.execute(
                select(RemediationCostReference).where(RemediationCostReference.id == ref_id)
            )
            if existing.scalar_one_or_none() is not None:
                continue
            ref = RemediationCostReference(**{k: v for k, v in ref_data.items() if v is not None or k == "is_forfait"})
            # Ensure nullable fields not in ref_data are set
            for field in (
                "forfait_min",
                "forfait_median",
                "forfait_max",
                "cost_per_m2_min",
                "cost_per_m2_median",
                "cost_per_m2_max",
            ):
                if field not in ref_data or ref_data[field] is None:
                    setattr(ref, field, None)
            session.add(ref)
        await session.commit()
        count = len(COST_REFERENCES)
        print(f"  ✓ Remediation cost references: {count} entries seeded/verified")


if __name__ == "__main__":
    asyncio.run(seed_cost_references())
