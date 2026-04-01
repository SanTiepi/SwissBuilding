"""BatiConnect Enrichment Package -- decomposed from building_enrichment_service.py.

Re-exports all public functions so existing imports continue to work.
"""

__all__ = [
    # score_computers
    "COMPONENT_LIFESPANS",
    "COMPONENT_NAMES_FR",
    # renovation_planner
    "RENOVATION_COSTS_CHF_M2",
    # source_provenance
    "SOURCE_CLASSES",
    # geo_admin_fetchers
    "SUPPORTED_IDENTIFY_LAYERS",
    # address_utils
    "_ABBREVIATION_MAP",
    "_REVERSE_ABBREVIATION_MAP",
    "_UNSUPPORTED_LAYERS",
    # orchestrator
    "_build_ai_prompt",
    "_call_anthropic",
    "_call_openai",
    "_component_status",
    "_component_urgency",
    "_extract_street_name",
    "_extract_street_number",
    "_geo_identify",
    "_get_source_class",
    "_lat_lon_to_tile",
    "_normalize_address",
    "_normalize_for_comparison",
    # http_helpers
    "_retry_request",
    "_source_entry",
    "_strip_accents",
    "_throttle",
    "compute_accessibility_assessment",
    "compute_component_lifecycle",
    "compute_connectivity_score",
    "compute_enrichment_quality",
    "compute_environmental_risk_score",
    "compute_livability_score",
    "compute_neighborhood_score",
    "compute_overall_building_intelligence_score",
    "compute_pollutant_risk_prediction",
    # regulatory_checks
    "compute_regulatory_compliance",
    "compute_renovation_potential",
    "enrich_all_buildings",
    "enrich_building",
    "enrich_building_with_ai",
    # financial_estimator
    "estimate_financial_impact",
    "estimate_subsidy_eligibility",
    "fetch_accident_sites",
    "fetch_agricultural_zones",
    "fetch_aircraft_noise",
    "fetch_broadband",
    "fetch_building_zones",
    "fetch_cadastre_egrid",
    # osm_fetchers
    "fetch_climate_data",
    "fetch_contaminated_sites",
    "fetch_ev_charging",
    "fetch_flood_zones",
    "fetch_forest_reserves",
    "fetch_groundwater_zones",
    "fetch_heritage_status",
    "fetch_military_zones",
    "fetch_mobile_coverage",
    "fetch_natural_hazards",
    "fetch_nearest_stops",
    "fetch_noise_data",
    "fetch_osm_amenities",
    "fetch_osm_building_details",
    "fetch_protected_monuments",
    "fetch_radon_risk",
    "fetch_railway_noise",
    "fetch_regbl_data",
    "fetch_seismic_zone",
    "fetch_solar_potential",
    "fetch_swisstopo_image_url",
    "fetch_thermal_networks",
    "fetch_transport_quality",
    "fetch_water_protection",
    # narrative_generator
    "generate_building_narrative",
    "generate_renovation_plan",
    "geocode_address",
    "verify_egid_address",
    "verify_geocode_match",
]
from app.services.enrichment.address_utils import (
    _ABBREVIATION_MAP,
    _REVERSE_ABBREVIATION_MAP,
    _extract_street_name,
    _extract_street_number,
    _normalize_address,
    _normalize_for_comparison,
    _strip_accents,
    verify_egid_address,
    verify_geocode_match,
)
from app.services.enrichment.financial_estimator import estimate_financial_impact
from app.services.enrichment.geo_admin_fetchers import (
    _UNSUPPORTED_LAYERS,
    SUPPORTED_IDENTIFY_LAYERS,
    _geo_identify,
    fetch_accident_sites,
    fetch_agricultural_zones,
    fetch_aircraft_noise,
    fetch_broadband,
    fetch_building_zones,
    fetch_contaminated_sites,
    fetch_ev_charging,
    fetch_flood_zones,
    fetch_forest_reserves,
    fetch_groundwater_zones,
    fetch_heritage_status,
    fetch_military_zones,
    fetch_mobile_coverage,
    fetch_natural_hazards,
    fetch_noise_data,
    fetch_protected_monuments,
    fetch_radon_risk,
    fetch_railway_noise,
    fetch_seismic_zone,
    fetch_solar_potential,
    fetch_thermal_networks,
    fetch_transport_quality,
    fetch_water_protection,
)
from app.services.enrichment.http_helpers import _retry_request, _throttle
from app.services.enrichment.narrative_generator import generate_building_narrative
from app.services.enrichment.orchestrator import (
    _build_ai_prompt,
    _call_anthropic,
    _call_openai,
    _lat_lon_to_tile,
    enrich_all_buildings,
    enrich_building,
    enrich_building_with_ai,
    fetch_cadastre_egrid,
    fetch_regbl_data,
    fetch_swisstopo_image_url,
    geocode_address,
)
from app.services.enrichment.osm_fetchers import (
    fetch_climate_data,
    fetch_nearest_stops,
    fetch_osm_amenities,
    fetch_osm_building_details,
)
from app.services.enrichment.regulatory_checks import compute_regulatory_compliance
from app.services.enrichment.renovation_planner import (
    RENOVATION_COSTS_CHF_M2,
    generate_renovation_plan,
)
from app.services.enrichment.score_computers import (
    COMPONENT_LIFESPANS,
    COMPONENT_NAMES_FR,
    _component_status,
    _component_urgency,
    compute_accessibility_assessment,
    compute_component_lifecycle,
    compute_connectivity_score,
    compute_environmental_risk_score,
    compute_livability_score,
    compute_neighborhood_score,
    compute_overall_building_intelligence_score,
    compute_pollutant_risk_prediction,
    compute_renovation_potential,
    estimate_subsidy_eligibility,
)
from app.services.enrichment.source_provenance import (
    SOURCE_CLASSES,
    _get_source_class,
    _source_entry,
    compute_enrichment_quality,
)
