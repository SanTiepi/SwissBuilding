"""Subsidy/funding source adapter — structured access to cantonal subsidy programs."""

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

# Cache TTL — subsidy data refreshed weekly at most
CACHE_TTL_DAYS = 7

# ---------------------------------------------------------------------------
# Known subsidy program catalogues per canton
# ---------------------------------------------------------------------------
SUBSIDY_PROGRAMS: dict[str, dict[str, Any]] = {
    "VD": {
        "name": "Programme Batiments VD",
        "url": "https://www.vd.ch/themes/environnement/energie/subventions",
        "last_updated": "2026-01-01",
        "programs": [
            {
                "name": "Isolation thermique",
                "category": "energy",
                "max_chf_m2": 40,
                "conditions": "CECB requis, batiment avant 2000",
            },
            {
                "name": "Remplacement chauffage",
                "category": "heating",
                "max_chf": 10000,
                "conditions": "Remplacement chauffage fossile",
            },
            {
                "name": "Assainissement amiante",
                "category": "pollutant",
                "max_chf": 15000,
                "conditions": "Batiment avant 1990, diagnostic amiante positif",
                "pollutant": "asbestos",
                "building_age_cutoff": 1990,
            },
            {
                "name": "Fenetres",
                "category": "windows",
                "max_chf_m2": 70,
                "conditions": "Triple vitrage, Uw <= 1.0 W/m2K",
            },
            {
                "name": "Ventilation controlee",
                "category": "ventilation",
                "max_chf": 5000,
                "conditions": "Installation VMC double-flux",
            },
        ],
    },
    "GE": {
        "name": "Programme Batiments GE",
        "url": "https://www.ge.ch/dossier/programme-batiments",
        "last_updated": "2026-01-01",
        "programs": [
            {
                "name": "Isolation thermique enveloppe",
                "category": "energy",
                "max_chf_m2": 50,
                "conditions": "CECB requis, amelioration >= 2 classes",
            },
            {
                "name": "Pompe a chaleur",
                "category": "heating",
                "max_chf": 12000,
                "conditions": "Remplacement chauffage fossile par PAC",
            },
            {
                "name": "Assainissement polluants",
                "category": "pollutant",
                "max_chf": 20000,
                "conditions": "Batiment avant 1991, diagnostic polluants valide",
                "pollutant": "asbestos",
                "building_age_cutoff": 1991,
            },
            {
                "name": "Solaire thermique",
                "category": "solar",
                "max_chf": 8000,
                "conditions": "Installation panneaux solaires thermiques",
            },
        ],
    },
    "FR": {
        "name": "Programme Batiments FR",
        "url": "https://www.fr.ch/energie",
        "last_updated": "2026-01-01",
        "programs": [
            {
                "name": "Isolation facade et toiture",
                "category": "energy",
                "max_chf_m2": 45,
                "conditions": "Normes Minergie ou equivalentes",
            },
            {
                "name": "Chauffage renouvelable",
                "category": "heating",
                "max_chf": 8000,
                "conditions": "Remplacement chauffage fossile",
            },
            {
                "name": "Assainissement amiante",
                "category": "pollutant",
                "max_chf": 12000,
                "conditions": "Batiment avant 1990, rapport diagnostiqueur agree",
                "pollutant": "asbestos",
                "building_age_cutoff": 1990,
            },
        ],
    },
}

# All supported cantons
SUPPORTED_CANTONS: list[str] = list(SUBSIDY_PROGRAMS.keys())

