"""Per-source metadata, source class taxonomy, and enrichment quality summary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Source class taxonomy — every piece of data is tagged by nature
# ---------------------------------------------------------------------------

SOURCE_CLASSES: dict[str, str] = {
    "geo.admin.ch/geocode": "official",
    "geo.admin.ch/gwr": "official",
    "geocode": "official",
    "regbl": "official",
    "cadastre": "official",
    "ch.bag.radonkarte": "observed",
    "ch.bafu.laerm-strassenlaerm_tag": "observed",
    "ch.bfe.solarenergie-eignung-daecher": "observed",
    "ch.are.gueteklassen_oev": "official",
    "ch.bak.bundesinventar-schuetzenswerte-ortsbilder": "official",
    "ch.bafu.erdbeben-erdbebenzonen": "official",
    "radon": "observed",
    "noise": "observed",
    "solar": "observed",
    "railway_noise": "observed",
    "aircraft_noise": "observed",
    "natural_hazards": "observed",
    "heritage": "official",
    "transport": "official",
    "seismic": "official",
    "water_protection": "official",
    "building_zones": "official",
    "contaminated_sites": "official",
    "groundwater_zones": "official",
    "flood_zones": "official",
    "protected_monuments": "official",
    "agricultural_zones": "official",
    "forest_reserves": "official",
    "military_zones": "official",
    "mobile_coverage": "observed",
    "broadband": "observed",
    "ev_charging": "commercial",
    "thermal_networks": "observed",
    "swisstopo_image": "official",
    "osm/amenities": "commercial",
    "osm_amenities": "commercial",
    "osm_building": "commercial",
    "transport.opendata.ch": "commercial",
    "nearest_stops": "commercial",
    "climate": "observed",
    "ai_enrichment": "derived",
    "risk_prediction": "derived",
    "neighborhood_score": "derived",
    "lifecycle_prediction": "derived",
    "renovation_plan": "derived",
    "compliance_check": "derived",
    "financial_impact": "derived",
    "narrative": "derived",
    "connectivity_score": "derived",
    "environmental_risk_score": "derived",
    "livability_score": "derived",
    "renovation_potential": "derived",
    "intelligence_score": "derived",
    "accessibility": "derived",
    "subsidies": "derived",
    "pollutant_risk": "derived",
}


def _get_source_class(source_name: str) -> str:
    """Resolve source_class for a given source_name."""
    return SOURCE_CLASSES.get(source_name, "derived")


def _source_entry(
    source_name: str,
    *,
    status: str = "success",
    confidence: str = "high",
    match_quality: str | None = None,
    retry_count: int = 0,
    error: str | None = None,
    source_class: str | None = None,
) -> dict[str, Any]:
    """Create a standardized per-source metadata entry with source_class."""
    resolved_class = source_class or _get_source_class(source_name)
    entry: dict[str, Any] = {
        "source_name": source_name,
        "source_class": resolved_class,
        "status": status,
        "confidence": confidence,
        "fetched_at": datetime.now(UTC).isoformat(),
        "retry_count": retry_count,
        "error": error,
    }
    if match_quality is not None:
        entry["match_quality"] = match_quality
    return entry


# ---------------------------------------------------------------------------
# Enrichment quality summary
# ---------------------------------------------------------------------------


def compute_enrichment_quality(
    source_entries: list[dict[str, Any]],
    *,
    geocode_quality: str | None = None,
    egid_confidence: str | None = None,
) -> dict[str, Any]:
    """Compute an enrichment quality summary from per-source entries.

    Returns dict with total_sources, succeeded, failed, unavailable,
    timeout, skipped, overall_confidence, critical_gaps, warnings.
    """
    total = len(source_entries)
    succeeded = sum(1 for e in source_entries if e.get("status") == "success")
    partial = sum(1 for e in source_entries if e.get("status") == "partial")
    failed = sum(1 for e in source_entries if e.get("status") == "failed")
    unavailable = sum(1 for e in source_entries if e.get("status") == "unavailable")
    timeout = sum(1 for e in source_entries if e.get("status") == "timeout")
    skipped = sum(1 for e in source_entries if e.get("status") == "skipped")

    critical_gaps: list[str] = []
    warnings: list[str] = []

    # Check critical sources
    source_map = {e["source_name"]: e for e in source_entries}

    geocode_entry = source_map.get("geocode")
    if geocode_entry and geocode_entry.get("status") != "success":
        critical_gaps.append("Geocode failed — no coordinates")
    elif geocode_quality and geocode_quality in ("weak", "no_match"):
        warnings.append(f"Geocode match is {geocode_quality}")

    regbl_entry = source_map.get("regbl")
    if regbl_entry and regbl_entry.get("status") != "success":
        critical_gaps.append("RegBL data missing")

    if egid_confidence == "unverified":
        warnings.append("EGID not verified against address")
    elif egid_confidence == "probable":
        warnings.append("EGID match is probable but not exact")

    # No EGID at all
    if not source_map.get("regbl") or source_map.get("regbl", {}).get("status") in ("failed", "skipped"):
        critical_gaps.append("EGID not found")

    # Overall confidence
    if critical_gaps:
        overall_confidence = "low"
    elif warnings or failed > total * 0.3:
        overall_confidence = "medium"
    else:
        overall_confidence = "high"

    return {
        "total_sources": total,
        "succeeded": succeeded + partial,
        "failed": failed,
        "unavailable": unavailable,
        "timeout": timeout,
        "skipped": skipped,
        "overall_confidence": overall_confidence,
        "critical_gaps": critical_gaps,
        "warnings": warnings,
    }
