"""Seed 5 requirement profiles for conformance checking.

Idempotent: skips profiles that already exist by name.

Profiles:
1. authority_pack — strict authority submission requirements
2. insurer_pack — insurer-grade requirements
3. transfer — building transfer/handoff requirements
4. import — passport reimport validation requirements
5. publication — public publication requirements
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conformance import RequirementProfile

logger = logging.getLogger(__name__)

PROFILES = [
    {
        "name": "authority_pack",
        "description": (
            "Exigences pour un pack autorite: completude elevee, confiance elevee, "
            "readiness evaluee, aucune contradiction ouverte, sections reglementaires presentes."
        ),
        "profile_type": "pack",
        "required_sections": [
            "passport_summary",
            "completeness_report",
            "readiness_verdict",
            "pollutant_inventory",
            "diagnostic_summary",
            "compliance_status",
            "document_inventory",
        ],
        "required_fields": ["passport_grade", "canton"],
        "minimum_completeness": 0.80,
        "minimum_trust": 0.70,
        "required_readiness": {"safe_to_start": "clear"},
        "max_unknowns": 2,
        "max_contradictions": 0,
        "redaction_allowed": False,
    },
    {
        "name": "insurer_pack",
        "description": (
            "Exigences pour un pack assureur: inventaire polluants, historique risques, "
            "confiance minimale, contradictions limitees."
        ),
        "profile_type": "pack",
        "required_sections": [
            "passport_summary",
            "pollutant_inventory",
            "risk_summary",
            "intervention_history",
            "compliance_status",
            "readiness_verdict",
        ],
        "required_fields": ["passport_grade"],
        "minimum_completeness": 0.60,
        "minimum_trust": 0.60,
        "required_readiness": None,
        "max_unknowns": 5,
        "max_contradictions": 2,
        "redaction_allowed": True,
    },
    {
        "name": "transfer",
        "description": (
            "Exigences pour un transfert de batiment: dossier quasi-complet, "
            "confiance elevee, aucune contradiction, toutes sections requises."
        ),
        "profile_type": "exchange",
        "required_sections": [
            "knowledge_state",
            "completeness",
            "readiness",
            "blind_spots",
            "contradictions",
            "evidence_coverage",
        ],
        "required_fields": ["passport_grade", "address", "canton", "construction_year"],
        "minimum_completeness": 0.85,
        "minimum_trust": 0.75,
        "required_readiness": None,
        "max_unknowns": 3,
        "max_contradictions": 0,
        "redaction_allowed": False,
    },
    {
        "name": "import",
        "description": (
            "Exigences minimales pour un reimport de passeport: champs d'identite obligatoires, completude minimale."
        ),
        "profile_type": "import",
        "required_sections": None,
        "required_fields": ["address", "canton"],
        "minimum_completeness": 0.30,
        "minimum_trust": None,
        "required_readiness": None,
        "max_unknowns": None,
        "max_contradictions": None,
        "redaction_allowed": True,
    },
    {
        "name": "publication",
        "description": (
            "Exigences pour une publication de passeport: completude et confiance "
            "minimales, pas trop d'inconnus, redaction autorisee."
        ),
        "profile_type": "publication",
        "required_sections": [
            "knowledge_state",
            "completeness",
            "readiness",
        ],
        "required_fields": ["passport_grade"],
        "minimum_completeness": 0.50,
        "minimum_trust": 0.50,
        "required_readiness": None,
        "max_unknowns": 10,
        "max_contradictions": 3,
        "redaction_allowed": True,
    },
]


async def seed_conformance_profiles(db: AsyncSession) -> int:
    """Seed default requirement profiles. Returns count of profiles created."""
    created = 0
    for profile_data in PROFILES:
        name = profile_data["name"]
        existing = await db.execute(select(RequirementProfile).where(RequirementProfile.name == name))
        if existing.scalar_one_or_none() is not None:
            continue

        profile = RequirementProfile(**profile_data)
        db.add(profile)
        created += 1
        logger.info("Seeded conformance profile: %s", name)

    if created:
        await db.flush()

    return created