# Source registry names per canton
_SOURCE_NAME_MAP: dict[str, str] = {
    "VD": "subsidy_programs_vd",
    "GE": "subsidy_programs_ge",
    "FR": "subsidy_programs_fr",
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


class SubsidySourceService:
    """Fetches and caches subsidy/funding program data for Swiss cantons."""

    @staticmethod
    def get_supported_cantons() -> list[str]:
        """Return list of cantons with known subsidy programs."""
        return list(SUPPORTED_CANTONS)

    @staticmethod
    async def get_subsidy_catalog(
        db: AsyncSession,
        canton: str,
        *,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Fetch subsidy catalog for a canton.

        Uses in-memory cache with TTL. Records a health event on every fetch.
        Returns structured program data or empty result for unknown cantons.
        """
        canton = canton.upper()

        # Unknown canton — graceful degradation
        if canton not in SUBSIDY_PROGRAMS:
            return {
                "canton": canton,
                "programs": [],
                "total_programs": 0,
                "source": None,
                "error": "unknown_canton",
            }

        # Check cache
        if not force_refresh and _is_cache_fresh(canton):
            cached = _cache[canton]
            return {
                "canton": canton,
                "name": cached["data"]["name"],
                "url": cached["data"]["url"],
                "programs": cached["data"]["programs"],
                "total_programs": len(cached["data"]["programs"]),
                "last_updated": cached["data"]["last_updated"],
                "fetched_at": cached["fetched_at"].isoformat(),
                "cached": True,
            }

        # "Fetch" — in practice reads structured data; would be HTTP in production
        program_data = SUBSIDY_PROGRAMS[canton]
        now = datetime.now(UTC)

        # Update cache
        _cache[canton] = {"data": program_data, "fetched_at": now}

        # Record health event
        source_name = _SOURCE_NAME_MAP.get(canton)
        if source_name:
            try:
                await SourceRegistryService.record_health_event(
                    db,
                    source_name,
                    "healthy",
                    description=f"Subsidy catalog refreshed for {canton}: {len(program_data['programs'])} programs",
                )
            except Exception:
                logger.debug("Failed to record subsidy health event for %s", canton, exc_info=True)

        return {
            "canton": canton,
            "name": program_data["name"],
            "url": program_data["url"],
            "programs": program_data["programs"],
            "total_programs": len(program_data["programs"]),
            "last_updated": program_data["last_updated"],
            "fetched_at": now.isoformat(),
            "cached": False,
        }

    @staticmethod
    async def get_applicable_subsidies(
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get subsidies applicable to a building based on canton, age, work type.

        Returns: {programs: [...], total_potential_chf: float, canton: str}
        """
        # Load building
        result = await db.execute(select(Building).where(Building.id == building_id))
        building = result.scalar_one_or_none()
        if building is None:
            return {"error": "building_not_found", "programs": [], "total_potential_chf": 0}

        canton = (building.canton or "").upper()
        if canton not in SUBSIDY_PROGRAMS:
            return {
                "canton": canton,
                "building_id": str(building_id),
                "programs": [],
                "total_potential_chf": 0,
                "error": "no_programs_for_canton",
            }

        catalog = await SubsidySourceService.get_subsidy_catalog(db, canton)
        if catalog.get("error"):
            return {
                "canton": canton,
                "building_id": str(building_id),
                "programs": [],
                "total_potential_chf": 0,
                "error": catalog["error"],
            }

        # Filter programs by building age where applicable
        applicable: list[dict[str, Any]] = []
        total_potential = 0.0

        for program in catalog.get("programs", []):
            age_cutoff = program.get("building_age_cutoff")
            if age_cutoff and building.construction_year and building.construction_year > age_cutoff:
                continue  # Building too new for this program

            applicable.append(program)
            # Sum potential amounts
            if "max_chf" in program:
                total_potential += program["max_chf"]
            elif "max_chf_m2" in program:
                # Rough estimate — assume 200 m2 if we don't have surface data
                total_potential += program["max_chf_m2"] * 200

        return {
            "canton": canton,
            "building_id": str(building_id),
            "catalog_name": catalog.get("name"),
            "catalog_url": catalog.get("url"),
            "programs": applicable,
            "total_programs": len(applicable),
            "total_potential_chf": total_potential,
            "last_updated": catalog.get("last_updated"),
        }

    @staticmethod
    async def get_subsidy_eligibility(
        db: AsyncSession,
        building_id: uuid.UUID,
        work_type: str,
    ) -> dict[str, Any]:
        """Check eligibility for a specific work type.

        Maps work_type to subsidy categories and returns matching programs.
        Returns: {eligible: bool, programs: [...], conditions: [...], max_amount: float}
        """
        # Work type -> subsidy category mapping
        work_type_to_category: dict[str, list[str]] = {
            "asbestos_removal": ["pollutant"],
            "pcb_removal": ["pollutant"],
            "lead_removal": ["pollutant"],
            "hap_removal": ["pollutant"],
            "pfas_remediation": ["pollutant"],
            "renovation": ["energy", "windows", "ventilation"],
            "energy_renovation": ["energy", "heating", "windows", "ventilation", "solar"],
            "hvac": ["heating", "ventilation"],
            "roof_facade": ["energy"],
            "demolition": [],
            "electrical": [],
            "plumbing": [],
            "fire_safety": [],
            "maintenance": [],
        }

        categories = work_type_to_category.get(work_type, [])
        if not categories:
            return {
                "building_id": str(building_id),
                "work_type": work_type,
                "eligible": False,
                "programs": [],
                "conditions": [],
                "max_amount": 0,
                "reason": "no_subsidy_category_for_work_type",
            }

        # Get applicable subsidies for this building
        applicable = await SubsidySourceService.get_applicable_subsidies(db, building_id)
        if applicable.get("error"):
            return {
                "building_id": str(building_id),
                "work_type": work_type,
                "eligible": False,
                "programs": [],
                "conditions": [],
                "max_amount": 0,
                "error": applicable["error"],
            }

        # Filter by matching categories
        matching: list[dict[str, Any]] = []
        conditions: list[str] = []
        max_amount = 0.0

        for program in applicable.get("programs", []):
            if program.get("category") in categories:
                matching.append(program)
                if program.get("conditions"):
                    conditions.append(program["conditions"])
                if "max_chf" in program:
                    max_amount += program["max_chf"]
                elif "max_chf_m2" in program:
                    max_amount += program["max_chf_m2"] * 200

        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "canton": applicable.get("canton"),
            "eligible": len(matching) > 0,
            "programs": matching,
            "conditions": conditions,
            "max_amount": max_amount,
        }

    @staticmethod
    async def refresh_subsidy_data(
        db: AsyncSession,
        canton: str,
    ) -> dict[str, Any]:
        """Force-refresh cached subsidy data for a canton. Records health event."""
        return await SubsidySourceService.get_subsidy_catalog(db, canton, force_refresh=True)
