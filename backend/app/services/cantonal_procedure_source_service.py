"""Cantonal procedure source adapter — provides authority context, portals, filing requirements."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.source_registry_service import SourceRegistryService

logger = logging.getLogger(__name__)

# Schema validation: required fields for authority entries and filing requirements
_REQUIRED_AUTHORITY_FIELDS: list[str] = ["name"]
# An authority must have at least portal or email for contact
_AUTHORITY_CONTACT_FIELDS: list[str] = ["portal", "email"]
_REQUIRED_FILING_FIELDS: list[str] = ["procedure", "authority", "required_documents"]

# Cache TTL — authority info changes infrequently
CACHE_TTL_DAYS = 30

# ---------------------------------------------------------------------------
# Cantonal authority catalogues
# ---------------------------------------------------------------------------
CANTONAL_AUTHORITIES: dict[str, dict[str, dict[str, Any]]] = {
    "VD": {
        "environment": {
            "name": "DGE-DIREV",
            "full_name": "Direction generale de l'environnement — Division sols, carrieres et dechets",
            "portal": "https://www.vd.ch/dge",
            "filing": "portal",
            "email": "info.dge@vd.ch",
            "phone": "+41 21 316 43 60",
        },
        "construction": {
            "name": "CAMAC",
            "full_name": "Centrale des autorisations en matiere de construction",
            "portal": "https://www.vd.ch/camac",
            "filing": "portal",
            "email": "info.camac@vd.ch",
        },
        "heritage": {
            "name": "Section monuments et sites",
            "full_name": "Section monuments et sites — DGIP",
            "portal": "https://www.vd.ch/monuments-sites",
            "filing": "email",
            "email": "monuments@vd.ch",
        },
        "energy": {
            "name": "DGE-DIREN",
            "full_name": "Direction generale de l'environnement — Division energie",
            "portal": "https://www.vd.ch/energie",
            "filing": "portal",
            "email": "info.energie@vd.ch",
        },
        "health": {
            "name": "DSAS — Unite radioprotection",
            "full_name": "Departement de la sante et de l'action sociale",
            "portal": "https://www.vd.ch/sante",
            "filing": "email",
            "email": "radioprotection@vd.ch",
        },
    },
    "GE": {
        "environment": {
            "name": "OCEV",
            "full_name": "Office cantonal de l'eau et des dechets",
            "portal": "https://www.ge.ch/ocev",
            "filing": "portal",
            "email": "ocev@etat.ge.ch",
        },
        "construction": {
            "name": "Office des autorisations de construire",
            "full_name": "Office des autorisations de construire — DT",
            "portal": "https://www.ge.ch/autorisations-construire",
            "filing": "portal",
            "email": "oac@etat.ge.ch",
        },
        "heritage": {
            "name": "Office du patrimoine et des sites",
            "full_name": "Office du patrimoine et des sites — DT",
            "portal": "https://www.ge.ch/patrimoine",
            "filing": "portal",
            "email": "patrimoine@etat.ge.ch",
        },
        "energy": {
            "name": "OCEN",
            "full_name": "Office cantonal de l'energie",
            "portal": "https://www.ge.ch/ocen",
            "filing": "portal",
            "email": "ocen@etat.ge.ch",
        },
    },
    "FR": {
        "environment": {
            "name": "SEn",
            "full_name": "Service de l'environnement",
            "portal": "https://www.fr.ch/sen",
            "filing": "friac",
            "email": "sen@fr.ch",
        },
        "construction": {
            "name": "SeCa",
            "full_name": "Service des constructions et de l'amenagement",
            "portal": "https://www.fr.ch/seca",
            "filing": "friac",
            "email": "seca@fr.ch",
        },
        "heritage": {
            "name": "SABC",
            "full_name": "Service des biens culturels",
            "portal": "https://www.fr.ch/sabc",
            "filing": "friac",
            "email": "sabc@fr.ch",
        },
        "energy": {
            "name": "SdE",
            "full_name": "Service de l'energie",
            "portal": "https://www.fr.ch/energie",
            "filing": "friac",
            "email": "sde@fr.ch",
        },
    },
}

# ---------------------------------------------------------------------------
# Filing requirements per canton and procedure type
# ---------------------------------------------------------------------------
FILING_REQUIREMENTS: dict[str, dict[str, dict[str, Any]]] = {
    "VD": {
        "demolition_permit": {
            "procedure": "Demande de permis de demolir",
            "authority": "CAMAC",
            "portal": "https://www.vd.ch/camac",
            "filing_method": "portal",
            "required_documents": [
                "Formulaire de demande CAMAC",
                "Plans de situation",
                "Diagnostic polluants (amiante, PCB, plomb, HAP)",
                "Plan d'elimination des dechets",
                "Preavis monuments historiques (si classe/inventorie)",
            ],
            "typical_delay_days": 60,
            "fee_chf": 500,
        },
        "asbestos_notification": {
            "procedure": "Annonce de travaux avec amiante",
            "authority": "SUVA + DGE-DIREV",
            "portal": "https://www.suva.ch/fr/annonce-travaux-amiante",
            "filing_method": "portal",
            "required_documents": [
                "Formulaire SUVA annonce amiante",
                "Diagnostic amiante (diagnostiqueur agree)",
                "Plan de travaux et mesures de protection",
                "Plan d'elimination des dechets",
            ],
            "typical_delay_days": 30,
            "fee_chf": 0,
        },
        "energy_subsidy": {
            "procedure": "Demande de subvention Programme Batiments",
            "authority": "DGE-DIREN",
            "portal": "https://www.vd.ch/energie/subventions",
            "filing_method": "portal",
            "required_documents": [
                "CECB ou audit energetique",
                "Devis des travaux",
                "Formulaire de demande cantonal",
                "Photos de l'etat existant",
            ],
            "typical_delay_days": 45,
            "fee_chf": 0,
            "note": "Accord prealable obligatoire AVANT debut des travaux",
        },
        "construction_permit": {
            "procedure": "Permis de construire",
            "authority": "CAMAC",
            "portal": "https://www.vd.ch/camac",
            "filing_method": "portal",
            "required_documents": [
                "Formulaire CAMAC",
                "Plans d'architecte",
                "Diagnostic polluants",
                "Descriptif du projet",
                "Rapport energetique (si renovation lourde)",
            ],
            "typical_delay_days": 90,
            "fee_chf": 1000,
        },
    },
    "GE": {
        "demolition_permit": {
            "procedure": "Autorisation de demolir",
            "authority": "Office des autorisations de construire",
            "portal": "https://www.ge.ch/autorisations-construire",
            "filing_method": "portal",
            "required_documents": [
                "Formulaire AD (autorisation de demolir)",
                "Plans de situation et cadastre",
                "Diagnostic polluants complet",
                "Plan d'elimination des dechets",
                "Preavis Office du patrimoine (si necessaire)",
            ],
            "typical_delay_days": 90,
            "fee_chf": 600,
        },
        "asbestos_notification": {
            "procedure": "Annonce SABRA travaux amiante",
            "authority": "SABRA (OCEV)",
            "portal": "https://www.ge.ch/sabra",
            "filing_method": "portal",
            "required_documents": [
                "Formulaire SABRA",
                "Diagnostic amiante par diagnostiqueur agree GE",
                "Plan de travaux detaille",
                "Attestation entreprise de desamiantage agreee",
            ],
            "typical_delay_days": 21,
            "fee_chf": 0,
        },
        "energy_subsidy": {
            "procedure": "Demande subvention GEnergie",
            "authority": "OCEN",
            "portal": "https://www.ge.ch/ocen/subventions",
            "filing_method": "portal",
            "required_documents": [
                "CECB Plus",
                "Devis detailles",
                "Formulaire OCEN",
            ],
            "typical_delay_days": 60,
            "fee_chf": 0,
            "note": "CECB Plus obligatoire (pas CECB simple)",
        },
    },
    "FR": {
        "demolition_permit": {
            "procedure": "Demande de permis de demolir",
            "authority": "SeCa",
            "portal": "https://www.fr.ch/friac",
            "filing_method": "friac",
            "required_documents": [
                "Formulaire FRIAC demolition",
                "Plans de situation",
                "Diagnostic polluants",
                "Plan d'elimination des dechets",
            ],
            "typical_delay_days": 60,
            "fee_chf": 400,
        },
        "asbestos_notification": {
            "procedure": "Annonce travaux amiante FR",
            "authority": "SEn + SUVA",
            "portal": "https://www.fr.ch/sen",
            "filing_method": "friac",
            "required_documents": [
                "Formulaire annonce SUVA",
                "Diagnostic amiante",
                "Plan de travaux",
                "Certification entreprise",
            ],
            "typical_delay_days": 30,
            "fee_chf": 0,
        },
        "energy_subsidy": {
            "procedure": "Demande subvention energie FR",
            "authority": "SdE",
            "portal": "https://www.fr.ch/energie/subventions",
            "filing_method": "friac",
            "required_documents": [
                "CECB ou audit energetique",
                "Devis des travaux",
                "Formulaire cantonal FR",
            ],
            "typical_delay_days": 45,
            "fee_chf": 0,
        },
    },
}

SUPPORTED_CANTONS: list[str] = list(CANTONAL_AUTHORITIES.keys())

# Source registry names per canton
_SOURCE_NAME_MAP: dict[str, str] = {
    "VD": "cantonal_authorities_vd",
    "GE": "cantonal_authorities_ge",
    "FR": "cantonal_authorities_fr",
}

# In-memory cache: canton -> {data, fetched_at}
_cache: dict[str, dict[str, Any]] = {}


def _is_cache_fresh(canton: str) -> bool:
    """Check if cached data is still within TTL."""
    entry = _cache.get(canton)
    if entry is None:
        return False
    age = datetime.now(UTC) - entry["fetched_at"]
    return age < timedelta(days=CACHE_TTL_DAYS)


class CantonalProcedureSourceService:
    """Provides cantonal procedure context: portals, contacts, specific requirements."""

    @staticmethod
    def get_supported_cantons() -> list[str]:
        """Return list of cantons with known authority data."""
        return list(SUPPORTED_CANTONS)

    @staticmethod
    async def get_authority_context(
        canton: str,
        domain: str,
    ) -> dict[str, Any]:
        """Get authority info for a canton + domain.

        Domains: environment, construction, heritage, energy, health.
        Returns authority details or empty result for unknown canton/domain.
        """
        canton = canton.upper()

        if canton not in CANTONAL_AUTHORITIES:
            return {
                "canton": canton,
                "domain": domain,
                "authority": None,
                "error": "unknown_canton",
            }

        canton_data = CANTONAL_AUTHORITIES[canton]
        authority = canton_data.get(domain)

        if authority is None:
            return {
                "canton": canton,
                "domain": domain,
                "authority": None,
                "error": "unknown_domain",
                "available_domains": list(canton_data.keys()),
            }

        return {
            "canton": canton,
            "domain": domain,
            "authority": authority,
        }

    @staticmethod
    async def get_filing_requirements(
        canton: str,
        procedure_type: str,
    ) -> dict[str, Any]:
        """Get specific filing requirements for a canton + procedure type.

        Procedure types: demolition_permit, asbestos_notification, energy_subsidy,
        construction_permit.
        Returns filing details or empty result for unknown canton/procedure.
        """
        canton = canton.upper()

        if canton not in FILING_REQUIREMENTS:
            return {
                "canton": canton,
                "procedure_type": procedure_type,
                "requirements": None,
                "error": "unknown_canton",
            }

        canton_data = FILING_REQUIREMENTS[canton]
        requirements = canton_data.get(procedure_type)

        if requirements is None:
            return {
                "canton": canton,
                "procedure_type": procedure_type,
                "requirements": None,
                "error": "unknown_procedure",
                "available_procedures": list(canton_data.keys()),
            }

        return {
            "canton": canton,
            "procedure_type": procedure_type,
            "requirements": requirements,
        }

    @staticmethod
    async def get_canton_context(
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get full cantonal context for a building. Records health event.

        Returns all authorities + filing requirements for the building's canton.
        """
        # Load building
        result = await db.execute(select(Building).where(Building.id == building_id))
        building = result.scalar_one_or_none()
        if building is None:
            return {"error": "building_not_found", "authorities": {}, "filing_requirements": {}}

        canton = (building.canton or "").upper()

        # Graceful degradation for unknown cantons
        if canton not in CANTONAL_AUTHORITIES:
            return {
                "canton": canton,
                "building_id": str(building_id),
                "authorities": {},
                "filing_requirements": {},
                "error": "no_data_for_canton",
            }

        # Use cache if fresh
        if not _is_cache_fresh(canton):
            now = datetime.now(UTC)
            _cache[canton] = {
                "authorities": CANTONAL_AUTHORITIES[canton],
                "filing_requirements": FILING_REQUIREMENTS.get(canton, {}),
                "fetched_at": now,
            }

            # Record health event
            source_name = _SOURCE_NAME_MAP.get(canton)
            if source_name:
                try:
                    authority_count = len(CANTONAL_AUTHORITIES[canton])
                    procedure_count = len(FILING_REQUIREMENTS.get(canton, {}))
                    await SourceRegistryService.record_health_event(
                        db,
                        source_name,
                        "healthy",
                        description=(
                            f"Canton context loaded for {canton}: "
                            f"{authority_count} authorities, {procedure_count} procedures"
                        ),
                    )
                except Exception:
                    logger.debug("Failed to record cantonal authority health event for %s", canton, exc_info=True)

        cached = _cache[canton]

        return {
            "canton": canton,
            "building_id": str(building_id),
            "authorities": cached["authorities"],
            "filing_requirements": cached.get("filing_requirements", {}),
            "fetched_at": cached["fetched_at"].isoformat(),
            "supported_domains": list(cached["authorities"].keys()),
            "supported_procedures": list(cached.get("filing_requirements", {}).keys()),
        }

    @staticmethod
    async def get_all_authorities(
        db: AsyncSession,
        canton: str,
    ) -> dict[str, Any]:
        """Get all authorities for a canton. Records health event."""
        canton = canton.upper()

        if canton not in CANTONAL_AUTHORITIES:
            return {
                "canton": canton,
                "authorities": {},
                "error": "unknown_canton",
            }

        # Record health event
        source_name = _SOURCE_NAME_MAP.get(canton)
        if source_name:
            try:
                await SourceRegistryService.record_health_event(
                    db,
                    source_name,
                    "healthy",
                    description=f"Authorities catalog fetched for {canton}",
                )
            except Exception:
                logger.debug("Failed to record health event for %s", canton, exc_info=True)

        return {
            "canton": canton,
            "authorities": CANTONAL_AUTHORITIES[canton],
            "total_authorities": len(CANTONAL_AUTHORITIES[canton]),
        }

    # ------------------------------------------------------------------
    # Reliability-grade: fallback, freshness, validation
    # ------------------------------------------------------------------

    @staticmethod
    async def get_canton_context_with_fallback(
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Try canton-specific data. If unknown canton, fall back to federal-level authorities.

        Records degraded health event when fallback is used.
        """
        # Load building
        result = await db.execute(select(Building).where(Building.id == building_id))
        building = result.scalar_one_or_none()
        if building is None:
            return {
                "error": "building_not_found",
                "authorities": {},
                "filing_requirements": {},
                "fallback_used": False,
                "fallback_source": None,
            }

        canton = (building.canton or "").upper()

        # Try canton-specific data first
        if canton in CANTONAL_AUTHORITIES:
            # Known canton — use normal path
            ctx = await CantonalProcedureSourceService.get_canton_context(db, building_id)
            ctx["fallback_used"] = False
            ctx["fallback_source"] = None
            return ctx

        # Unknown canton — fall back to federal-level authorities
        try:
            await SourceRegistryService.record_health_event(
                db,
                "cantonal_authorities_federal",
                "degraded",
                description=f"Canton {canton} not in catalog, federal fallback used",
                fallback_used=True,
                fallback_source_name="federal_authorities",
            )
        except Exception:
            logger.debug("Failed to record degraded health event for canton %s", canton, exc_info=True)

        return {
            "canton": canton,
            "building_id": str(building_id),
            "authorities": FEDERAL_AUTHORITIES,
            "filing_requirements": {},
            "fetched_at": datetime.now(UTC).isoformat(),
            "supported_domains": list(FEDERAL_AUTHORITIES.keys()),
            "supported_procedures": [],
            "fallback_used": True,
            "fallback_source": "federal",
            "detail": f"Canton {canton} not in cantonal catalog — federal-level authorities provided",
        }

    @staticmethod
    async def check_procedure_freshness(
        db: AsyncSession,
        canton: str,
    ) -> dict[str, Any]:
        """Check if cantonal procedure data is current.

        Authority contacts and filing requirements change.
        Returns: {fresh, stale_domains, recommended_action}
        """
        canton = canton.upper()

        if canton not in CANTONAL_AUTHORITIES:
            return {
                "canton": canton,
                "fresh": False,
                "stale_domains": [],
                "recommended_action": "no_data_available",
                "detail": "unknown_canton",
            }

        # Check in-memory cache freshness
        entry = _cache.get(canton)
        if entry is None:
            return {
                "canton": canton,
                "fresh": False,
                "stale_domains": list(CANTONAL_AUTHORITIES[canton].keys()),
                "recommended_action": "refresh",
                "detail": "no_cache_entry",
            }

        age = datetime.now(UTC) - entry["fetched_at"]
        age_days = round(age.total_seconds() / 86400, 1)
        is_fresh = age < timedelta(days=CACHE_TTL_DAYS)

        if is_fresh:
            return {
                "canton": canton,
                "fresh": True,
                "stale_domains": [],
                "age_days": age_days,
                "recommended_action": "none",
            }

        return {
            "canton": canton,
            "fresh": False,
            "stale_domains": list(CANTONAL_AUTHORITIES[canton].keys()),
            "age_days": age_days,
            "recommended_action": "refresh",
            "detail": f"Cache is {age_days} days old (TTL: {CACHE_TTL_DAYS} days)",
        }

    @staticmethod
    def _validate_authority_entry(entry: dict[str, Any]) -> dict[str, Any]:
        """Validate an authority entry has required fields (name, portal or email).

        Returns: {valid, missing_fields}
        """
        if not isinstance(entry, dict):
            return {
                "valid": False,
                "missing_fields": [*_REQUIRED_AUTHORITY_FIELDS, "portal_or_email"],
                "detail": "entry_is_not_a_dict",
            }

        missing: list[str] = []
        for field in _REQUIRED_AUTHORITY_FIELDS:
            if field not in entry or entry[field] is None:
                missing.append(field)

        # Must have at least portal or email
        has_contact = any(entry.get(f) for f in _AUTHORITY_CONTACT_FIELDS)
        if not has_contact:
            missing.append("portal_or_email")

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "detail": "all_fields_present" if not missing else f"missing: {missing}",
        }

    @staticmethod
    def _validate_filing_requirements(requirements: dict[str, Any]) -> dict[str, Any]:
        """Validate filing requirements have required structure.

        Returns: {valid, missing_fields}
        """
        if not isinstance(requirements, dict):
            return {
                "valid": False,
                "missing_fields": list(_REQUIRED_FILING_FIELDS),
                "detail": "requirements_is_not_a_dict",
            }

        missing = [f for f in _REQUIRED_FILING_FIELDS if f not in requirements or requirements[f] is None]

        # required_documents should be a non-empty list
        docs = requirements.get("required_documents")
        if isinstance(docs, list) and len(docs) == 0:
            missing.append("required_documents_empty")

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "detail": "all_fields_present" if not missing else f"missing: {missing}",
        }


# ---------------------------------------------------------------------------
# Federal-level fallback authorities (used when canton is unknown)
# ---------------------------------------------------------------------------
FEDERAL_AUTHORITIES: dict[str, dict[str, Any]] = {
    "environment": {
        "name": "OFEV",
        "full_name": "Office federal de l'environnement",
        "portal": "https://www.bafu.admin.ch",
        "filing": "portal",
        "email": "info@bafu.admin.ch",
    },
    "construction": {
        "name": "ARE",
        "full_name": "Office federal du developpement territorial",
        "portal": "https://www.are.admin.ch",
        "filing": "portal",
        "email": "info@are.admin.ch",
    },
    "energy": {
        "name": "OFEN",
        "full_name": "Office federal de l'energie",
        "portal": "https://www.bfe.admin.ch",
        "filing": "portal",
        "email": "info@bfe.admin.ch",
    },
    "health": {
        "name": "OFSP",
        "full_name": "Office federal de la sante publique",
        "portal": "https://www.bag.admin.ch",
        "filing": "portal",
        "email": "info@bag.admin.ch",
    },
}
