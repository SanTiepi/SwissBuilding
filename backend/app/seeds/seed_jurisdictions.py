"""
SwissBuildingOS - Jurisdiction & RegulatoryPack Seed
Idempotent seed script for jurisdiction hierarchy and Swiss regulatory packs.

Usage:
    python -m app.seeds.seed_jurisdictions
"""

import asyncio
import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.jurisdiction import Jurisdiction
from app.models.regulatory_pack import RegulatoryPack

# ---------------------------------------------------------------------------
# Stable UUIDs for idempotent upserts
# ---------------------------------------------------------------------------
ID_EU = uuid.UUID("00000000-0000-4000-a000-000000000001")
ID_CH = uuid.UUID("00000000-0000-4000-a000-000000000002")
ID_CH_VD = uuid.UUID("00000000-0000-4000-a000-000000000003")
ID_CH_GE = uuid.UUID("00000000-0000-4000-a000-000000000004")
ID_CH_ZH = uuid.UUID("00000000-0000-4000-a000-000000000005")
ID_CH_BE = uuid.UUID("00000000-0000-4000-a000-000000000006")
ID_CH_VS = uuid.UUID("00000000-0000-4000-a000-000000000007")
ID_FR = uuid.UUID("00000000-0000-4000-a000-000000000008")
ID_DE = uuid.UUID("00000000-0000-4000-a000-000000000009")
ID_IT = uuid.UUID("00000000-0000-4000-a000-00000000000a")
ID_AT = uuid.UUID("00000000-0000-4000-a000-00000000000b")

JURISDICTIONS = [
    # Supranational
    {
        "id": ID_EU,
        "code": "eu",
        "name": "European Union",
        "parent_id": None,
        "level": "supranational",
        "country_code": None,
        "is_active": True,
        "metadata_json": None,
    },
    # Countries
    {
        "id": ID_CH,
        "code": "ch",
        "name": "Suisse / Schweiz / Svizzera",
        "parent_id": ID_EU,
        "level": "country",
        "country_code": "CH",
        "is_active": True,
        "metadata_json": {"official_languages": ["fr", "de", "it", "rm"]},
    },
    {
        "id": ID_FR,
        "code": "fr",
        "name": "France",
        "parent_id": ID_EU,
        "level": "country",
        "country_code": "FR",
        "is_active": True,
        "metadata_json": None,
    },
    {
        "id": ID_DE,
        "code": "de",
        "name": "Deutschland",
        "parent_id": ID_EU,
        "level": "country",
        "country_code": "DE",
        "is_active": True,
        "metadata_json": None,
    },
    {
        "id": ID_IT,
        "code": "it",
        "name": "Italia",
        "parent_id": ID_EU,
        "level": "country",
        "country_code": "IT",
        "is_active": True,
        "metadata_json": None,
    },
    {
        "id": ID_AT,
        "code": "at",
        "name": "Osterreich",
        "parent_id": ID_EU,
        "level": "country",
        "country_code": "AT",
        "is_active": True,
        "metadata_json": None,
    },
    # Swiss cantons
    {
        "id": ID_CH_VD,
        "code": "ch-vd",
        "name": "Canton de Vaud",
        "parent_id": ID_CH,
        "level": "region",
        "country_code": "CH",
        "is_active": True,
        "metadata_json": {
            "authority_name": "DGE-DIRNA",
            "canton_code": "VD",
            "diagnostic_required_before_year": 1991,
            "requires_waste_elimination_plan": True,
            "form_name": "Plan d'elimination des dechets (PED)",
            "notification_delay_days": 14,
        },
    },
    {
        "id": ID_CH_GE,
        "code": "ch-ge",
        "name": "Canton de Geneve",
        "parent_id": ID_CH,
        "level": "region",
        "country_code": "CH",
        "is_active": True,
        "metadata_json": {
            "authority_name": "GESDEC",
            "canton_code": "GE",
            "online_system": "SADEC",
            "diagnostic_required_before_year": 1991,
            "requires_waste_elimination_plan": True,
            "form_name": "Formulaire GESDEC diagnostic polluants",
            "notification_delay_days": 14,
        },
    },
    {
        "id": ID_CH_ZH,
        "code": "ch-zh",
        "name": "Kanton Zurich",
        "parent_id": ID_CH,
        "level": "region",
        "country_code": "CH",
        "is_active": True,
        "metadata_json": {
            "authority_name": "AWEL",
            "canton_code": "ZH",
            "diagnostic_required_before_year": 1991,
            "requires_waste_elimination_plan": True,
            "form_name": "Checkliste Schadstoffe im Gebaude",
            "notification_delay_days": 14,
        },
    },
    {
        "id": ID_CH_BE,
        "code": "ch-be",
        "name": "Kanton Bern / Canton de Berne",
        "parent_id": ID_CH,
        "level": "region",
        "country_code": "CH",
        "is_active": True,
        "metadata_json": {
            "authority_name": "AWA",
            "canton_code": "BE",
            "diagnostic_required_before_year": 1991,
            "requires_waste_elimination_plan": True,
            "form_name": "Notice intercantonale diagnostic polluants",
            "notification_delay_days": 14,
        },
    },
    {
        "id": ID_CH_VS,
        "code": "ch-vs",
        "name": "Canton du Valais / Kanton Wallis",
        "parent_id": ID_CH,
        "level": "region",
        "country_code": "CH",
        "is_active": True,
        "metadata_json": {
            "authority_name": "SEN",
            "canton_code": "VS",
            "diagnostic_required_before_year": 1991,
            "requires_waste_elimination_plan": True,
            "form_name": "Notice diagnostic polluants et plan d'elimination",
            "notification_delay_days": 14,
        },
    },
]

