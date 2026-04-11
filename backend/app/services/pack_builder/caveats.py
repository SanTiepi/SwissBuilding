"""Pack caveats builder.

Generates the caveats (reserves et limites) section for any pack type,
including first-class Caveat records from the commitment graph.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.schemas.pack_builder import PackSection
from app.services.pack_builder.pack_types import _SECTION_NAMES

logger = logging.getLogger(__name__)


async def _build_pack_caveats(
    sections: list[PackSection], building: Building, pack_type: str, db: AsyncSession | None = None
) -> PackSection:
    """Build explicit caveats listing what is NOT covered or NOT verified.

    Includes first-class Caveat records from the database when db is provided.
    """
    caveats: list[dict] = []

    # 1. First-class caveats from the database (Commitment & Caveat graph)
    if db is not None:
        try:
            from app.services.commitment_service import get_caveats_for_pack

            db_caveats = await get_caveats_for_pack(db, building.id, pack_type)
            for c in db_caveats:
                caveats.append(
                    {
                        "caveat_type": c.caveat_type,
                        "message": f"{c.subject}: {c.description}" if c.description else c.subject,
                        "severity": c.severity,
                        "source": "commitment_graph",
                        "caveat_id": str(c.id),
                    }
                )
        except Exception:
            logger.warning("Failed to load first-class caveats for building %s", building.id)

    # Universal liability caveat
    caveats.append(
        {
            "caveat_type": "liability",
            "message": (
                "Ce pack ne constitue pas une garantie de conformite legale. "
                "Il s'agit d'un outil d'aide a la decision base sur les donnees disponibles."
            ),
            "severity": "info",
        }
    )

    # Low-completeness sections
    for s in sections:
        if s.completeness < 0.5 and s.section_type not in ("caveats",):
            caveats.append(
                {
                    "caveat_type": "incomplete_section",
                    "message": f"Section '{s.section_name}' incomplete ({round(s.completeness * 100)}%)",
                    "severity": "warning",
                    "section_type": s.section_type,
                }
            )

    # Building age warning
    if building.construction_year and building.construction_year < 1990:
        caveats.append(
            {
                "caveat_type": "building_age",
                "message": f"Batiment construit en {building.construction_year} — verifier la couverture amiante, PCB et plomb",
                "severity": "info",
            }
        )

    # Missing EGID
    if not building.egid:
        caveats.append(
            {
                "caveat_type": "missing_identity",
                "message": "EGID manquant — identification officielle incomplete",
                "severity": "warning",
            }
        )

    # PFAS caveat
    caveats.append(
        {
            "caveat_type": "regulatory",
            "message": (
                "Le cadre reglementaire PFAS est encore provisoire (OSEC/OFEV). "
                "Les seuils et obligations peuvent evoluer."
            ),
            "severity": "info",
        }
    )

    # Audience-specific caveats
    if pack_type == "notary":
        caveats.append(
            {
                "caveat_type": "transaction",
                "message": (
                    "Ce pack ne remplace pas un due diligence complet. "
                    "Les informations refletent l'etat connu a la date de generation."
                ),
                "severity": "warning",
            }
        )
    elif pack_type == "insurer":
        caveats.append(
            {
                "caveat_type": "insurance",
                "message": (
                    "L'evaluation des risques est basee sur les donnees declarees et les diagnostics disponibles. "
                    "Une inspection complementaire peut etre necessaire."
                ),
                "severity": "info",
            }
        )
    elif pack_type == "contractor":
        caveats.append(
            {
                "caveat_type": "scope",
                "message": (
                    "Le perimetre des travaux doit etre confirme par une visite de chantier. "
                    "Les quantites et conditions reelles peuvent differer."
                ),
                "severity": "warning",
            }
        )

    # Format caveat
    caveats.append(
        {
            "caveat_type": "format",
            "message": "Le pack est genere au format JSON. La generation PDF est prevue dans une version ulterieure.",
            "severity": "info",
        }
    )

    return PackSection(
        section_name=_SECTION_NAMES["caveats"],
        section_type="caveats",
        items=caveats,
        completeness=1.0,
        notes=f"{len(caveats)} reserve(s) identifiee(s)",
    )
