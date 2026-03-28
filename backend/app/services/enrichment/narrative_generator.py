"""Building narrative generator (pure computation, template-based)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def generate_building_narrative(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Generate a template-based narrative in French from structured data.

    Pure function -- no API calls, no LLM.
    """
    year = building_data.get("construction_year")
    address = building_data.get("address", "Adresse inconnue")
    city = building_data.get("city", "")
    canton = building_data.get("canton", "")
    floors = building_data.get("floors_above") or building_data.get("floors")
    surface = building_data.get("surface_area_m2")
    dwellings = building_data.get("dwellings")
    heating = building_data.get("heating_type", "")
    current_year = datetime.now(UTC).year

    sections: list[dict[str, str]] = []

    # 1. Identification
    location = f"{address}, {city}" if city else address
    if canton:
        location += f" ({canton})"
    id_body = f"Le batiment situe au {location}"
    if year:
        id_body += f" a ete construit en {year}, ce qui lui confere un age de {current_year - year} ans"
    id_body += "."
    sections.append({"title": "Identification et contexte", "body": id_body})

    # 2. Physical characteristics
    phys_parts: list[str] = []
    if floors:
        phys_parts.append(f"{floors} etage(s) hors sol")
    if surface:
        phys_parts.append(f"une surface estimee de {surface} m2")
    if dwellings:
        phys_parts.append(f"{dwellings} logement(s)")
    if phys_parts:
        phys_body = "L'immeuble comprend " + ", ".join(phys_parts) + "."
    else:
        phys_body = "Les caracteristiques physiques detaillees ne sont pas disponibles."
    sections.append({"title": "Caracteristiques physiques", "body": phys_body})

    # 3. Environmental context
    radon = enrichment_data.get("radon", {})
    noise = enrichment_data.get("noise", {})
    hazards = enrichment_data.get("natural_hazards", {})
    heritage = enrichment_data.get("heritage", {})
    env_parts: list[str] = []
    radon_level = radon.get("radon_level")
    if radon_level:
        _radon_fr = {"high": "eleve", "medium": "moyen", "low": "faible"}
        env_parts.append(f"risque radon {_radon_fr.get(radon_level, radon_level)}")
    road_db = noise.get("road_noise_day_db")
    if road_db:
        env_parts.append(f"bruit routier de {road_db} dB en journee")
    if hazards.get("flood_risk"):
        env_parts.append(f"risque d'inondation: {hazards['flood_risk']}")
    if heritage.get("isos_protected"):
        env_parts.append("site ISOS protege")
    if env_parts:
        env_body = "Contexte environnemental: " + ", ".join(env_parts) + "."
    else:
        env_body = "Les donnees environnementales detaillees ne sont pas disponibles."
    sections.append({"title": "Contexte environnemental", "body": env_body})

    # 4. Energy performance
    energy_parts: list[str] = []
    if heating:
        energy_parts.append(f"systeme de chauffage: {heating}")
    solar = enrichment_data.get("solar", {})
    if solar.get("suitability"):
        _solar_fr = {"high": "elevee", "medium": "moyenne", "low": "faible"}
        energy_parts.append(f"potentiel solaire {_solar_fr.get(solar['suitability'], solar['suitability'])}")
    thermal = enrichment_data.get("thermal_networks", {})
    if thermal.get("has_district_heating"):
        energy_parts.append("raccordement au chauffage a distance possible")
    if energy_parts:
        energy_body = "Performance energetique: " + ", ".join(energy_parts) + "."
    else:
        energy_body = "Les donnees de performance energetique ne sont pas disponibles."
    sections.append({"title": "Performance energetique", "body": energy_body})

    # 5. Pollutant risk
    pollutant_risk = enrichment_data.get("pollutant_risk", {})
    overall_risk = pollutant_risk.get("overall_risk_score", 0)
    if overall_risk > 0.5:
        poll_body = (
            f"Le score de risque polluant est de {overall_risk:.2f}/1.0, indiquant un risque eleve. "
            "Un diagnostic de substances dangereuses est fortement recommande avant tout travaux."
        )
    elif overall_risk > 0.2:
        poll_body = (
            f"Le score de risque polluant est de {overall_risk:.2f}/1.0, indiquant un risque modere. "
            "Un diagnostic preventif est recommande."
        )
    else:
        poll_body = "Le risque de presence de polluants est estime comme faible."
    sections.append({"title": "Evaluation des polluants", "body": poll_body})

    # 6. Regulatory compliance
    compliance = enrichment_data.get("regulatory_compliance", {})
    comp_summary = compliance.get("summary_fr")
    if comp_summary:
        reg_body = comp_summary
    else:
        reg_body = "L'evaluation reglementaire n'est pas disponible."
    sections.append({"title": "Conformite reglementaire", "body": reg_body})

    # 7. Renovation priorities
    reno_plan = enrichment_data.get("renovation_plan", {})
    reno_summary = reno_plan.get("summary_fr")
    if reno_summary:
        reno_body = reno_summary
    else:
        reno_body = "Aucune priorite de renovation identifiee."
    sections.append({"title": "Priorites de renovation", "body": reno_body})

    # 8. Financial outlook
    financial = enrichment_data.get("financial_impact", {})
    fin_summary = financial.get("summary_fr")
    if fin_summary:
        fin_body = fin_summary
    else:
        fin_body = "L'estimation financiere n'est pas disponible."
    sections.append({"title": "Perspectives financieres", "body": fin_body})

    # 9. Neighborhood quality
    ns = enrichment_data.get("neighborhood_score")
    if ns is not None:
        if ns >= 7:
            nb_body = f"Score de quartier: {ns}/10 — environnement de qualite superieure."
        elif ns >= 5:
            nb_body = f"Score de quartier: {ns}/10 — environnement de qualite moyenne."
        else:
            nb_body = f"Score de quartier: {ns}/10 — potentiel d'amelioration identifie."
    else:
        nb_body = "Le score de qualite du quartier n'est pas disponible."
    sections.append({"title": "Qualite du quartier", "body": nb_body})

    # Assemble full narrative
    narrative_parts: list[str] = []
    for section in sections:
        narrative_parts.append(f"{section['title']}\n{section['body']}")
    narrative_fr = "\n\n".join(narrative_parts)

    word_count = len(narrative_fr.split())

    return {
        "narrative_fr": narrative_fr,
        "sections": sections,
        "word_count": word_count,
    }