# ---------------------------------------------------------------------------
# Swiss federal regulatory packs (CH level)
# ---------------------------------------------------------------------------

REGULATORY_PACKS_CH = [
    # Asbestos — material content
    {
        "jurisdiction_id": ID_CH,
        "pollutant_type": "asbestos",
        "version": "1.0",
        "threshold_value": 1.0,
        "threshold_unit": "percent_weight",
        "threshold_action": "remediate",
        "risk_year_start": 1920,
        "risk_year_end": 1990,
        "base_probability": 0.85,
        "legal_reference": "OTConst Art. 60a, 82-86; FACH 2018",
        "legal_url": "https://www.fedlex.admin.ch/eli/cc/2005/43/fr",
        "description_fr": "Toute presence d'amiante dans les materiaux de construction doit faire l'objet d'un assainissement.",
        "description_de": "Jedes Vorkommen von Asbest in Baumaterialien muss saniert werden.",
        "notification_required": True,
        "notification_authority": "SUVA",
        "notification_delay_days": 14,
        "work_categories_json": {
            "minor": {
                "description": "Non-friable, bon etat, surface <= 5 m2",
                "legal_ref": "CFST 6503",
            },
            "medium": {
                "description": "Surface moyenne ou etat degrade",
                "legal_ref": "CFST 6503",
            },
            "major": {
                "description": "Grande surface (>10 m2), friable ou tres degrade",
                "legal_ref": "CFST 6503",
            },
        },
        "waste_classification_json": {
            "friable": "special",
            "bonded_good": "type_b",
            "bonded_degraded": "type_e",
            "default": "type_e",
        },
    },
    # PCB — material content
    {
        "jurisdiction_id": ID_CH,
        "pollutant_type": "pcb",
        "version": "1.0",
        "threshold_value": 50.0,
        "threshold_unit": "mg_per_kg",
        "threshold_action": "remediate",
        "risk_year_start": 1955,
        "risk_year_end": 1986,
        "base_probability": 0.70,
        "legal_reference": "ORRChim Annexe 2.15",
        "legal_url": "https://www.fedlex.admin.ch/eli/cc/2005/478/fr",
        "description_fr": "Les materiaux contenant plus de 50 mg/kg de PCB doivent etre elimines comme dechets speciaux.",
        "description_de": "Materialien mit mehr als 50 mg/kg PCB mussen als Sonderabfall entsorgt werden.",
        "notification_required": False,
        "waste_classification_json": {"default": "special"},
    },
    # Lead — paint content
    {
        "jurisdiction_id": ID_CH,
        "pollutant_type": "lead",
        "version": "1.0",
        "threshold_value": 5000.0,
        "threshold_unit": "mg_per_kg",
        "threshold_action": "remediate",
        "risk_year_start": None,
        "risk_year_end": 1980,
        "base_probability": 0.60,
        "legal_reference": "ORRChim Annexe 2.18",
        "legal_url": "https://www.fedlex.admin.ch/eli/cc/2005/478/fr",
        "description_fr": "Les peintures contenant plus de 5000 mg/kg de plomb doivent etre traitees.",
        "description_de": "Farben mit mehr als 5000 mg/kg Blei mussen behandelt werden.",
        "notification_required": False,
        "waste_classification_json": {
            "friable": "special",
            "default": "type_e",
        },
    },
    # HAP — material content
    {
        "jurisdiction_id": ID_CH,
        "pollutant_type": "hap",
        "version": "1.0",
        "threshold_value": 200.0,
        "threshold_unit": "mg_per_kg",
        "threshold_action": "remediate",
        "risk_year_start": 1940,
        "risk_year_end": 1985,
        "base_probability": 0.55,
        "legal_reference": "OLED dechet special",
        "description_fr": "Les materiaux contenant plus de 200 mg/kg de HAP sont des dechets speciaux.",
        "description_de": "Materialien mit mehr als 200 mg/kg PAK sind Sonderabfall.",
        "notification_required": False,
        "waste_classification_json": {"default": "special"},
    },
    # Radon — reference value
    {
        "jurisdiction_id": ID_CH,
        "pollutant_type": "radon",
        "version": "1.0",
        "threshold_value": 300.0,
        "threshold_unit": "bq_per_m3",
        "threshold_action": "monitor",
        "risk_year_start": None,
        "risk_year_end": None,
        "base_probability": 0.30,
        "legal_reference": "ORaP Art. 110 (valeur de reference)",
        "legal_url": "https://www.fedlex.admin.ch/eli/cc/2017/503/fr",
        "description_fr": "Valeur de reference: 300 Bq/m3. Au-dela, des mesures d'assainissement sont recommandees.",
        "description_de": "Referenzwert: 300 Bq/m3. Daruber hinaus werden Sanierungsmassnahmen empfohlen.",
        "notification_required": False,
    },
    # Radon — mandatory action value
    {
        "jurisdiction_id": ID_CH,
        "pollutant_type": "radon",
        "version": "1.0-action",
        "threshold_value": 1000.0,
        "threshold_unit": "bq_per_m3",
        "threshold_action": "remediate",
        "risk_year_start": None,
        "risk_year_end": None,
        "base_probability": 0.10,
        "legal_reference": "ORaP Art. 110 (valeur limite)",
        "legal_url": "https://www.fedlex.admin.ch/eli/cc/2017/503/fr",
        "description_fr": "Valeur limite: 1000 Bq/m3. Au-dela, un assainissement est obligatoire.",
        "description_de": "Grenzwert: 1000 Bq/m3. Daruber hinaus ist eine Sanierung obligatorisch.",
        "notification_required": True,
        "notification_authority": "Service cantonal de radioprotection",
        "notification_delay_days": 30,
    },
]

