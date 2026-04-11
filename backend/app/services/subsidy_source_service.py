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

# Programs change annually; data older than this is considered stale
PROGRAM_STALENESS_DAYS = 365

# Required fields for a valid subsidy program entry
_REQUIRED_PROGRAM_FIELDS: list[str] = ["name", "category"]

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

# Federal-level fallback programs (Programme Batiments federal)
FEDERAL_PROGRAMS: dict[str, Any] = {
    "name": "Programme Batiments federal",
    "url": "https://www.leprogrammebatiments.ch",
    "last_updated": "2026-01-01",
    "programs": [
        {
            "name": "Isolation thermique (federal)",
            "category": "energy",
            "max_chf_m2": 30,
            "conditions": "CECB requis, amelioration energetique significative",
        },
        {
            "name": "Remplacement chauffage fossile (federal)",
            "category": "heating",
            "max_chf": 6000,
            "conditions": "Remplacement chauffage fossile par renouvelable",
        },
    ],
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

    @staticmethod
    async def get_applicable_subsidies_with_fallback(
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> dict[str, Any]:
        """If canton-specific data unavailable, fall back to federal-level programs.

        Records degraded health event when fallback is used.
        """
        # Load building
        result = await db.execute(select(Building).where(Building.id == building_id))
        building = result.scalar_one_or_none()
        if building is None:
            return {"error": "building_not_found", "programs": [], "total_potential_chf": 0}

        canton = (building.canton or "").upper()
        used_fallback = False

        if canton in SUBSIDY_PROGRAMS:
            catalog = await SubsidySourceService.get_subsidy_catalog(db, canton)
            if catalog.get("error"):
                # Canton known but catalog fetch failed — fall back to federal
                used_fallback = True
                programs = FEDERAL_PROGRAMS["programs"]
                catalog_name = FEDERAL_PROGRAMS["name"]
                catalog_url = FEDERAL_PROGRAMS["url"]
                last_updated = FEDERAL_PROGRAMS["last_updated"]
            else:
                programs = catalog.get("programs", [])
                catalog_name = catalog.get("name")
                catalog_url = catalog.get("url")
                last_updated = catalog.get("last_updated")
        else:
            # Unknown canton — fall back to federal programs
            used_fallback = True
            programs = FEDERAL_PROGRAMS["programs"]
            catalog_name = FEDERAL_PROGRAMS["name"]
            catalog_url = FEDERAL_PROGRAMS["url"]
            last_updated = FEDERAL_PROGRAMS["last_updated"]

        # Record health event for fallback
        if used_fallback:
            try:
                await SourceRegistryService.record_health_event(
                    db,
                    "subsidy_programs_federal",
                    "degraded",
                    description=f"Federal fallback used for canton {canton}",
                    fallback_used=True,
                    fallback_source_name="federal_programs",
                )
            except Exception:
                logger.debug("Failed to record federal fallback health event", exc_info=True)

        # Filter programs by building age where applicable
        applicable: list[dict[str, Any]] = []
        total_potential = 0.0

        for program in programs:
            age_cutoff = program.get("building_age_cutoff")
            if age_cutoff and building.construction_year and building.construction_year > age_cutoff:
                continue
            applicable.append(program)
            if "max_chf" in program:
                total_potential += program["max_chf"]
            elif "max_chf_m2" in program:
                total_potential += program["max_chf_m2"] * 200

        return {
            "canton": canton,
            "building_id": str(building_id),
            "catalog_name": catalog_name,
            "catalog_url": catalog_url,
            "programs": applicable,
            "total_programs": len(applicable),
            "total_potential_chf": total_potential,
            "last_updated": last_updated,
            "used_fallback": used_fallback,
            "fallback_source": "federal" if used_fallback else None,
        }

    @staticmethod
    async def check_subsidy_freshness(
        db: AsyncSession,
        canton: str,
    ) -> dict[str, Any]:
        """Check if subsidy data is still current. Programs change annually.

        Returns: {fresh: bool, stale_since: str | None, recommended_action: str}
        """
        canton = canton.upper()

        if canton not in SUBSIDY_PROGRAMS:
            return {
                "canton": canton,
                "fresh": False,
                "stale_since": None,
                "recommended_action": "no_data_available",
                "detail": "unknown_canton",
            }

        program_data = SUBSIDY_PROGRAMS[canton]
        last_updated_str = program_data.get("last_updated")
        if not last_updated_str:
            return {
                "canton": canton,
                "fresh": False,
                "stale_since": None,
                "recommended_action": "refresh",
                "detail": "no_last_updated_field",
            }

        try:
            last_updated = datetime.fromisoformat(last_updated_str).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return {
                "canton": canton,
                "fresh": False,
                "stale_since": None,
                "recommended_action": "refresh",
                "detail": "invalid_last_updated_format",
            }

        now = datetime.now(UTC)
        age = now - last_updated
        is_fresh = age < timedelta(days=PROGRAM_STALENESS_DAYS)

        # Also check in-memory cache freshness
        cache_fresh = _is_cache_fresh(canton)

        result: dict[str, Any] = {
            "canton": canton,
            "fresh": is_fresh,
            "age_days": round(age.total_seconds() / 86400, 1),
            "last_updated": last_updated_str,
            "cache_fresh": cache_fresh,
        }

        if is_fresh:
            result["stale_since"] = None
            result["recommended_action"] = "none"
        else:
            result["stale_since"] = last_updated_str
            result["recommended_action"] = "refresh"

        # Record health event for staleness
        source_name = _SOURCE_NAME_MAP.get(canton)
        if source_name and not is_fresh:
            try:
                await SourceRegistryService.record_health_event(
                    db,
                    source_name,
                    "degraded",
                    description=f"Subsidy data for {canton} is stale ({round(age.total_seconds() / 86400)} days old)",
                )
            except Exception:
                logger.debug("Failed to record staleness event for %s", canton, exc_info=True)

        return result

    @staticmethod
    def _validate_subsidy_program(program: dict[str, Any]) -> dict[str, Any]:
        """Validate a subsidy program entry has required fields.

        Detect if program structure changed.
        Returns: {valid: bool, missing_fields: [...], detail: str}
        """
        if not isinstance(program, dict):
            return {
                "valid": False,
                "missing_fields": _REQUIRED_PROGRAM_FIELDS,
                "detail": "program_is_not_a_dict",
            }

        missing = [f for f in _REQUIRED_PROGRAM_FIELDS if f not in program or program[f] is None]
        if missing:
            return {
                "valid": False,
                "missing_fields": missing,
                "detail": f"missing_required_fields: {missing}",
            }

        # Validate category is a known value
        known_categories = {"energy", "heating", "pollutant", "windows", "ventilation", "solar"}
        cat = program.get("category")
        if cat and cat not in known_categories:
            return {
                "valid": True,
                "missing_fields": [],
                "detail": f"unknown_category: {cat}",
            }

        return {"valid": True, "missing_fields": [], "detail": "ok"}
