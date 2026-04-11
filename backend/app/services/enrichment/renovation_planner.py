"""Renovation plan generator (pure computation)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

RENOVATION_COSTS_CHF_M2: dict[str, float] = {
    "facade_insulation": 280,
    "roof_insulation": 200,
    "window_replacement": 1200,
    "heating_replacement": 350,
    "electrical_renovation": 80,
    "plumbing_renovation": 100,
    "elevator_replacement": 120_000,  # forfait
    "asbestos_removal": 100,
    "pcb_remediation": 80,
    "lead_paint_removal": 60,
    "waterproofing": 150,
    "fire_protection": 40,
    "accessibility": 50_000,  # forfait
}


def generate_renovation_plan(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Generate a 10-year renovation plan from component lifecycle + subsidies + costs.

    Pure function -- no API calls.
    All cost estimates are indicative (estimation) and should be confirmed by professional quotes.
    """
    surface = building_data.get("surface_area_m2") or 200  # default 200m2
    current_year = datetime.now(UTC).year

    lifecycle = enrichment_data.get("component_lifecycle", {})
    components = lifecycle.get("components", [])
    pollutant_risk = enrichment_data.get("pollutant_risk", {})

    plan_items: list[dict[str, Any]] = []

    def _add_item(
        year_rec: int,
        component: str,
        desc_fr: str,
        cost_key: str,
        priority: str,
        *,
        is_forfait: bool = False,
        regulatory_trigger: str = "",
        subsidy_pct: float = 0.0,
    ) -> None:
        if is_forfait:
            cost = RENOVATION_COSTS_CHF_M2[cost_key]
        else:
            cost = int(RENOVATION_COSTS_CHF_M2[cost_key] * surface)
        subsidy = int(cost * subsidy_pct)
        plan_items.append(
            {
                "year_recommended": year_rec,
                "component": component,
                "work_description_fr": f"{desc_fr} (estimation)",
                "estimated_cost_chf": cost,
                "available_subsidy_chf": subsidy,
                "net_cost_chf": cost - subsidy,
                "priority": priority,
                "regulatory_trigger": regulatory_trigger,
            }
        )

    # --- Year 1-2: Urgent — critical/overdue + pollutant remediation ---
    for comp in components:
        if comp.get("urgency") in ("critical", "urgent"):
            name = comp["name"]
            name_fr = comp.get("name_fr", name)
            if "roof" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Remplacement {name_fr}",
                    "roof_insulation",
                    "critical",
                    subsidy_pct=0.15,
                )
            elif "facade" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Renovation {name_fr}",
                    "facade_insulation",
                    "critical",
                    subsidy_pct=0.20,
                    regulatory_trigger="MoPEC: isolation obligatoire si renovation > 10% de l'enveloppe",
                )
            elif "heating" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Remplacement {name_fr}",
                    "heating_replacement",
                    "critical",
                    subsidy_pct=0.25,
                    regulatory_trigger="OEne: remplacement obligatoire chauffage fossile",
                )
            elif "window" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Remplacement {name_fr}",
                    "window_replacement",
                    "critical",
                    subsidy_pct=0.10,
                )
            elif "elevator" in name:
                _add_item(
                    current_year + 2,
                    name,
                    f"Remplacement {name_fr}",
                    "elevator_replacement",
                    "critical",
                    is_forfait=True,
                )
            elif "electrical" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Renovation {name_fr}",
                    "electrical_renovation",
                    "critical",
                    regulatory_trigger="OIBT: mise en conformite obligatoire",
                )
            elif "water_pipes" in name or "drainage" in name:
                _add_item(
                    current_year + 2,
                    name,
                    f"Renovation {name_fr}",
                    "plumbing_renovation",
                    "high",
                )
            elif "waterproofing" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Refection {name_fr}",
                    "waterproofing",
                    "critical",
                )
            elif "fire_protection" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Mise aux normes {name_fr}",
                    "fire_protection",
                    "critical",
                    regulatory_trigger="AEAI: conformite obligatoire",
                )

    # Pollutant remediation (Year 1-2)
    asbestos_prob = pollutant_risk.get("asbestos_probability", 0)
    pcb_prob = pollutant_risk.get("pcb_probability", 0)
    lead_prob = pollutant_risk.get("lead_probability", 0)

    if asbestos_prob > 0.5:
        _add_item(
            current_year + 1,
            "asbestos",
            "Desamiantage",
            "asbestos_removal",
            "critical",
            regulatory_trigger="OTConst Art. 60a: desamiantage obligatoire avant travaux",
        )
    if pcb_prob > 0.4:
        _add_item(
            current_year + 2,
            "pcb",
            "Assainissement PCB",
            "pcb_remediation",
            "high",
            regulatory_trigger="ORRChim Annexe 2.15: assainissement si > 50 mg/kg",
        )
    if lead_prob > 0.5:
        _add_item(
            current_year + 2,
            "lead",
            "Decapage peintures au plomb",
            "lead_paint_removal",
            "high",
            regulatory_trigger="ORRChim Annexe 2.18: assainissement si > 5000 mg/kg",
        )

    # --- Year 3-5: Important — end_of_life + energy ---
    for comp in components:
        if comp.get("urgency") == "budget":
            name = comp["name"]
            name_fr = comp.get("name_fr", name)
            year_rec = current_year + 4
            if "roof" in name:
                _add_item(year_rec, name, f"Renovation {name_fr}", "roof_insulation", "medium", subsidy_pct=0.15)
            elif "facade" in name:
                _add_item(year_rec, name, f"Renovation {name_fr}", "facade_insulation", "medium", subsidy_pct=0.20)
            elif "window" in name:
                _add_item(year_rec, name, f"Remplacement {name_fr}", "window_replacement", "medium", subsidy_pct=0.10)
            elif "heating" in name:
                _add_item(
                    current_year + 3,
                    name,
                    f"Remplacement {name_fr}",
                    "heating_replacement",
                    "medium",
                    subsidy_pct=0.25,
                )
            elif "electrical" in name:
                _add_item(year_rec, name, f"Renovation {name_fr}", "electrical_renovation", "medium")
            elif "waterproofing" in name:
                _add_item(year_rec, name, f"Refection {name_fr}", "waterproofing", "medium")

    # --- Year 6-10: Planned — aging components ---
    for comp in components:
        if comp.get("urgency") == "plan":
            name = comp["name"]
            name_fr = comp.get("name_fr", name)
            year_rec = current_year + 8
            if "roof" in name:
                _add_item(year_rec, name, f"Planification renovation {name_fr}", "roof_insulation", "low")
            elif "facade" in name:
                _add_item(year_rec, name, f"Planification renovation {name_fr}", "facade_insulation", "low")
            elif "window" in name:
                _add_item(year_rec, name, f"Planification remplacement {name_fr}", "window_replacement", "low")

    total_estimated = sum(i["estimated_cost_chf"] for i in plan_items)
    total_subsidy = sum(i["available_subsidy_chf"] for i in plan_items)
    total_net = total_estimated - total_subsidy
    critical_items = sum(1 for i in plan_items if i["priority"] == "critical")

    summary_parts: list[str] = []
    if critical_items:
        summary_parts.append(f"{critical_items} intervention(s) critique(s) a realiser sous 2 ans")
    if total_estimated:
        summary_parts.append(f"cout total estime: CHF {total_estimated:,.0f}")
    if total_subsidy:
        summary_parts.append(f"subventions estimees: CHF {total_subsidy:,.0f}")
    summary_fr = ". ".join(summary_parts) + "." if summary_parts else "Aucune renovation urgente identifiee."

    return {
        "plan_items": plan_items,
        "total_estimated_chf": total_estimated,
        "total_subsidy_chf": total_subsidy,
        "total_net_chf": total_net,
        "critical_items_count": critical_items,
        "summary_fr": summary_fr,
    }