# ---------------------------------------------------------------------------
# Cantonal regulatory packs (where they differ from federal)
# ---------------------------------------------------------------------------

REGULATORY_PACKS_VD = [
    {
        "jurisdiction_id": ID_CH_VD,
        "pollutant_type": "asbestos",
        "version": "1.0",
        "threshold_value": 1.0,
        "threshold_unit": "percent_weight",
        "threshold_action": "remediate",
        "legal_reference": "Directive cantonale VD, DGE-DIRNA",
        "description_fr": "Le canton de Vaud exige un Plan d'elimination des dechets (PED) pour tout chantier avec amiante.",
        "notification_required": True,
        "notification_authority": "DGE-DIRNA",
        "notification_delay_days": 14,
        "work_categories_json": {
            "requirement": "Plan d'elimination des dechets (PED)",
            "diagnostic_required_before_year": 1991,
        },
    },
]

REGULATORY_PACKS_GE = [
    {
        "jurisdiction_id": ID_CH_GE,
        "pollutant_type": "asbestos",
        "version": "1.0",
        "threshold_value": 1.0,
        "threshold_unit": "percent_weight",
        "threshold_action": "remediate",
        "legal_reference": "Directive cantonale GE, GESDEC",
        "description_fr": "Le canton de Geneve requiert un formulaire GESDEC et utilise le systeme SADEC.",
        "notification_required": True,
        "notification_authority": "GESDEC",
        "notification_delay_days": 14,
        "work_categories_json": {
            "requirement": "Formulaire GESDEC diagnostic polluants",
            "online_system": "SADEC",
            "diagnostic_required_before_year": 1991,
        },
    },
]


async def _upsert_jurisdiction(session, data: dict) -> Jurisdiction:
    """Insert or update a jurisdiction by id."""
    result = await session.execute(select(Jurisdiction).where(Jurisdiction.id == data["id"]))
    existing = result.scalar_one_or_none()
    if existing:
        for key, value in data.items():
            if key != "id":
                setattr(existing, key, value)
        return existing
    jurisdiction = Jurisdiction(**data)
    session.add(jurisdiction)
    return jurisdiction


async def _upsert_regulatory_pack(session, data: dict) -> RegulatoryPack:
    """Insert or update a regulatory pack by jurisdiction_id + pollutant_type + version."""
    version = data.get("version", "1.0")
    result = await session.execute(
        select(RegulatoryPack).where(
            RegulatoryPack.jurisdiction_id == data["jurisdiction_id"],
            RegulatoryPack.pollutant_type == data["pollutant_type"],
            RegulatoryPack.version == version,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        for key, value in data.items():
            if key != "id":
                setattr(existing, key, value)
        return existing
    pack = RegulatoryPack(**data)
    session.add(pack)
    return pack


async def seed_jurisdictions():
    """Idempotent seed for jurisdictions and regulatory packs."""
    async with AsyncSessionLocal() as session:
        # Seed jurisdictions (order matters for FK constraints)
        for jur_data in JURISDICTIONS:
            await _upsert_jurisdiction(session, jur_data)
        await session.flush()

        # Seed regulatory packs
        all_packs = REGULATORY_PACKS_CH + REGULATORY_PACKS_VD + REGULATORY_PACKS_GE
        for pack_data in all_packs:
            await _upsert_regulatory_pack(session, pack_data)

        await session.commit()

    print(f"Seeded {len(JURISDICTIONS)} jurisdictions and {len(all_packs)} regulatory packs.")


if __name__ == "__main__":
    asyncio.run(seed_jurisdictions())
