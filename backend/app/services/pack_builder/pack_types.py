"""Pack type configuration and mappings.

Defines the available pack types, their sections, and the mapping
from pack types to conformance profiles.
"""

PACK_BUILDER_VERSION = "1.0.0"

# Map pack_type to conformance requirement profile name
PACK_TO_PROFILE: dict[str, str] = {
    "authority": "authority_pack",
    "insurer": "insurer_pack",
    "transfer": "transfer",
    "owner": "publication",
    "contractor": "publication",
    "notary": "transfer",
}

PACK_TYPES = {
    "authority": {
        "name": "Pack Autorite",
        "sections": [
            "passport_summary",
            "completeness_report",
            "readiness_verdict",
            "pollutant_inventory",
            "diagnostic_summary",
            "compliance_status",
            "document_inventory",
            "contradictions",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": True,
    },
    "owner": {
        "name": "Pack Proprietaire",
        "sections": [
            "passport_summary",
            "completeness_report",
            "readiness_verdict",
            "cost_summary",
            "intervention_history",
            "upcoming_obligations",
            "insurance_status",
            "document_inventory",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": False,
    },
    "insurer": {
        "name": "Pack Assureur",
        "sections": [
            "passport_summary",
            "pollutant_inventory",
            "risk_summary",
            "intervention_history",
            "compliance_status",
            "claims_history",
            "readiness_verdict",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": True,
    },
    "contractor": {
        "name": "Pack Entreprise",
        "sections": [
            "scope_summary",
            "pollutant_inventory",
            "zones_concerned",
            "regulatory_requirements",
            "safety_requirements",
            "document_inventory",
            "work_conditions",
        ],
        "includes_trust": False,
        "includes_provenance": False,
    },
    "notary": {
        "name": "Pack Notaire / Transaction",
        "sections": [
            "passport_summary",
            "completeness_report",
            "pollutant_inventory",
            "intervention_history",
            "compliance_status",
            "upcoming_obligations",
            "contradictions",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": True,
    },
    "transfer": {
        "name": "Pack Transmission",
        "sections": ["full"],
        "includes_trust": True,
        "includes_provenance": True,
    },
}

_SECTION_NAMES = {
    "passport_summary": "Resume du passeport batiment",
    "completeness_report": "Rapport de completude du dossier",
    "readiness_verdict": "Verdict de readiness reglementaire",
    "pollutant_inventory": "Inventaire des polluants",
    "diagnostic_summary": "Synthese des diagnostics",
    "compliance_status": "Statut de conformite",
    "document_inventory": "Inventaire des documents",
    "contradictions": "Contradictions detectees",
    "caveats": "Reserves et limites",
    "intervention_history": "Historique des interventions",
    "cost_summary": "Synthese des couts",
    "upcoming_obligations": "Obligations a venir",
    "insurance_status": "Statut assurances",
    "risk_summary": "Synthese des risques",
    "claims_history": "Historique des sinistres",
    "scope_summary": "Perimetre des travaux",
    "zones_concerned": "Zones concernees",
    "regulatory_requirements": "Exigences reglementaires",
    "safety_requirements": "Exigences de securite",
    "work_conditions": "Conditions de travail",
}
