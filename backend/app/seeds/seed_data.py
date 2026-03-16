"""
SwissBuildingOS - Seed Data
Idempotent seed script for development and demo environments.

Usage:
    python -m app.seeds.seed_data
"""

import asyncio
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import select

from app.constants import DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD
from app.database import AsyncSessionLocal
from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.campaign import Campaign
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.models.evidence_link import EvidenceLink
from app.models.export_job import ExportJob
from app.models.intervention import Intervention
from app.models.invitation import Invitation
from app.models.material import Material
from app.models.notification import Notification, NotificationPreference
from app.models.organization import Organization
from app.models.pollutant_rule import PollutantRule
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.user import User
from app.models.zone import Zone
from app.seeds.seed_jurisdictions import (
    ID_CH_BE,
    ID_CH_GE,
    ID_CH_VD,
    ID_CH_VS,
    ID_CH_ZH,
    seed_jurisdictions,
)
from app.services.action_generator import generate_actions_from_diagnostic

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Canton code → jurisdiction UUID mapping (only for seeded cantons)
_CANTON_JURISDICTION = {
    "VD": ID_CH_VD,
    "GE": ID_CH_GE,
    "ZH": ID_CH_ZH,
    "BE": ID_CH_BE,
    "VS": ID_CH_VS,
    "FR": None,  # Fribourg not seeded as jurisdiction
}

# Stable UUID5 namespace for scenario buildings (idempotent)
_SCENARIO_NS = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")
SCENARIO_IDS = {
    "contradiction": uuid.uuid5(_SCENARIO_NS, "scenario-contradiction-building"),
    "nearly_ready": uuid.uuid5(_SCENARIO_NS, "scenario-nearly-ready-building"),
    "post_works": uuid.uuid5(_SCENARIO_NS, "scenario-post-works-building"),
    "portfolio_cluster": uuid.uuid5(_SCENARIO_NS, "scenario-portfolio-cluster-building"),
    "empty_dossier": uuid.uuid5(_SCENARIO_NS, "scenario-empty-dossier-building"),
    # Diagnostics
    "contradiction_diag_pos": uuid.uuid5(_SCENARIO_NS, "scenario-contradiction-diag-positive"),
    "contradiction_diag_neg": uuid.uuid5(_SCENARIO_NS, "scenario-contradiction-diag-negative"),
    "nearly_ready_diag": uuid.uuid5(_SCENARIO_NS, "scenario-nearly-ready-diag"),
    "post_works_diag": uuid.uuid5(_SCENARIO_NS, "scenario-post-works-diag"),
    # Samples
    "contradiction_sample_pos": uuid.uuid5(_SCENARIO_NS, "scenario-contradiction-sample-pos"),
    "contradiction_sample_neg": uuid.uuid5(_SCENARIO_NS, "scenario-contradiction-sample-neg"),
    "nearly_ready_sample1": uuid.uuid5(_SCENARIO_NS, "scenario-nearly-ready-sample1"),
    "nearly_ready_sample2": uuid.uuid5(_SCENARIO_NS, "scenario-nearly-ready-sample2"),
    "post_works_sample": uuid.uuid5(_SCENARIO_NS, "scenario-post-works-sample"),
    # Artefacts
    "nearly_ready_artefact_ok": uuid.uuid5(_SCENARIO_NS, "scenario-nearly-ready-artefact-ok"),
    "nearly_ready_artefact_pending": uuid.uuid5(_SCENARIO_NS, "scenario-nearly-ready-artefact-pending"),
    # Interventions
    "post_works_intervention": uuid.uuid5(_SCENARIO_NS, "scenario-post-works-intervention"),
}


def _risk_score(construction_year, canton, building_type):
    """
    Compute realistic risk probabilities based on Swiss construction
    era, canton radon zones, and building type.
    """
    # -- Asbestos: peak usage 1950-1990 in Switzerland
    if construction_year is None:
        asb = 0.5
    elif construction_year < 1940:
        asb = 0.15
    elif construction_year <= 1960:
        asb = 0.70
    elif construction_year <= 1975:
        asb = 0.92
    elif construction_year <= 1990:
        asb = 0.75
    else:
        asb = 0.05

    # -- PCB: used 1955-1975 in sealants, capacitors, paints
    if construction_year is None:
        pcb = 0.4
    elif 1955 <= construction_year <= 1975:
        pcb = 0.80
    elif 1945 <= construction_year < 1955:
        pcb = 0.30
    elif 1975 < construction_year <= 1985:
        pcb = 0.40
    else:
        pcb = 0.05

    # -- Lead paint: common before 1960
    if construction_year is None:
        lead = 0.4
    elif construction_year < 1950:
        lead = 0.85
    elif construction_year <= 1970:
        lead = 0.55
    elif construction_year <= 1990:
        lead = 0.20
    else:
        lead = 0.05

    # -- HAP (PAH): coal tar products, pre-1970
    if construction_year is None:
        hap = 0.3
    elif construction_year < 1960:
        hap = 0.65
    elif construction_year <= 1975:
        hap = 0.45
    else:
        hap = 0.10

    # -- Radon: geological zones (simplified by canton)
    radon_high = {"JU", "NE", "TI", "GR", "VS", "BE"}
    radon_medium = {"VD", "FR", "BL", "SO", "SH", "AI", "AR"}
    if canton in radon_high:
        radon = 0.70
    elif canton in radon_medium:
        radon = 0.40
    else:
        radon = 0.15

    # -- Industrial buildings have higher contamination risk
    if building_type == "industrial":
        asb = min(asb * 1.15, 1.0)
        pcb = min(pcb * 1.20, 1.0)
        hap = min(hap * 1.30, 1.0)

    # -- Overall risk level (must match frontend RiskLevel type)
    max_p = max(asb, pcb, lead, hap, radon)
    if max_p >= 0.80:
        level = "critical"
    elif max_p >= 0.60:
        level = "high"
    elif max_p >= 0.35:
        level = "medium"
    else:
        level = "low"

    confidence = round(0.65 + 0.15 * (1 if construction_year and construction_year < 1990 else 0), 2)

    return {
        "asbestos_probability": round(asb, 2),
        "pcb_probability": round(pcb, 2),
        "lead_probability": round(lead, 2),
        "hap_probability": round(hap, 2),
        "radon_probability": round(radon, 2),
        "overall_risk_level": level,
        "confidence": confidence,
    }


async def seed():
    # Seed jurisdictions first (idempotent, uses its own session)
    await seed_jurisdictions()

    async with AsyncSessionLocal() as db:
        # ── Idempotency check ──────────────────────────────────────────
        result = await db.execute(select(User).where(User.email == DEMO_ADMIN_EMAIL))
        existing_admin = result.scalar_one_or_none()
        if existing_admin:
            if not pwd.verify(DEMO_ADMIN_PASSWORD, existing_admin.password_hash):
                existing_admin.password_hash = pwd.hash(DEMO_ADMIN_PASSWORD)
                existing_admin.is_active = True
                await db.commit()
                print("[SEED] Demo admin password reset to default.")
            print("[SEED] Data already exists \u2014 skipping.")
            return

        # ── Organizations ──────────────────────────────────────────────
        org1 = Organization(
            id=uuid.uuid4(),
            name="DiagSwiss SA",
            type="diagnostic_lab",
            address="Route de Berne 45",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            email="info@diagswiss.ch",
            suva_recognized=True,
            fach_approved=True,
        )
        org2 = Organization(
            id=uuid.uuid4(),
            name="R\u00e9gie Romande Immobilier SA",
            type="property_management",
            address="Rue du Rh\u00f4ne 12",
            postal_code="1204",
            city="Gen\u00e8ve",
            canton="GE",
            email="contact@regieromande.ch",
            suva_recognized=False,
            fach_approved=False,
        )
        db.add_all([org1, org2])
        await db.flush()

        # ── Users ──────────────────────────────────────────────────────
        admin = User(
            id=uuid.uuid4(),
            email=DEMO_ADMIN_EMAIL,
            password_hash=pwd.hash(DEMO_ADMIN_PASSWORD),
            first_name="Admin",
            last_name="System",
            role="admin",
            language="fr",
            is_active=True,
            organization_id=org1.id,
        )
        diagnostician = User(
            id=uuid.uuid4(),
            email="jean.muller@diagswiss.ch",
            password_hash=pwd.hash("diag123"),
            first_name="Jean-Pierre",
            last_name="M\u00fcller",
            role="diagnostician",
            language="fr",
            is_active=True,
            organization_id=org1.id,
        )
        owner = User(
            id=uuid.uuid4(),
            email="sophie.martin@regieromande.ch",
            password_hash=pwd.hash("owner123"),
            first_name="Sophie",
            last_name="Martin",
            role="owner",
            language="fr",
            is_active=True,
            organization_id=org2.id,
        )
        # Additional organizations for MP2
        org3 = Organization(
            id=uuid.uuid4(),
            name="Archi+Bau AG",
            type="architecture_firm",
            address="Bahnhofstrasse 88",
            postal_code="8001",
            city="Zürich",
            canton="ZH",
            email="info@archibau.ch",
            phone="+41 44 555 66 77",
            suva_recognized=False,
            fach_approved=True,
        )
        org4 = Organization(
            id=uuid.uuid4(),
            name="Canton de Vaud - DIREN",
            type="authority",
            address="Place de la Riponne 10",
            postal_code="1014",
            city="Lausanne",
            canton="VD",
            email="diren@vd.ch",
            suva_recognized=False,
            fach_approved=False,
        )
        org5 = Organization(
            id=uuid.uuid4(),
            name="Sanacore Bau GmbH",
            type="contractor",
            address="Industriestrasse 12",
            postal_code="3001",
            city="Bern",
            canton="BE",
            email="kontakt@sanacore.ch",
            phone="+41 31 999 88 77",
            suva_recognized=True,
            fach_approved=False,
        )
        db.add_all([org3, org4, org5])
        await db.flush()

        db.add_all([admin, diagnostician, owner])
        await db.flush()

        # Additional users for MP2
        architect = User(
            id=uuid.uuid4(),
            email="marco.brunetti@archibau.ch",
            password_hash=pwd.hash("archi123"),
            first_name="Marco",
            last_name="Brunetti",
            role="architect",
            language="de",
            is_active=True,
            organization_id=org3.id,
        )
        authority = User(
            id=uuid.uuid4(),
            email="claire.dubois@vd.ch",
            password_hash=pwd.hash("auth123"),
            first_name="Claire",
            last_name="Dubois",
            role="authority",
            language="fr",
            is_active=True,
            organization_id=org4.id,
        )
        contractor = User(
            id=uuid.uuid4(),
            email="hans.weber@sanacore.ch",
            password_hash=pwd.hash("cont123"),
            first_name="Hans",
            last_name="Weber",
            role="contractor",
            language="de",
            is_active=True,
            organization_id=org5.id,
        )
        inactive_user = User(
            id=uuid.uuid4(),
            email="ancien.employe@diagswiss.ch",
            password_hash=pwd.hash("old12345"),
            first_name="Pierre",
            last_name="Ancien",
            role="diagnostician",
            language="fr",
            is_active=False,
            organization_id=org1.id,
        )
        db.add_all([architect, authority, contractor, inactive_user])
        await db.flush()

        # ── Buildings ──────────────────────────────────────────────────
        building_defs = [
            {
                "address": "Chemin des P\u00e2querettes 12",
                "postal_code": "1004",
                "city": "Lausanne",
                "canton": "VD",
                "construction_year": 1962,
                "renovation_year": 1988,
                "building_type": "residential",
                "floors_above": 6,
                "floors_below": 1,
                "surface_area_m2": 2400.0,
                "latitude": 46.5197,
                "longitude": 6.6323,
            },
            {
                "address": "Quai du Rh\u00f4ne 45",
                "postal_code": "1204",
                "city": "Gen\u00e8ve",
                "canton": "GE",
                "construction_year": 1955,
                "renovation_year": None,
                "building_type": "mixed",
                "floors_above": 8,
                "floors_below": 2,
                "surface_area_m2": 3200.0,
                "latitude": 46.2044,
                "longitude": 6.1432,
            },
            {
                "address": "Industriestrasse 22",
                "postal_code": "2502",
                "city": "Biel/Bienne",
                "canton": "BE",
                "construction_year": 1972,
                "renovation_year": None,
                "building_type": "industrial",
                "floors_above": 2,
                "floors_below": 0,
                "surface_area_m2": 5000.0,
                "latitude": 47.1368,
                "longitude": 7.2467,
            },
            {
                "address": "Rue de l'\u00c9cole 8",
                "postal_code": "1950",
                "city": "Sion",
                "canton": "VS",
                "construction_year": 1948,
                "renovation_year": 1975,
                "building_type": "public",
                "floors_above": 3,
                "floors_below": 1,
                "surface_area_m2": 1800.0,
                "latitude": 46.2333,
                "longitude": 7.3667,
            },
            {
                "address": "Bahnhofstrasse 100",
                "postal_code": "8001",
                "city": "Z\u00fcrich",
                "canton": "ZH",
                "construction_year": 1985,
                "renovation_year": None,
                "building_type": "commercial",
                "floors_above": 12,
                "floors_below": 3,
                "surface_area_m2": 8500.0,
                "latitude": 47.3769,
                "longitude": 8.5417,
            },
        ]

        buildings = []
        for bdef in building_defs:
            b = Building(
                id=uuid.uuid4(),
                address=bdef["address"],
                postal_code=bdef["postal_code"],
                city=bdef["city"],
                canton=bdef["canton"],
                construction_year=bdef["construction_year"],
                renovation_year=bdef["renovation_year"],
                building_type=bdef["building_type"],
                floors_above=bdef["floors_above"],
                floors_below=bdef["floors_below"],
                surface_area_m2=bdef["surface_area_m2"],
                latitude=bdef["latitude"],
                longitude=bdef["longitude"],
                created_by=admin.id,
                owner_id=owner.id if bdef["canton"] in ("VD", "GE") else None,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get(bdef["canton"]),
            )
            buildings.append(b)
        db.add_all(buildings)
        await db.flush()

        # ── Pollutant Rules (Swiss regulatory framework) ───────────────
        pollutant_rules = [
            # --- ASBESTOS ---
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="asbestos",
                material_category="all_materials",
                risk_start_year=1904,
                risk_end_year=1990,
                threshold_value=1.0,
                threshold_unit="percent_weight",
                diagnostic_required=True,
                legal_reference="FACH 2018 \u2014 Directive amiante",
                action_if_exceeded="Assainissement obligatoire selon urgence FACH; notification SUVA pour travaux",
                waste_disposal_type="special",
                cfst_default_category="medium",
                canton_specific=None,
                description_fr="Seuil de d\u00e9tection amiante dans mat\u00e9riaux: teneur > 1% en poids \u2192 positif",
                description_de="Asbestnachweisgrenze in Materialien: Gehalt > 1 Gew.-% \u2192 positiv",
            ),
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="asbestos",
                material_category="air_measurement",
                risk_start_year=1904,
                risk_end_year=1990,
                threshold_value=1000.0,
                threshold_unit="LAF/m\u00b3",
                diagnostic_required=True,
                legal_reference="OHyg art. 4 \u2014 VLT amiante (valeur limite technique)",
                action_if_exceeded="\u00c9vacuation et assainissement imm\u00e9diat; zone confin\u00e9e obligatoire",
                waste_disposal_type="special",
                cfst_default_category="high",
                canton_specific=None,
                description_fr="Valeur limite technique (VLT) amiante dans l'air: 1000 LAF/m\u00b3",
                description_de="Technischer Expositionsgrenzwert (TEG) Asbest in der Luft: 1000 LAF/m\u00b3",
            ),
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="asbestos",
                material_category="air_workplace",
                risk_start_year=1904,
                risk_end_year=1990,
                threshold_value=10000.0,
                threshold_unit="LAF/m\u00b3",
                diagnostic_required=True,
                legal_reference="SUVA Grenzwert \u2014 VLE amiante (valeur limite d'exposition)",
                action_if_exceeded="Arr\u00eat imm\u00e9diat des travaux; protection respiratoire P3 obligatoire",
                waste_disposal_type="special",
                cfst_default_category="high",
                canton_specific=None,
                description_fr="Valeur limite d'exposition professionnelle (VLE) amiante: 10'000 LAF/m\u00b3 sur 8h",
                description_de="Maximaler Arbeitsplatzgrenzwert (MAK) Asbest: 10'000 LAF/m\u00b3 \u00fcber 8h",
            ),
            # --- PCB ---
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="pcb",
                material_category="joint_sealant",
                risk_start_year=1955,
                risk_end_year=1975,
                threshold_value=50.0,
                threshold_unit="mg/kg",
                diagnostic_required=True,
                legal_reference="ORRChim annexe 2.15 \u2014 Interdiction PCB",
                action_if_exceeded="D\u00e9contamination obligatoire; \u00e9limination en tant que d\u00e9chet sp\u00e9cial (OLED)",
                waste_disposal_type="special",
                cfst_default_category="medium",
                canton_specific=None,
                description_fr="Seuil PCB dans les mat\u00e9riaux de construction (joints, mastics): > 50 mg/kg",
                description_de="PCB-Grenzwert in Baumaterialien (Fugen, Dichtungsmassen): > 50 mg/kg",
            ),
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="pcb",
                material_category="air_indoor",
                risk_start_year=1955,
                risk_end_year=1975,
                threshold_value=6000.0,
                threshold_unit="ng/m\u00b3",
                diagnostic_required=True,
                legal_reference="OFSP 2019 \u2014 Valeur directrice PCB air int\u00e9rieur",
                action_if_exceeded="Assainissement des sources; ventilation renforc\u00e9e; contr\u00f4le apr\u00e8s travaux",
                waste_disposal_type="special",
                cfst_default_category="medium",
                canton_specific=None,
                description_fr="Valeur directrice PCB dans l'air int\u00e9rieur: < 6000 ng/m\u00b3 (OFSP)",
                description_de="PCB-Richtwert in der Innenraumluft: < 6000 ng/m\u00b3 (BAG)",
            ),
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="pcb",
                material_category="waste_threshold",
                risk_start_year=1955,
                risk_end_year=1975,
                threshold_value=10.0,
                threshold_unit="mg/kg",
                diagnostic_required=False,
                legal_reference="OLED annexe 1 \u2014 D\u00e9chet sp\u00e9cial PCB",
                action_if_exceeded="\u00c9limination en tant que d\u00e9chet sp\u00e9cial; fili\u00e8re agr\u00e9\u00e9e obligatoire",
                waste_disposal_type="special",
                cfst_default_category=None,
                canton_specific=None,
                description_fr="Seuil d\u00e9chet sp\u00e9cial PCB: > 10 mg/kg selon OLED",
                description_de="Sonderabfall-Grenzwert PCB: > 10 mg/kg gem\u00e4ss VVEA",
            ),
            # --- LEAD ---
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="lead",
                material_category="paint",
                risk_start_year=1900,
                risk_end_year=1970,
                threshold_value=5000.0,
                threshold_unit="mg/kg",
                diagnostic_required=True,
                legal_reference="ORRChim annexe 2.18 \u2014 Interdiction plomb dans peintures",
                action_if_exceeded="D\u00e9capage contr\u00f4l\u00e9; protection des travailleurs; \u00e9limination d\u00e9chet sp\u00e9cial",
                waste_disposal_type="special",
                cfst_default_category="low",
                canton_specific=None,
                description_fr="Seuil plomb dans peintures anciennes: > 5000 mg/kg (0.5%)",
                description_de="Blei-Grenzwert in Altanstrichen: > 5000 mg/kg (0.5%)",
            ),
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="lead",
                material_category="drinking_water",
                risk_start_year=1900,
                risk_end_year=1970,
                threshold_value=10.0,
                threshold_unit="\u03bcg/l",
                diagnostic_required=True,
                legal_reference="OSEC annexe 2 \u2014 Eau potable plomb",
                action_if_exceeded="Remplacement des conduites en plomb; rin\u00e7age r\u00e9gulier en attendant",
                waste_disposal_type="controlled",
                cfst_default_category=None,
                canton_specific=None,
                description_fr="Valeur de tol\u00e9rance plomb dans l'eau potable: < 10 \u03bcg/l (OSEC)",
                description_de="Toleranzwert Blei im Trinkwasser: < 10 \u03bcg/l (FIV)",
            ),
            # --- HAP (PAH) ---
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="hap",
                material_category="tar_products",
                risk_start_year=1900,
                risk_end_year=1970,
                threshold_value=200.0,
                threshold_unit="mg/kg",
                diagnostic_required=True,
                legal_reference="OLED annexe 1 \u2014 D\u00e9chet sp\u00e9cial HAP",
                action_if_exceeded="\u00c9limination en tant que d\u00e9chet sp\u00e9cial; interdiction de r\u00e9utilisation",
                waste_disposal_type="special",
                cfst_default_category="medium",
                canton_specific=None,
                description_fr="Seuil HAP (16 EPA) dans mat\u00e9riaux goudronneux: > 200 mg/kg \u2192 d\u00e9chet sp\u00e9cial",
                description_de="PAK-Grenzwert (16 EPA) in Teerprodukten: > 200 mg/kg \u2192 Sonderabfall",
            ),
            # --- RADON ---
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="radon",
                material_category="indoor_air",
                risk_start_year=None,
                risk_end_year=None,
                threshold_value=300.0,
                threshold_unit="Bq/m\u00b3",
                diagnostic_required=True,
                legal_reference="ORaP art. 110 \u2014 Valeur de r\u00e9f\u00e9rence radon",
                action_if_exceeded="Mesures d'assainissement recommand\u00e9es; ventilation du sous-sol",
                waste_disposal_type=None,
                cfst_default_category=None,
                canton_specific=None,
                description_fr="Valeur de r\u00e9f\u00e9rence radon en locaux d'habitation: 300 Bq/m\u00b3 (ORaP)",
                description_de="Radon-Referenzwert in Wohnr\u00e4umen: 300 Bq/m\u00b3 (StSV)",
            ),
            PollutantRule(
                id=uuid.uuid4(),
                pollutant="radon",
                material_category="indoor_air",
                risk_start_year=None,
                risk_end_year=None,
                threshold_value=1000.0,
                threshold_unit="Bq/m\u00b3",
                diagnostic_required=True,
                legal_reference="ORaP art. 110 \u2014 Seuil d'action obligatoire radon",
                action_if_exceeded="Assainissement obligatoire dans un d\u00e9lai fix\u00e9 par l'autorit\u00e9 cantonale",
                waste_disposal_type=None,
                cfst_default_category=None,
                canton_specific=None,
                description_fr="Seuil d'action obligatoire radon: 1000 Bq/m\u00b3 \u2014 assainissement exig\u00e9",
                description_de="Radon-Massnahmenschwelle: 1000 Bq/m\u00b3 \u2014 Sanierung erforderlich",
            ),
        ]
        db.add_all(pollutant_rules)
        await db.flush()

        # ── Diagnostics & Samples ──────────────────────────────────────

        # Diagnostic 1: Lausanne building, completed full diagnostic
        diag1 = Diagnostic(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            diagnostic_type="full",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="Laboratoire EMPA Suisse",
            laboratory_report_number="EMPA-2025-04872",
            date_inspection=date(2025, 9, 15),
            date_report=date(2025, 10, 2),
            summary="Diagnostic complet avant travaux de r\u00e9novation \u00e9nerg\u00e9tique. "
            "Pr\u00e9sence confirm\u00e9e d'amiante chrysotile dans les rev\u00eatements de sol vinyle (15%) "
            "et de PCB dans les joints de fa\u00e7ade (1250 mg/kg). Plomb dans peintures sous le seuil.",
            conclusion="positive",
            methodology="VDI 3866 / SIA 118/430",
            suva_notification_required=True,
            suva_notification_date=date(2025, 10, 5),
        )
        db.add(diag1)
        await db.flush()

        sample1_1 = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag1.id,
            sample_number="LS-2025-001",
            location_floor="2\u00e8me \u00e9tage",
            location_room="Appartement 2.1 \u2014 Salon",
            location_detail="Rev\u00eatement de sol vinyle coll\u00e9 sur chape",
            material_category="floor_covering_vinyl",
            material_description="Dalles vinyle-amiante 30x30 cm, beige marbr\u00e9, coll\u00e9es",
            material_state="intact",
            pollutant_type="asbestos",
            pollutant_subtype="chrysotile",
            concentration=15.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
            action_required="containment_before_removal",
            waste_disposal_type="special",
            notes="Mat\u00e9riau non friable mais concentration \u00e9lev\u00e9e. "
            "Retrait par entreprise agr\u00e9\u00e9e SUVA obligatoire.",
        )
        sample1_2 = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag1.id,
            sample_number="LS-2025-002",
            location_floor="Fa\u00e7ade",
            location_room="Fa\u00e7ade sud",
            location_detail="Joint d'\u00e9tanch\u00e9it\u00e9 entre panneaux pr\u00e9fabriqu\u00e9s",
            material_category="facade_joint_sealant",
            material_description="Mastic d'\u00e9tanch\u00e9it\u00e9 gris-noir, souple, entre \u00e9l\u00e9ments de fa\u00e7ade",
            material_state="degraded",
            pollutant_type="pcb",
            pollutant_subtype="Aroclor 1260",
            concentration=1250.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
            action_required="decontamination",
            waste_disposal_type="special",
            notes="Concentration PCB 25x sup\u00e9rieure au seuil ORRChim (50 mg/kg). "
            "D\u00e9contamination compl\u00e8te de la fa\u00e7ade n\u00e9cessaire.",
        )
        sample1_3 = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag1.id,
            sample_number="LS-2025-003",
            location_floor="4\u00e8me \u00e9tage",
            location_room="Appartement 4.2 \u2014 Chambre",
            location_detail="Peinture sur boiseries de fen\u00eatre",
            material_category="lead_paint",
            material_description="Peinture blanche multicouche sur cadres de fen\u00eatres bois",
            material_state="intact",
            pollutant_type="lead",
            pollutant_subtype=None,
            concentration=4200.0,
            unit="mg_per_kg",
            threshold_exceeded=False,
            risk_level="low",
            cfst_work_category=None,
            action_required="monitoring",
            waste_disposal_type="controlled",
            notes="Concentration sous le seuil r\u00e9glementaire de 5000 mg/kg. "
            "Surveillance recommand\u00e9e lors de futurs travaux de peinture.",
        )
        db.add_all([sample1_1, sample1_2, sample1_3])

        # Diagnostic 2: Gen\u00e8ve building, in progress
        diag2 = Diagnostic(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="in_progress",
            diagnostician_id=diagnostician.id,
            laboratory="Laboratoire EMPA Suisse",
            laboratory_report_number=None,
            date_inspection=date(2026, 2, 20),
            date_report=None,
            summary="Diagnostic amiante avant transformation du rez-de-chauss\u00e9e commercial. "
            "Flocage suspect identifi\u00e9 dans le faux-plafond du sous-sol.",
            conclusion=None,
            methodology="VDI 3866",
            suva_notification_required=False,
        )
        db.add(diag2)
        await db.flush()

        sample2_1 = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag2.id,
            sample_number="GE-2026-001",
            location_floor="Sous-sol 1",
            location_room="Local technique \u2014 Chaufferie",
            location_detail="Flocage sur structure m\u00e9tallique du faux-plafond",
            material_category="flocage",
            material_description="Flocage fibreux gris-blanc sur poutres m\u00e9talliques, \u00e9paisseur ~3 cm",
            material_state="friable",
            pollutant_type="asbestos",
            pollutant_subtype="chrysotile/amosite",
            concentration=None,
            unit="percent_weight",
            threshold_exceeded=None,
            risk_level="critical",
            cfst_work_category="high",
            action_required="immediate_containment",
            waste_disposal_type="special",
            notes="Mat\u00e9riau friable \u2014 risque critique d'exposition. "
            "Zone confin\u00e9e mise en place. Analyses en laboratoire en cours.",
        )
        db.add(sample2_1)

        # ── Additional Buildings (for realistic data) ────────────────
        extra_building_defs = [
            {
                "address": "Rue du March\u00e9 3",
                "postal_code": "2000",
                "city": "Neuch\u00e2tel",
                "canton": "NE",
                "construction_year": 1935,
                "renovation_year": 1980,
                "building_type": "residential",
                "floors_above": 4,
                "floors_below": 1,
                "surface_area_m2": 1600.0,
                "latitude": 46.9920,
                "longitude": 6.9310,
            },
            {
                "address": "Via Pessina 14",
                "postal_code": "6900",
                "city": "Lugano",
                "canton": "TI",
                "construction_year": 1968,
                "renovation_year": None,
                "building_type": "commercial",
                "floors_above": 5,
                "floors_below": 1,
                "surface_area_m2": 2000.0,
                "latitude": 46.0037,
                "longitude": 8.9511,
            },
            {
                "address": "Kramgasse 52",
                "postal_code": "3011",
                "city": "Bern",
                "canton": "BE",
                "construction_year": 1910,
                "renovation_year": 1995,
                "building_type": "mixed",
                "floors_above": 5,
                "floors_below": 1,
                "surface_area_m2": 1800.0,
                "latitude": 46.9480,
                "longitude": 7.4474,
            },
            {
                "address": "Steinenvorstadt 28",
                "postal_code": "4051",
                "city": "Basel",
                "canton": "BS",
                "construction_year": 1975,
                "renovation_year": None,
                "building_type": "commercial",
                "floors_above": 7,
                "floors_below": 2,
                "surface_area_m2": 3500.0,
                "latitude": 47.5536,
                "longitude": 7.5886,
            },
            {
                "address": "Haldenstrasse 16",
                "postal_code": "6006",
                "city": "Luzern",
                "canton": "LU",
                "construction_year": 1958,
                "renovation_year": None,
                "building_type": "residential",
                "floors_above": 4,
                "floors_below": 1,
                "surface_area_m2": 1400.0,
                "latitude": 47.0502,
                "longitude": 8.3093,
            },
            {
                "address": "Rue de Lausanne 78",
                "postal_code": "1700",
                "city": "Fribourg",
                "canton": "FR",
                "construction_year": 1945,
                "renovation_year": 1972,
                "building_type": "public",
                "floors_above": 3,
                "floors_below": 1,
                "surface_area_m2": 2200.0,
                "latitude": 46.8065,
                "longitude": 7.1620,
            },
            {
                "address": "Bielstrasse 5",
                "postal_code": "4500",
                "city": "Solothurn",
                "canton": "SO",
                "construction_year": 1982,
                "renovation_year": None,
                "building_type": "industrial",
                "floors_above": 2,
                "floors_below": 0,
                "surface_area_m2": 6000.0,
                "latitude": 47.2088,
                "longitude": 7.5372,
            },
            {
                "address": "Rheinstrasse 44",
                "postal_code": "8200",
                "city": "Schaffhausen",
                "canton": "SH",
                "construction_year": 1952,
                "renovation_year": None,
                "building_type": "residential",
                "floors_above": 3,
                "floors_below": 1,
                "surface_area_m2": 900.0,
                "latitude": 47.6961,
                "longitude": 8.6350,
            },
            {
                "address": "Grand-Rue 18",
                "postal_code": "2800",
                "city": "Del\u00e9mont",
                "canton": "JU",
                "construction_year": 1965,
                "renovation_year": None,
                "building_type": "mixed",
                "floors_above": 4,
                "floors_below": 1,
                "surface_area_m2": 1300.0,
                "latitude": 47.3647,
                "longitude": 7.3440,
            },
            {
                "address": "Via San Gottardo 99",
                "postal_code": "6600",
                "city": "Locarno",
                "canton": "TI",
                "construction_year": 1970,
                "renovation_year": 2005,
                "building_type": "residential",
                "floors_above": 6,
                "floors_below": 1,
                "surface_area_m2": 2800.0,
                "latitude": 46.1708,
                "longitude": 8.7960,
            },
            {
                "address": "Bundesplatz 1",
                "postal_code": "3003",
                "city": "Bern",
                "canton": "BE",
                "construction_year": 1902,
                "renovation_year": 1960,
                "building_type": "public",
                "floors_above": 4,
                "floors_below": 2,
                "surface_area_m2": 4000.0,
                "latitude": 46.9466,
                "longitude": 7.4444,
            },
            {
                "address": "Avenue de la Gare 33",
                "postal_code": "1003",
                "city": "Lausanne",
                "canton": "VD",
                "construction_year": 2010,
                "renovation_year": None,
                "building_type": "commercial",
                "floors_above": 8,
                "floors_below": 2,
                "surface_area_m2": 5500.0,
                "latitude": 46.5160,
                "longitude": 6.6290,
            },
            {
                "address": "Marktplatz 7",
                "postal_code": "5000",
                "city": "Aarau",
                "canton": "AG",
                "construction_year": 1960,
                "renovation_year": None,
                "building_type": "mixed",
                "floors_above": 5,
                "floors_below": 1,
                "surface_area_m2": 1700.0,
                "latitude": 47.3925,
                "longitude": 8.0442,
            },
            {
                "address": "Piazza Grande 2",
                "postal_code": "6600",
                "city": "Locarno",
                "canton": "TI",
                "construction_year": 1940,
                "renovation_year": None,
                "building_type": "public",
                "floors_above": 3,
                "floors_below": 0,
                "surface_area_m2": 1500.0,
                "latitude": 46.1710,
                "longitude": 8.7955,
            },
            {
                "address": "Alte Landstrasse 12",
                "postal_code": "8700",
                "city": "K\u00fcsnacht",
                "canton": "ZH",
                "construction_year": 1988,
                "renovation_year": None,
                "building_type": "residential",
                "floors_above": 3,
                "floors_below": 1,
                "surface_area_m2": 1100.0,
                "latitude": 47.3187,
                "longitude": 8.5834,
            },
        ]

        extra_buildings = []
        for bdef in extra_building_defs:
            b = Building(
                id=uuid.uuid4(),
                address=bdef["address"],
                postal_code=bdef["postal_code"],
                city=bdef["city"],
                canton=bdef["canton"],
                construction_year=bdef["construction_year"],
                renovation_year=bdef["renovation_year"],
                building_type=bdef["building_type"],
                floors_above=bdef["floors_above"],
                floors_below=bdef["floors_below"],
                surface_area_m2=bdef["surface_area_m2"],
                latitude=bdef["latitude"],
                longitude=bdef["longitude"],
                created_by=admin.id,
                owner_id=owner.id if bdef["canton"] in ("VD", "GE", "FR", "NE") else None,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get(bdef["canton"]),
            )
            extra_buildings.append(b)
        db.add_all(extra_buildings)
        await db.flush()

        all_buildings = buildings + extra_buildings

        # ── Scenario Buildings (product demo stories) ─────────────────
        scenario_buildings = [
            Building(
                id=SCENARIO_IDS["contradiction"],
                address="Bâtiment Contradictions — Rue de la Gare 8, Yverdon",
                postal_code="1400",
                city="Yverdon-les-Bains",
                canton="VD",
                construction_year=1958,
                building_type="commercial",
                floors_above=4,
                floors_below=1,
                surface_area_m2=1900.0,
                latitude=46.7785,
                longitude=6.6410,
                created_by=admin.id,
                owner_id=owner.id,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get("VD"),
            ),
            Building(
                id=SCENARIO_IDS["nearly_ready"],
                address="Immeuble Presque Prêt — Avenue de Cour 15, Lausanne",
                postal_code="1007",
                city="Lausanne",
                canton="VD",
                construction_year=1970,
                building_type="residential",
                floors_above=5,
                floors_below=1,
                surface_area_m2=2200.0,
                latitude=46.5120,
                longitude=6.6280,
                created_by=admin.id,
                owner_id=owner.id,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get("VD"),
            ),
            Building(
                id=SCENARIO_IDS["post_works"],
                address="Résidence Post-Travaux — Chemin des Alpes 22, Montreux",
                postal_code="1820",
                city="Montreux",
                canton="VD",
                construction_year=1965,
                building_type="residential",
                floors_above=5,
                floors_below=1,
                surface_area_m2=2000.0,
                latitude=46.4312,
                longitude=6.9107,
                created_by=admin.id,
                owner_id=owner.id,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get("VD"),
            ),
            Building(
                id=SCENARIO_IDS["portfolio_cluster"],
                address="Lot Portefeuille A — Place du Marché 3, Nyon",
                postal_code="1260",
                city="Nyon",
                canton="VD",
                construction_year=1962,
                building_type="residential",
                floors_above=4,
                floors_below=1,
                surface_area_m2=1600.0,
                latitude=46.3833,
                longitude=6.2396,
                created_by=admin.id,
                owner_id=owner.id,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get("VD"),
            ),
            Building(
                id=SCENARIO_IDS["empty_dossier"],
                address="Nouveau Import — Route de Berne 50, Fribourg",
                postal_code="1700",
                city="Fribourg",
                canton="FR",
                construction_year=1975,
                building_type="mixed_use",
                floors_above=4,
                floors_below=1,
                surface_area_m2=1800.0,
                latitude=46.8065,
                longitude=7.1620,
                created_by=admin.id,
                owner_id=owner.id,
                status="active",
                jurisdiction_id=_CANTON_JURISDICTION.get("FR"),
            ),
        ]
        db.add_all(scenario_buildings)
        await db.flush()
        all_buildings = all_buildings + scenario_buildings

        # ── Scenario 1: Contradiction-heavy — conflicting diagnostics ─
        sc_diag_pos = Diagnostic(
            id=SCENARIO_IDS["contradiction_diag_pos"],
            building_id=SCENARIO_IDS["contradiction"],
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="Laboratoire EMPA Suisse",
            laboratory_report_number="EMPA-SC-001",
            date_inspection=date(2025, 6, 10),
            date_report=date(2025, 6, 25),
            summary="Amiante détecté dans flocage du sous-sol.",
            conclusion="positive",
            methodology="VDI 3866",
        )
        sc_diag_neg = Diagnostic(
            id=SCENARIO_IDS["contradiction_diag_neg"],
            building_id=SCENARIO_IDS["contradiction"],
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="Labo Romand SA",
            laboratory_report_number="LR-SC-002",
            date_inspection=date(2025, 8, 5),
            date_report=date(2025, 8, 20),
            summary="Aucune trace d'amiante dans les prélèvements du sous-sol.",
            conclusion="negative",
            methodology="VDI 3866",
        )
        db.add_all([sc_diag_pos, sc_diag_neg])
        await db.flush()

        # Contradictory samples: same material, opposite results
        sc_sample_pos = Sample(
            id=SCENARIO_IDS["contradiction_sample_pos"],
            diagnostic_id=SCENARIO_IDS["contradiction_diag_pos"],
            sample_number="SC-CONTR-001",
            location_floor="Sous-sol",
            location_room="Local technique",
            location_detail="Flocage sur conduite",
            material_category="flocage",
            material_description="Flocage fibreux gris sur conduite",
            material_state="friable",
            pollutant_type="asbestos",
            pollutant_subtype="chrysotile",
            concentration=12.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="major",
            action_required="containment_before_removal",
            waste_disposal_type="special",
        )
        sc_sample_neg = Sample(
            id=SCENARIO_IDS["contradiction_sample_neg"],
            diagnostic_id=SCENARIO_IDS["contradiction_diag_neg"],
            sample_number="SC-CONTR-002",
            location_floor="Sous-sol",
            location_room="Local technique",
            location_detail="Flocage sur conduite",
            material_category="flocage",
            material_description="Flocage fibreux gris sur conduite",
            material_state="friable",
            pollutant_type="asbestos",
            pollutant_subtype=None,
            concentration=0.0,
            unit="percent_weight",
            threshold_exceeded=False,
            risk_level="low",
            cfst_work_category=None,
            action_required="none",
            waste_disposal_type="controlled",
        )
        db.add_all([sc_sample_pos, sc_sample_neg])

        # ── Scenario 2: Nearly-ready — 1 pending artefact blocker ─────
        sc_diag_ready = Diagnostic(
            id=SCENARIO_IDS["nearly_ready_diag"],
            building_id=SCENARIO_IDS["nearly_ready"],
            diagnostic_type="full",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="Laboratoire EMPA Suisse",
            laboratory_report_number="EMPA-SC-003",
            date_inspection=date(2025, 9, 1),
            date_report=date(2025, 9, 15),
            summary="Diagnostic complet. Amiante dans sol vinyle, PCB sous seuil.",
            conclusion="positive",
            methodology="VDI 3866 / SIA 118/430",
            suva_notification_required=True,
            suva_notification_date=date(2025, 9, 20),
        )
        db.add(sc_diag_ready)
        await db.flush()

        sc_sample_r1 = Sample(
            id=SCENARIO_IDS["nearly_ready_sample1"],
            diagnostic_id=SCENARIO_IDS["nearly_ready_diag"],
            sample_number="SC-READY-001",
            location_floor="2ème étage",
            location_room="Salon",
            location_detail="Sol vinyle collé",
            material_category="floor_covering_vinyl",
            material_description="Dalles vinyle 30x30 cm",
            material_state="intact",
            pollutant_type="asbestos",
            pollutant_subtype="chrysotile",
            concentration=10.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
            action_required="containment_before_removal",
            waste_disposal_type="special",
        )
        sc_sample_r2 = Sample(
            id=SCENARIO_IDS["nearly_ready_sample2"],
            diagnostic_id=SCENARIO_IDS["nearly_ready_diag"],
            sample_number="SC-READY-002",
            location_floor="Façade",
            location_room="Façade sud",
            location_detail="Joint de façade",
            material_category="facade_joint_sealant",
            material_description="Mastic d'étanchéité gris",
            material_state="degraded",
            pollutant_type="pcb",
            pollutant_subtype=None,
            concentration=35.0,
            unit="mg_per_kg",
            threshold_exceeded=False,
            risk_level="low",
            cfst_work_category=None,
            action_required="monitoring",
            waste_disposal_type="controlled",
        )
        db.add_all([sc_sample_r1, sc_sample_r2])

        # Artefacts: one acknowledged, one pending (the blocker)
        sc_artefact_ok = ComplianceArtefact(
            id=SCENARIO_IDS["nearly_ready_artefact_ok"],
            building_id=SCENARIO_IDS["nearly_ready"],
            diagnostic_id=SCENARIO_IDS["nearly_ready_diag"],
            artefact_type="suva_notification",
            status="acknowledged",
            title="Notification SUVA — Travaux amiante",
            reference_number="SUVA-SC-001",
            authority_name="SUVA",
            authority_type="federal",
            legal_basis="OTConst Art. 82-86",
            submitted_at=datetime(2025, 10, 1, tzinfo=UTC),
            acknowledged_at=datetime(2025, 10, 5, tzinfo=UTC),
        )
        sc_artefact_pending = ComplianceArtefact(
            id=SCENARIO_IDS["nearly_ready_artefact_pending"],
            building_id=SCENARIO_IDS["nearly_ready"],
            diagnostic_id=SCENARIO_IDS["nearly_ready_diag"],
            artefact_type="cantonal_notification",
            status="submitted",
            title="Formulaire cantonal — Notification polluants (EN ATTENTE)",
            reference_number="VD-SC-002",
            authority_name="Canton de Vaud - DIREN",
            authority_type="cantonal",
            legal_basis="RLATC Art. 13",
            submitted_at=datetime(2025, 10, 10, tzinfo=UTC),
        )
        db.add_all([sc_artefact_ok, sc_artefact_pending])

        # ── Scenario 3: Post-works — completed diagnostic + intervention ─
        sc_diag_pw = Diagnostic(
            id=SCENARIO_IDS["post_works_diag"],
            building_id=SCENARIO_IDS["post_works"],
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="Laboratoire EMPA Suisse",
            laboratory_report_number="EMPA-SC-004",
            date_inspection=date(2025, 3, 10),
            date_report=date(2025, 3, 25),
            summary="Amiante confirmé dans flocage technique. Intervention planifiée.",
            conclusion="positive",
            methodology="VDI 3866",
            suva_notification_required=True,
            suva_notification_date=date(2025, 4, 1),
        )
        db.add(sc_diag_pw)
        await db.flush()

        sc_sample_pw = Sample(
            id=SCENARIO_IDS["post_works_sample"],
            diagnostic_id=SCENARIO_IDS["post_works_diag"],
            sample_number="SC-PW-001",
            location_floor="Sous-sol",
            location_room="Local technique",
            location_detail="Flocage sur structure",
            material_category="flocage",
            material_description="Flocage amianté sur poutre métallique",
            material_state="friable",
            pollutant_type="asbestos",
            pollutant_subtype="chrysotile",
            concentration=18.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="critical",
            cfst_work_category="major",
            action_required="containment_before_removal",
            waste_disposal_type="special",
        )
        db.add(sc_sample_pw)

        sc_intervention = Intervention(
            id=SCENARIO_IDS["post_works_intervention"],
            building_id=SCENARIO_IDS["post_works"],
            diagnostic_id=SCENARIO_IDS["post_works_diag"],
            intervention_type="asbestos_removal",
            title="Désamiantage complet — Flocage sous-sol",
            description="Retrait complet du flocage amianté. Mesures libératoires effectuées.",
            status="completed",
            date_start=date(2025, 6, 1),
            date_end=date(2025, 7, 15),
            contractor_name="Sanacore Bau GmbH",
            cost_chf=72000.0,
            zones_affected=["Sous-sol — Local technique"],
            created_by=admin.id,
        )
        db.add(sc_intervention)
        await db.flush()

        # Scenarios 4 & 5: portfolio_cluster and empty_dossier have no extra
        # data — they are just the building shells (portfolio_cluster gets
        # risk scores via the loop below; empty_dossier stays minimal).

        # ── Additional Diagnostics (varied states) ────────────────────

        # Diagnostic 3: Neuch\u00e2tel - draft (just started)
        diag3 = Diagnostic(
            id=uuid.uuid4(),
            building_id=extra_buildings[0].id,
            diagnostic_type="lead",
            diagnostic_context="UN",
            status="draft",
            diagnostician_id=diagnostician.id,
            laboratory=None,
            date_inspection=date(2026, 3, 1),
            summary="Diagnostic plomb - utilisation normale. En attente des pr\u00e9l\u00e8vements.",
        )
        db.add(diag3)
        await db.flush()

        # Diagnostic 4: Lugano - validated
        diag4 = Diagnostic(
            id=uuid.uuid4(),
            building_id=extra_buildings[1].id,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="validated",
            diagnostician_id=diagnostician.id,
            laboratory="LabAnalytica Ticino",
            laboratory_report_number="LAT-2025-0892",
            date_inspection=date(2025, 6, 15),
            date_report=date(2025, 7, 1),
            summary="Diagnostic amiante avant r\u00e9novation fa\u00e7ade. Amiante chrysotile confirm\u00e9 "
            "dans les joints ext\u00e9rieurs et les dalles de sol du sous-sol.",
            conclusion="positive",
            methodology="VDI 3866",
            suva_notification_required=True,
            suva_notification_date=date(2025, 7, 5),
        )
        db.add(diag4)
        await db.flush()

        # Samples for validated diagnostic
        for i, (floor, room, detail, mat, conc, exceeded) in enumerate(
            [
                ("Sous-sol", "Parking", "Dalles de sol vinyle", "Dalles vinyle-amiante 25x25", 12.0, True),
                ("RdC", "Hall d'entr\u00e9e", "Colle sous carrelage", "Colle noire bitumineuse", 3.5, True),
                ("Fa\u00e7ade", "Fa\u00e7ade ouest", "Joint entre panneaux", "Mastic gris souple", 0.0, False),
            ],
            1,
        ):
            s = Sample(
                id=uuid.uuid4(),
                diagnostic_id=diag4.id,
                sample_number=f"LUG-2025-{i:03d}",
                location_floor=floor,
                location_room=room,
                location_detail=detail,
                material_category="floor_covering"
                if "sol" in detail.lower()
                else "adhesive"
                if "colle" in detail.lower()
                else "sealant",
                material_description=mat,
                material_state="intact",
                pollutant_type="asbestos",
                pollutant_subtype="chrysotile",
                concentration=conc,
                unit="percent_weight",
                threshold_exceeded=exceeded,
                risk_level="high" if exceeded else "low",
                cfst_work_category="medium" if exceeded else None,
                action_required="removal_before_works" if exceeded else "monitoring",
                waste_disposal_type="special" if exceeded else None,
            )
            db.add(s)

        # Diagnostic 5: Basel - completed (awaiting validation)
        diag5 = Diagnostic(
            id=uuid.uuid4(),
            building_id=extra_buildings[3].id,
            diagnostic_type="pcb",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="SGS Schweiz AG",
            laboratory_report_number="SGS-2026-01234",
            date_inspection=date(2026, 1, 20),
            date_report=date(2026, 2, 5),
            summary="Diagnostic PCB avant travaux de r\u00e9novation int\u00e9rieure. "
            "PCB d\u00e9tect\u00e9 dans les joints de fen\u00eatres et les condensateurs d'\u00e9clairage.",
            conclusion="positive",
            methodology="EPA 8082A",
            suva_notification_required=False,
        )
        db.add(diag5)
        await db.flush()

        for i, (floor, room, detail, conc, exceeded) in enumerate(
            [
                ("3e \u00e9tage", "Bureau 3.1", "Joint de fen\u00eatre", 380.0, True),
                ("5e \u00e9tage", "Salle de conf\u00e9rence", "Joint de vitrage", 120.0, True),
                ("Sous-sol", "Local technique", "Condensateur fluorescent", 8500.0, True),
            ],
            1,
        ):
            s = Sample(
                id=uuid.uuid4(),
                diagnostic_id=diag5.id,
                sample_number=f"BS-2026-{i:03d}",
                location_floor=floor,
                location_room=room,
                location_detail=detail,
                material_category="sealant" if "joint" in detail.lower() else "electrical",
                material_description=f"Pr\u00e9l\u00e8vement {detail.lower()}",
                material_state="degraded" if conc > 200 else "intact",
                pollutant_type="pcb",
                pollutant_subtype="Aroclor 1254",
                concentration=conc,
                unit="mg_per_kg",
                threshold_exceeded=exceeded,
                risk_level="high" if conc > 200 else "medium",
                cfst_work_category="medium",
                action_required="decontamination",
                waste_disposal_type="special",
            )
            db.add(s)

        # Diagnostic 6: Luzern - draft with radon
        diag6 = Diagnostic(
            id=uuid.uuid4(),
            building_id=extra_buildings[4].id,
            diagnostic_type="radon",
            diagnostic_context="UN",
            status="draft",
            diagnostician_id=diagnostician.id,
            date_inspection=date(2026, 2, 15),
            summary="Mesure radon en cours dans les locaux du rez-de-chauss\u00e9e.",
        )
        db.add(diag6)

        # Diagnostic 7: Fribourg - completed HAP
        diag7 = Diagnostic(
            id=uuid.uuid4(),
            building_id=extra_buildings[5].id,
            diagnostic_type="hap",
            diagnostic_context="AvT",
            status="completed",
            diagnostician_id=diagnostician.id,
            laboratory="EMPA Suisse",
            laboratory_report_number="EMPA-2025-09321",
            date_inspection=date(2025, 11, 10),
            date_report=date(2025, 11, 28),
            summary="Diagnostic HAP avant r\u00e9novation. Goudr on d\u00e9tect\u00e9 sous le parquet du 1er \u00e9tage.",
            conclusion="positive",
            methodology="EPA 8270D",
            suva_notification_required=False,
        )
        db.add(diag7)
        await db.flush()

        s_hap = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag7.id,
            sample_number="FR-2025-001",
            location_floor="1er \u00e9tage",
            location_room="Grande salle",
            location_detail="Sous-couche noire sous parquet ch\u00eane",
            material_category="tar_products",
            material_description="Colle bitumineuse noire sous lattes de parquet",
            material_state="intact",
            pollutant_type="hap",
            pollutant_subtype="B[a]P (Benzo[a]pyr\u00e8ne)",
            concentration=850.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
            action_required="controlled_removal",
            waste_disposal_type="special",
            notes="Concentration 4x sup\u00e9rieure au seuil OLED (200 mg/kg).",
        )
        db.add(s_hap)

        # ── Documents ─────────────────────────────────────────────────
        doc_defs = [
            (
                buildings[0].id,
                "Rapport_diagnostic_complet_Lausanne.pdf",
                2450000,
                "application/pdf",
                "diagnostic_report",
                "Rapport de diagnostic complet AvT - Amiante et PCB",
            ),
            (
                buildings[0].id,
                "Notification_SUVA_20251005.pdf",
                180000,
                "application/pdf",
                "notification",
                "Copie de la notification SUVA",
            ),
            (
                buildings[1].id,
                "Photos_flocage_sous-sol.zip",
                15600000,
                "application/zip",
                "photo",
                "Photos du flocage suspect en sous-sol",
            ),
            (
                extra_buildings[1].id,
                "LAT-2025-0892_rapport.pdf",
                3200000,
                "application/pdf",
                "diagnostic_report",
                "Rapport laboratoire LabAnalytica Ticino",
            ),
            (
                extra_buildings[3].id,
                "SGS-2026-01234_PCB_results.pdf",
                1800000,
                "application/pdf",
                "lab_analysis",
                "R\u00e9sultats d'analyse PCB - SGS Schweiz",
            ),
            (
                extra_buildings[5].id,
                "Plan_etage_1_Fribourg.pdf",
                4500000,
                "application/pdf",
                "plan",
                "Plan du 1er \u00e9tage avec zones de pr\u00e9l\u00e8vement",
            ),
        ]

        for b_id, fname, fsize, mime, doc_type, desc in doc_defs:
            doc = Document(
                id=uuid.uuid4(),
                building_id=b_id,
                file_path=f"/documents/{fname}",
                file_name=fname,
                file_size_bytes=fsize,
                mime_type=mime,
                document_type=doc_type,
                description=desc,
                uploaded_by=admin.id,
            )
            db.add(doc)

        # ── Building Risk Scores ───────────────────────────────────────
        for b in all_buildings:
            scores = _risk_score(b.construction_year, b.canton, b.building_type)
            factors = {
                "construction_year": b.construction_year,
                "canton": b.canton,
                "building_type": b.building_type,
                "renovation_year": b.renovation_year,
            }
            risk = BuildingRiskScore(
                id=uuid.uuid4(),
                building_id=b.id,
                asbestos_probability=scores["asbestos_probability"],
                pcb_probability=scores["pcb_probability"],
                lead_probability=scores["lead_probability"],
                hap_probability=scores["hap_probability"],
                radon_probability=scores["radon_probability"],
                overall_risk_level=scores["overall_risk_level"],
                confidence=scores["confidence"],
                factors_json=factors,
                data_source="seed_model",
            )
            db.add(risk)

        # ── Events ─────────────────────────────────────────────────────
        for b in all_buildings:
            evt = Event(
                id=uuid.uuid4(),
                building_id=b.id,
                event_type="construction",
                date=date(b.construction_year, 1, 1),
                title=f"Construction du b\u00e2timent \u2014 {b.city}",
                description=f"B\u00e2timent construit en {b.construction_year} \u00e0 {b.address}, {b.postal_code} {b.city} ({b.canton}).",
                created_by=admin.id,
                metadata_json={"construction_year": b.construction_year, "building_type": b.building_type},
            )
            db.add(evt)

        # Diagnostic events
        diag_event = Event(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            event_type="diagnostic_completed",
            date=date(2025, 10, 2),
            title="Diagnostic complet termin\u00e9 \u2014 Amiante et PCB confirm\u00e9s",
            description="Diagnostic AvT complet r\u00e9alis\u00e9 par Jean-Pierre M\u00fcller (DiagSwiss SA). "
            "R\u00e9sultats: amiante chrysotile 15% dans sols vinyle, PCB 1250 mg/kg dans joints fa\u00e7ade. "
            "Notification SUVA effectu\u00e9e le 05.10.2025.",
            created_by=diagnostician.id,
            metadata_json={
                "diagnostic_id": str(diag1.id),
                "conclusion": "positive",
                "pollutants_found": ["asbestos", "pcb"],
                "suva_notified": True,
            },
        )
        db.add(diag_event)

        diag_event2 = Event(
            id=uuid.uuid4(),
            building_id=extra_buildings[1].id,
            event_type="diagnostic_validated",
            date=date(2025, 7, 10),
            title="Diagnostic amiante valid\u00e9 \u2014 Lugano",
            description="Diagnostic AvT valid\u00e9 par l'autorit\u00e9 cantonale du Tessin.",
            created_by=admin.id,
            metadata_json={"diagnostic_id": str(diag4.id), "validated_by": "Autorit\u00e9 cantonale TI"},
        )
        db.add(diag_event2)

        # ── Rich Timeline Events (for first 3 buildings) ─────────────

        # Building 1 (Lausanne) — 8 additional events
        rich_events = [
            # Renovation event
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="renovation",
                date=date(1988, 6, 1),
                title="Renovation partielle — Lausanne",
                description="Renovation de la toiture et isolation des combles. "
                "Les dalles vinyle et joints de facade d'origine n'ont pas ete touches.",
                created_by=admin.id,
                metadata_json={"renovation_year": 1988, "scope": "roof_insulation"},
            ),
            # Document upload events
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="document_uploaded",
                date=date(2025, 10, 3),
                title="Rapport de diagnostic complet televerse",
                description="Rapport_diagnostic_complet_Lausanne.pdf televerse par l'administrateur.",
                created_by=admin.id,
                metadata_json={
                    "document_type": "diagnostic_report",
                    "file_name": "Rapport_diagnostic_complet_Lausanne.pdf",
                },
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="document_uploaded",
                date=date(2025, 10, 6),
                title="Notification SUVA televersee",
                description="Copie de la notification SUVA envoyee le 05.10.2025.",
                created_by=admin.id,
                metadata_json={"document_type": "notification", "file_name": "Notification_SUVA_20251005.pdf"},
            ),
            # Intervention events
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="intervention_completed",
                date=date(2019, 10, 15),
                title="Desamiantage partiel faux plafonds termine",
                description="Retrait des plaques fibrociment amiantees dans le hall d'entree "
                "par Sanacore Bau GmbH. Cout: CHF 35'000.",
                created_by=admin.id,
                metadata_json={"intervention_type": "asbestos_removal", "cost_chf": 35000},
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="intervention_completed",
                date=date(2010, 8, 30),
                title="Remplacement fenetres 1er etage",
                description="Toutes les fenetres du 1er etage remplacees par du PVC double vitrage.",
                created_by=admin.id,
                metadata_json={"intervention_type": "renovation", "cost_chf": 28000},
            ),
            # Sample result events
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="sample_result",
                date=date(2025, 9, 25),
                title="Resultat analyse — Amiante chrysotile 15%",
                description="Echantillon LS-2025-001: dalles vinyle-amiante, concentration 15% en poids. "
                "Seuil depasse (1%). Categorie CFST: medium.",
                created_by=diagnostician.id,
                metadata_json={
                    "sample_number": "LS-2025-001",
                    "pollutant": "asbestos",
                    "concentration": 15.0,
                    "threshold_exceeded": True,
                },
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="sample_result",
                date=date(2025, 9, 26),
                title="Resultat analyse — PCB 1250 mg/kg",
                description="Echantillon LS-2025-002: joint facade sud, PCB Aroclor 1260, 1250 mg/kg. "
                "25x superieur au seuil ORRChim (50 mg/kg).",
                created_by=diagnostician.id,
                metadata_json={
                    "sample_number": "LS-2025-002",
                    "pollutant": "pcb",
                    "concentration": 1250.0,
                    "threshold_exceeded": True,
                },
            ),
            # SUVA notification event
            Event(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                event_type="notification_sent",
                date=date(2025, 10, 5),
                title="Notification SUVA envoyee",
                description="Notification officielle SUVA suite au diagnostic positif amiante.",
                created_by=admin.id,
                metadata_json={"notification_type": "suva", "diagnostic_id": str(diag1.id)},
            ),
            # Building 2 (Geneve) — 5 events
            Event(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                event_type="diagnostic_started",
                date=date(2026, 2, 20),
                title="Debut diagnostic amiante — Geneve",
                description="Inspection sur site pour diagnostic amiante avant transformation du RdC.",
                created_by=diagnostician.id,
                metadata_json={"diagnostic_id": str(diag2.id), "diagnostic_type": "asbestos"},
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                event_type="document_uploaded",
                date=date(2026, 2, 21),
                title="Photos flocage sous-sol televersees",
                description="Archive photos du flocage suspect identifie en sous-sol.",
                created_by=diagnostician.id,
                metadata_json={"document_type": "photo", "file_name": "Photos_flocage_sous-sol.zip"},
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                event_type="intervention_started",
                date=date(2026, 2, 1),
                title="Debut remplacement conduites chauffage",
                description="Remplacement des conduites avec calorifuge amiante par Sanacore Bau GmbH.",
                created_by=admin.id,
                metadata_json={"intervention_type": "repair", "contractor": "Sanacore Bau GmbH"},
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                event_type="intervention_completed",
                date=date(2023, 3, 10),
                title="Maintenance ascenseur terminee",
                description="Maintenance annuelle de l'ascenseur et mise aux normes.",
                created_by=admin.id,
                metadata_json={"intervention_type": "maintenance", "cost_chf": 3500},
            ),
            # Building 3 (Biel) — 4 events
            Event(
                id=uuid.uuid4(),
                building_id=buildings[2].id,
                event_type="intervention_completed",
                date=date(2015, 9, 30),
                title="Extension garage terminee",
                description="Agrandissement du garage avec nouvelle dalle beton. Cout: CHF 80'000.",
                created_by=admin.id,
                metadata_json={"intervention_type": "installation", "cost_chf": 80000},
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[2].id,
                event_type="intervention_completed",
                date=date(2020, 6, 15),
                title="Peinture facade terminee",
                description="Nettoyage et peinture complete des facades.",
                created_by=admin.id,
                metadata_json={"intervention_type": "maintenance", "cost_chf": 12000},
            ),
            Event(
                id=uuid.uuid4(),
                building_id=buildings[2].id,
                event_type="inspection_planned",
                date=date(2025, 10, 1),
                title="Inspection radon planifiee",
                description="Pose de dosimetres radon prevue dans les locaux du RdC. "
                "Zone a risque radon eleve (canton BE).",
                created_by=admin.id,
                metadata_json={"inspection_type": "radon", "canton": "BE"},
            ),
            # Building 4 (Sion/VS) — renovation event
            Event(
                id=uuid.uuid4(),
                building_id=buildings[3].id,
                event_type="renovation",
                date=date(1975, 1, 1),
                title="Renovation — Sion",
                description="Renovation de l'ecole en 1975. Travaux d'isolation et menuiserie.",
                created_by=admin.id,
                metadata_json={"renovation_year": 1975},
            ),
        ]
        db.add_all(rich_events)

        # ── Action Items ──────────────────────────────────────────────
        action_defs = [
            ActionItem(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                diagnostic_id=diag1.id,
                source_type="diagnostic",
                action_type="schedule_removal",
                title="Planifier le retrait des dalles vinyle amiantées",
                description="Amiante chrysotile 15% confirmé dans les dalles de sol. "
                "Retrait par entreprise agréée SUVA obligatoire avant travaux.",
                priority="high",
                status="open",
                due_date=date(2026, 6, 30),
                assigned_to=diagnostician.id,
                created_by=admin.id,
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                diagnostic_id=diag1.id,
                source_type="diagnostic",
                action_type="decontamination",
                title="Décontamination PCB joints de façade",
                description="PCB 1250 mg/kg dans joints façade sud. "
                "Décontamination complète nécessaire (seuil ORRChim: 50 mg/kg).",
                priority="high",
                status="in_progress",
                due_date=date(2026, 5, 15),
                assigned_to=diagnostician.id,
                created_by=admin.id,
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                diagnostic_id=diag2.id,
                source_type="risk",
                action_type="create_diagnostic",
                title="Finaliser le diagnostic amiante en cours",
                description="Flocage suspect identifié en sous-sol. Résultats de laboratoire attendus.",
                priority="critical",
                status="open",
                due_date=date(2026, 4, 1),
                assigned_to=diagnostician.id,
                created_by=admin.id,
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=extra_buildings[3].id,
                diagnostic_id=diag5.id,
                source_type="compliance",
                action_type="request_validation",
                title="Demander la validation du diagnostic PCB",
                description="Diagnostic PCB complété le 05.02.2026. En attente de validation par l'autorité cantonale.",
                priority="medium",
                status="open",
                due_date=date(2026, 4, 15),
                assigned_to=admin.id,
                created_by=diagnostician.id,
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=extra_buildings[4].id,
                source_type="risk",
                action_type="create_diagnostic",
                title="Lancer mesure radon complète",
                description="Bâtiment 1958 à Luzern — zone à risque radon élevé. "
                "Dosimètres à poser pour mesure sur 3 mois.",
                priority="medium",
                status="open",
                due_date=date(2026, 5, 1),
                assigned_to=diagnostician.id,
                created_by=admin.id,
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=extra_buildings[5].id,
                diagnostic_id=diag7.id,
                source_type="diagnostic",
                action_type="controlled_removal",
                title="Retrait contrôlé HAP sous parquet",
                description="HAP 850 mg/kg détecté sous parquet 1er étage. "
                "Retrait contrôlé avec protection respiratoire obligatoire.",
                priority="high",
                status="blocked",
                due_date=date(2026, 7, 1),
                assigned_to=diagnostician.id,
                created_by=admin.id,
                metadata_json={"blocking_reason": "En attente du devis de l'entreprise spécialisée"},
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=extra_buildings[1].id,
                diagnostic_id=diag4.id,
                source_type="system",
                action_type="archive_diagnostic",
                title="Archiver le diagnostic validé",
                description="Diagnostic amiante Lugano validé et terminé. Prêt pour archivage.",
                priority="low",
                status="done",
                due_date=None,
                assigned_to=admin.id,
                created_by=admin.id,
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                source_type="manual",
                action_type="upload_document",
                title="Télécharger le plan d'assainissement",
                description="Joindre le plan d'assainissement de l'entreprise mandatée.",
                priority="medium",
                status="open",
                due_date=date(2026, 4, 30),
                assigned_to=owner.id,
                created_by=admin.id,
            ),
        ]
        db.add_all(action_defs)

        # ── Invitations ──────────────────────────────────────────────
        now = datetime.now(UTC)
        invitations = [
            Invitation(
                id=uuid.uuid4(),
                email="nouveau.diag@labtest.ch",
                role="diagnostician",
                organization_id=org1.id,
                status="pending",
                token=secrets.token_urlsafe(32),
                invited_by=admin.id,
                expires_at=now + timedelta(days=7),
            ),
            Invitation(
                id=uuid.uuid4(),
                email="immobilier@example.ch",
                role="owner",
                organization_id=org2.id,
                status="pending",
                token=secrets.token_urlsafe(32),
                invited_by=admin.id,
                expires_at=now + timedelta(days=5),
            ),
            Invitation(
                id=uuid.uuid4(),
                email="marco.brunetti@archibau.ch",
                role="architect",
                organization_id=org3.id,
                status="accepted",
                token=secrets.token_urlsafe(32),
                invited_by=admin.id,
                expires_at=now - timedelta(days=10),
                accepted_at=now - timedelta(days=12),
            ),
            Invitation(
                id=uuid.uuid4(),
                email="expired@example.ch",
                role="diagnostician",
                status="expired",
                token=secrets.token_urlsafe(32),
                invited_by=admin.id,
                expires_at=now - timedelta(days=30),
            ),
            Invitation(
                id=uuid.uuid4(),
                email="revoque@example.ch",
                role="contractor",
                organization_id=org5.id,
                status="revoked",
                token=secrets.token_urlsafe(32),
                invited_by=admin.id,
                expires_at=now + timedelta(days=3),
            ),
        ]
        db.add_all(invitations)

        # ── Assignments ──────────────────────────────────────────────
        assignments = [
            Assignment(
                id=uuid.uuid4(),
                target_type="building",
                target_id=buildings[0].id,
                user_id=diagnostician.id,
                role="diagnostician",
                created_by=admin.id,
            ),
            Assignment(
                id=uuid.uuid4(),
                target_type="building",
                target_id=buildings[0].id,
                user_id=owner.id,
                role="owner_contact",
                created_by=admin.id,
            ),
            Assignment(
                id=uuid.uuid4(),
                target_type="building",
                target_id=buildings[1].id,
                user_id=diagnostician.id,
                role="diagnostician",
                created_by=admin.id,
            ),
            Assignment(
                id=uuid.uuid4(),
                target_type="building",
                target_id=extra_buildings[3].id,
                user_id=contractor.id,
                role="contractor_contact",
                created_by=admin.id,
            ),
            Assignment(
                id=uuid.uuid4(),
                target_type="diagnostic",
                target_id=diag1.id,
                user_id=authority.id,
                role="reviewer",
                created_by=admin.id,
            ),
            Assignment(
                id=uuid.uuid4(),
                target_type="building",
                target_id=extra_buildings[5].id,
                user_id=architect.id,
                role="responsible",
                created_by=admin.id,
            ),
        ]
        db.add_all(assignments)

        # ── Notifications ────────────────────────────────────────────
        notifications = [
            Notification(
                id=uuid.uuid4(),
                user_id=admin.id,
                type="action",
                title="Nouvelle action critique : flocage amiante Genève",
                body="Un flocage suspect a été identifié au sous-sol. Action urgente requise.",
                link=f"/buildings/{buildings[1].id}",
                status="unread",
            ),
            Notification(
                id=uuid.uuid4(),
                user_id=admin.id,
                type="system",
                title="Bienvenue sur SwissBuildingOS",
                body="Votre plateforme de gestion des polluants est prête.",
                status="read",
                read_at=now - timedelta(days=5),
            ),
            Notification(
                id=uuid.uuid4(),
                user_id=diagnostician.id,
                type="action",
                title="Diagnostic PCB Basel en attente de validation",
                body="Le diagnostic SGS-2026-01234 est terminé et attend votre révision.",
                link=f"/buildings/{extra_buildings[3].id}",
                status="unread",
            ),
            Notification(
                id=uuid.uuid4(),
                user_id=owner.id,
                type="invitation",
                title="Vous avez été assignée au bâtiment Lausanne",
                body="L'administrateur vous a assignée comme contact propriétaire.",
                link=f"/buildings/{buildings[0].id}",
                status="unread",
            ),
            Notification(
                id=uuid.uuid4(),
                user_id=admin.id,
                type="export",
                title="Export dossier bâtiment terminé",
                body="Le dossier bâtiment pour Lausanne est prêt au téléchargement.",
                link="/exports",
                status="unread",
            ),
            Notification(
                id=uuid.uuid4(),
                user_id=diagnostician.id,
                type="system",
                title="Mise à jour du système",
                body="Version 2.0 déployée avec gestion des organisations et invitations.",
                status="read",
                read_at=now - timedelta(days=2),
            ),
        ]
        db.add_all(notifications)

        # ── Notification Preferences ─────────────────────────────────
        for u in [admin, diagnostician, owner, architect, authority, contractor]:
            pref = NotificationPreference(
                id=uuid.uuid4(),
                user_id=u.id,
                in_app_actions=True,
                in_app_invitations=True,
                in_app_exports=True,
                digest_enabled=u.role == "admin",
            )
            db.add(pref)

        # ── Export Jobs ──────────────────────────────────────────────
        export_jobs = [
            ExportJob(
                id=uuid.uuid4(),
                type="building_dossier",
                building_id=buildings[0].id,
                status="completed",
                requested_by=admin.id,
                file_path="/exports/dossier_lausanne_20260307.pdf",
                completed_at=now - timedelta(hours=2),
            ),
            ExportJob(
                id=uuid.uuid4(),
                type="audit_pack",
                building_id=extra_buildings[1].id,
                status="completed",
                requested_by=admin.id,
                file_path="/exports/audit_lugano_20260305.pdf",
                completed_at=now - timedelta(days=3),
            ),
            ExportJob(
                id=uuid.uuid4(),
                type="handoff_pack",
                building_id=extra_buildings[3].id,
                status="queued",
                requested_by=diagnostician.id,
            ),
            ExportJob(
                id=uuid.uuid4(),
                type="building_dossier",
                organization_id=org2.id,
                status="failed",
                requested_by=owner.id,
                error_message="Aucun bâtiment trouvé pour cette organisation.",
            ),
        ]
        db.add_all(export_jobs)

        # ── Zones ──────────────────────────────────────────────────────
        # Building 1 (buildings[0] — Lausanne)
        z001 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="basement",
            name="Sous-sol",
            description="Cave et locaux techniques en sous-sol",
            floor_number=-1,
            surface_area_m2=350.0,
            created_by=admin.id,
        )
        z002 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="floor",
            name="Rez-de-chaussée",
            description="Entrée principale et commerces",
            floor_number=0,
            surface_area_m2=400.0,
            created_by=admin.id,
        )
        z003 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="floor",
            name="1er étage",
            description="Appartements résidentiels",
            floor_number=1,
            surface_area_m2=400.0,
            created_by=admin.id,
        )
        z004 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="floor",
            name="2ème étage",
            description="Appartements résidentiels",
            floor_number=2,
            surface_area_m2=400.0,
            created_by=admin.id,
        )
        z005 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="roof",
            name="Combles",
            description="Combles aménageables avec charpente bois",
            floor_number=6,
            surface_area_m2=200.0,
            created_by=admin.id,
        )
        z006 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="facade",
            name="Façade nord",
            description="Façade principale donnant sur la rue",
            created_by=admin.id,
        )
        z007 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            zone_type="staircase",
            name="Cage d'escalier",
            description="Cage d'escalier centrale avec ascenseur",
            created_by=admin.id,
        )
        db.add_all([z001, z002, z003, z004, z005, z006, z007])
        await db.flush()

        # Child zones (need parent IDs)
        z008 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            parent_zone_id=z001.id,
            zone_type="technical_room",
            name="Local technique",
            description="Chaufferie et distribution eau/électricité",
            floor_number=-1,
            surface_area_m2=45.0,
            created_by=admin.id,
        )
        z009 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            parent_zone_id=z001.id,
            zone_type="room",
            name="Buanderie",
            description="Buanderie commune pour les résidents",
            floor_number=-1,
            surface_area_m2=30.0,
            created_by=admin.id,
        )
        z010 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            parent_zone_id=z002.id,
            zone_type="room",
            name="Hall d'entrée",
            description="Hall d'entrée avec boîtes aux lettres",
            floor_number=0,
            surface_area_m2=25.0,
            created_by=admin.id,
        )
        db.add_all([z008, z009, z010])
        await db.flush()

        # Building 2 (buildings[1] — Genève)
        z011 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            zone_type="basement",
            name="Sous-sol",
            description="Sous-sol avec locaux techniques",
            floor_number=-1,
            surface_area_m2=500.0,
            created_by=admin.id,
        )
        z012 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            zone_type="floor",
            name="Rez-de-chaussée",
            description="Rez-de-chaussée commercial",
            floor_number=0,
            surface_area_m2=400.0,
            created_by=admin.id,
        )
        z013 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            zone_type="floor",
            name="1er étage",
            description="Bureaux",
            floor_number=1,
            surface_area_m2=400.0,
            created_by=admin.id,
        )
        z014 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            zone_type="parking",
            name="Parking souterrain",
            description="Parking souterrain niveau -2",
            floor_number=-2,
            surface_area_m2=800.0,
            created_by=admin.id,
        )
        db.add_all([z011, z012, z013, z014])
        await db.flush()

        # Building 3 (buildings[2] — Biel/Bienne)
        z015 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            zone_type="floor",
            name="Rez-de-chaussée",
            description="Atelier et zone de production",
            floor_number=0,
            surface_area_m2=2500.0,
            created_by=admin.id,
        )
        z016 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            zone_type="floor",
            name="1er étage",
            description="Bureaux administratifs",
            floor_number=1,
            surface_area_m2=1200.0,
            created_by=admin.id,
        )
        z017 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            zone_type="parking",
            name="Garage",
            description="Garage pour véhicules de service",
            floor_number=0,
            surface_area_m2=300.0,
            created_by=admin.id,
        )
        z018 = Zone(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            zone_type="other",
            name="Jardin technique",
            description="Zone extérieure avec installations techniques",
            created_by=admin.id,
        )
        db.add_all([z015, z016, z017, z018])
        await db.flush()

        all_zones = [
            z001,
            z002,
            z003,
            z004,
            z005,
            z006,
            z007,
            z008,
            z009,
            z010,
            z011,
            z012,
            z013,
            z014,
            z015,
            z016,
            z017,
            z018,
        ]

        # ── Building Elements ──────────────────────────────────────────
        # Building 1 elements
        e001 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z002.id,
            element_type="wall",
            name="Mur porteur nord",
            description="Mur porteur en maçonnerie de briques, épaisseur 40 cm",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e002 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z010.id,
            element_type="ceiling",
            name="Faux plafond hall",
            description="Faux plafond en plaques fibrociment suspendues",
            condition="poor",
            installation_year=1975,
            created_by=admin.id,
        )
        e003 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z010.id,
            element_type="floor",
            name="Sol vinyle hall",
            description="Revêtement de sol en dalles vinyle collées 30x30 cm",
            condition="poor",
            installation_year=1968,
            created_by=admin.id,
        )
        e004 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z001.id,
            element_type="pipe",
            name="Conduite eau chaude",
            description="Conduite d'eau chaude avec calorifuge d'origine",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e005 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z001.id,
            element_type="insulation",
            name="Isolation cave",
            description="Isolation thermique du plafond de cave, panneaux fibreux",
            condition="critical",
            installation_year=1960,
            created_by=admin.id,
        )
        e006 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z006.id,
            element_type="coating",
            name="Revêtement façade",
            description="Crépi de façade d'origine avec couches de peinture successives",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e007 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z003.id,
            element_type="window",
            name="Fenêtres 1er étage",
            description="Fenêtres PVC double vitrage, remplacées en 2010",
            condition="good",
            installation_year=2010,
            created_by=admin.id,
        )
        e008 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z004.id,
            element_type="door",
            name="Porte palière 2ème",
            description="Porte palière en bois massif avec peinture multicouche",
            condition="fair",
            installation_year=1975,
            created_by=admin.id,
        )
        e009 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z007.id,
            element_type="duct",
            name="Gaine technique",
            description="Gaine technique verticale pour câblage et ventilation",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e010 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z001.id,
            element_type="structural",
            name="Dalle béton sous-sol",
            description="Dalle en béton armé, portée 6 m",
            condition="good",
            installation_year=1962,
            created_by=admin.id,
        )
        e011 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z007.id,
            element_type="wall",
            name="Mur cage escalier",
            description="Mur en béton de la cage d'escalier avec peinture",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e012 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z001.id,
            element_type="ceiling",
            name="Plafond sous-sol",
            description="Plafond béton brut avec calorifuges sur tuyaux",
            condition="poor",
            installation_year=1962,
            created_by=admin.id,
        )

        # Building 2 elements
        e013 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z012.id,
            element_type="wall",
            name="Mur extérieur",
            description="Mur extérieur en béton avec parement pierre",
            condition="fair",
            installation_year=1955,
            created_by=admin.id,
        )
        e014 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z014.id,
            element_type="floor",
            name="Sol parking",
            description="Sol béton lissé du parking souterrain",
            condition="fair",
            installation_year=1955,
            created_by=admin.id,
        )
        e015 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z013.id,
            element_type="insulation",
            name="Isolation toiture",
            description="Isolation thermique de la toiture en panneaux de laine",
            condition="poor",
            installation_year=1955,
            created_by=admin.id,
        )
        e016 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z011.id,
            element_type="pipe",
            name="Conduite chauffage",
            description="Conduite de chauffage avec calorifuge dégradé",
            condition="critical",
            installation_year=1955,
            created_by=admin.id,
        )
        e017 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z012.id,
            element_type="coating",
            name="Revêtement mural",
            description="Revêtement mural intérieur peint sur enduit",
            condition="fair",
            installation_year=1985,
            created_by=admin.id,
        )

        # Building 3 elements
        e018 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z015.id,
            element_type="wall",
            name="Mur porteur",
            description="Mur porteur en béton armé de l'atelier",
            condition="good",
            installation_year=1972,
            created_by=admin.id,
        )
        e019 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z016.id,
            element_type="structural",
            name="Toiture",
            description="Structure de toiture en charpente métallique avec bac acier",
            condition="fair",
            installation_year=1972,
            created_by=admin.id,
        )
        e020 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z017.id,
            element_type="floor",
            name="Sol garage",
            description="Sol béton industriel du garage",
            condition="fair",
            installation_year=1972,
            created_by=admin.id,
        )

        # Additional elements to reach ~35 total
        e021 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z005.id,
            element_type="structural",
            name="Charpente bois combles",
            description="Charpente traditionnelle en bois de sapin",
            condition="good",
            installation_year=1962,
            created_by=admin.id,
        )
        e022 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z009.id,
            element_type="floor",
            name="Sol buanderie",
            description="Carrelage grès cérame sur chape ciment",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e023 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z008.id,
            element_type="pipe",
            name="Collecteur principal",
            description="Collecteur eau usée en fonte avec joints amiantés",
            condition="poor",
            installation_year=1962,
            created_by=admin.id,
        )
        e024 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z003.id,
            element_type="ceiling",
            name="Plafond 1er étage",
            description="Plafond plâtre sur lattis bois",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e025 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z004.id,
            element_type="floor",
            name="Parquet 2ème étage",
            description="Parquet chêne massif collé sur bitume",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e026 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z002.id,
            element_type="window",
            name="Vitrine commerciale RdC",
            description="Grande vitrine en aluminium et verre double",
            condition="good",
            installation_year=1988,
            created_by=admin.id,
        )
        e027 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z006.id,
            element_type="structural",
            name="Balcons façade nord",
            description="Dalles de balcon en béton armé avec étanchéité bitumineuse",
            condition="fair",
            installation_year=1962,
            created_by=admin.id,
        )
        e028 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z011.id,
            element_type="structural",
            name="Dalles sous-sol Genève",
            description="Dalles béton armé du sous-sol",
            condition="good",
            installation_year=1955,
            created_by=admin.id,
        )
        e029 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z013.id,
            element_type="door",
            name="Portes coupe-feu",
            description="Portes coupe-feu EI60 dans le couloir du 1er étage",
            condition="good",
            installation_year=1985,
            created_by=admin.id,
        )
        e030 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z015.id,
            element_type="pipe",
            name="Réseau air comprimé",
            description="Réseau de distribution d'air comprimé avec joints et raccords",
            condition="fair",
            installation_year=1972,
            created_by=admin.id,
        )
        e031 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z016.id,
            element_type="ceiling",
            name="Faux plafond bureaux",
            description="Faux plafond dalles minérales 60x60 cm",
            condition="fair",
            installation_year=1985,
            created_by=admin.id,
        )
        e032 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z018.id,
            element_type="structural",
            name="Cuve enterrée",
            description="Cuve en béton pour stockage eau de pluie",
            condition="fair",
            installation_year=1972,
            created_by=admin.id,
        )
        e033 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z015.id,
            element_type="coating",
            name="Peinture sol atelier",
            description="Peinture époxy de sol industriel",
            condition="poor",
            installation_year=1980,
            created_by=admin.id,
        )
        e034 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z005.id,
            element_type="insulation",
            name="Isolation combles",
            description="Isolation thermique en laine minérale soufflée",
            condition="fair",
            installation_year=1988,
            created_by=admin.id,
        )
        e035 = BuildingElement(
            id=uuid.uuid4(),
            zone_id=z012.id,
            element_type="window",
            name="Fenêtres RdC Genève",
            description="Fenêtres bois d'origine avec simple vitrage",
            condition="poor",
            installation_year=1955,
            created_by=admin.id,
        )

        all_elements = [
            e001,
            e002,
            e003,
            e004,
            e005,
            e006,
            e007,
            e008,
            e009,
            e010,
            e011,
            e012,
            e013,
            e014,
            e015,
            e016,
            e017,
            e018,
            e019,
            e020,
            e021,
            e022,
            e023,
            e024,
            e025,
            e026,
            e027,
            e028,
            e029,
            e030,
            e031,
            e032,
            e033,
            e034,
            e035,
        ]
        db.add_all(all_elements)
        await db.flush()

        # ── Materials ──────────────────────────────────────────────────
        mat_list = [
            # e001 — Mur porteur nord: clean materials
            Material(
                id=uuid.uuid4(),
                element_id=e001.id,
                material_type="brick",
                name="Maçonnerie de briques",
                installation_year=1962,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e001.id,
                material_type="plaster",
                name="Enduit ciment",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e002 — Faux plafond hall: CONFIRMED asbestos
            Material(
                id=uuid.uuid4(),
                element_id=e002.id,
                material_type="fiber_cement",
                name="Plaques fibrociment Eternit",
                description="Plaques de faux plafond contenant de l'amiante chrysotile",
                installation_year=1975,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=True,
                sample_id=sample1_1.id,
                source="laboratory_analysis",
                notes="Amiante chrysotile 15% confirmé par EMPA",
                created_by=diagnostician.id,
            ),
            # e003 — Sol vinyle hall: CONFIRMED asbestos
            Material(
                id=uuid.uuid4(),
                element_id=e003.id,
                material_type="vinyl",
                name="Dalles vinyle-amiante",
                description="Dalles vinyle 30x30 cm contenant chrysotile",
                installation_year=1968,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=True,
                sample_id=sample1_1.id,
                source="laboratory_analysis",
                notes="Même type que l'échantillon LS-2025-001",
                created_by=diagnostician.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e003.id,
                material_type="adhesive",
                name="Colle noire bitumineuse",
                description="Colle de pose sous les dalles vinyle",
                installation_year=1968,
                contains_pollutant=True,
                pollutant_type="hap",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Colle noire suspecte de contenir des HAP",
                created_by=diagnostician.id,
            ),
            # e004 — Conduite eau chaude: SUSPECTED asbestos
            Material(
                id=uuid.uuid4(),
                element_id=e004.id,
                material_type="insulation_material",
                name="Calorifuge amiante",
                description="Calorifuge fibreux sur conduite, suspect d'amiante",
                installation_year=1962,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Aspect fibreux typique des calorifuges amiantés pré-1990",
                created_by=diagnostician.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e004.id,
                material_type="metal",
                name="Tube acier galvanisé",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e005 — Isolation cave: SUSPECTED asbestos (critical)
            Material(
                id=uuid.uuid4(),
                element_id=e005.id,
                material_type="fiber_cement",
                name="Panneaux isolants fibreux",
                description="Panneaux d'isolation en fibrociment dégradés",
                installation_year=1960,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Panneaux très dégradés, fibres visibles",
                created_by=diagnostician.id,
            ),
            # e006 — Revêtement façade: paint with lead
            Material(
                id=uuid.uuid4(),
                element_id=e006.id,
                material_type="paint",
                name="Peinture façade multicouche",
                description="Couches successives de peinture dont certaines au plomb",
                installation_year=1962,
                contains_pollutant=True,
                pollutant_type="lead",
                pollutant_confirmed=True,
                sample_id=sample1_3.id,
                source="laboratory_analysis",
                notes="Plomb 4200 mg/kg — sous le seuil de 5000 mg/kg",
                created_by=diagnostician.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e006.id,
                material_type="plaster",
                name="Crépi ciment",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e007 — Fenêtres 1er: clean (recent)
            Material(
                id=uuid.uuid4(),
                element_id=e007.id,
                material_type="pvc",
                name="Profilés PVC",
                installation_year=2010,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e007.id,
                material_type="glass",
                name="Double vitrage isolant",
                installation_year=2010,
                created_by=admin.id,
            ),
            # e008 — Porte palière: paint with lead (suspected)
            Material(
                id=uuid.uuid4(),
                element_id=e008.id,
                material_type="wood",
                name="Bois massif chêne",
                installation_year=1975,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e008.id,
                material_type="paint",
                name="Peinture porte au plomb",
                description="Peinture blanche multicouche suspecte de plomb",
                installation_year=1975,
                contains_pollutant=True,
                pollutant_type="lead",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Peinture ancienne multicouche — test plomb recommandé",
                created_by=diagnostician.id,
            ),
            # e009 — Gaine technique: clean
            Material(
                id=uuid.uuid4(),
                element_id=e009.id,
                material_type="concrete",
                name="Béton armé gaine",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e010 — Dalle béton sous-sol: clean
            Material(
                id=uuid.uuid4(),
                element_id=e010.id,
                material_type="concrete",
                name="Béton armé structurel",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e011 — Mur cage escalier: paint with lead
            Material(
                id=uuid.uuid4(),
                element_id=e011.id,
                material_type="paint",
                name="Peinture cage d'escalier",
                description="Peinture d'origine sur béton",
                installation_year=1962,
                contains_pollutant=True,
                pollutant_type="lead",
                pollutant_confirmed=False,
                source="visual_inspection",
                created_by=diagnostician.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e011.id,
                material_type="concrete",
                name="Béton mur escalier",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e012 — Plafond sous-sol: clean concrete
            Material(
                id=uuid.uuid4(),
                element_id=e012.id,
                material_type="concrete",
                name="Béton brut plafond",
                installation_year=1962,
                created_by=admin.id,
            ),
            # e013 — Mur extérieur Genève: PCB in joints
            Material(
                id=uuid.uuid4(),
                element_id=e013.id,
                material_type="concrete",
                name="Béton parement",
                installation_year=1955,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e013.id,
                material_type="sealant",
                name="Joint de dilatation PCB",
                description="Mastic d'étanchéité entre panneaux béton préfabriqués",
                installation_year=1955,
                contains_pollutant=True,
                pollutant_type="pcb",
                pollutant_confirmed=True,
                sample_id=sample1_2.id,
                source="laboratory_analysis",
                notes="PCB Aroclor 1260 — 1250 mg/kg confirmé",
                created_by=diagnostician.id,
            ),
            # e015 — Isolation toiture Genève: suspected asbestos
            Material(
                id=uuid.uuid4(),
                element_id=e015.id,
                material_type="mineral_wool",
                name="Laine minérale toiture",
                description="Panneaux de laine minérale anciens",
                installation_year=1955,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Isolant d'origine 1955, suspect d'amiante",
                created_by=diagnostician.id,
            ),
            # e016 — Conduite chauffage Genève: confirmed asbestos
            Material(
                id=uuid.uuid4(),
                element_id=e016.id,
                material_type="insulation_material",
                name="Flocage amiante chaufferie",
                description="Flocage fibreux gris-blanc sur conduites",
                installation_year=1955,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=True,
                sample_id=sample2_1.id,
                source="laboratory_analysis",
                notes="Flocage friable — risque critique d'exposition",
                created_by=diagnostician.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e016.id,
                material_type="metal",
                name="Conduite acier chauffage",
                installation_year=1955,
                created_by=admin.id,
            ),
            # e017 — Revêtement mural Genève: clean
            Material(
                id=uuid.uuid4(),
                element_id=e017.id,
                material_type="paint",
                name="Peinture acrylique",
                installation_year=1985,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e017.id,
                material_type="plaster",
                name="Enduit plâtre intérieur",
                installation_year=1955,
                created_by=admin.id,
            ),
            # e018 — Mur porteur Biel: clean
            Material(
                id=uuid.uuid4(),
                element_id=e018.id,
                material_type="concrete",
                name="Béton armé industriel",
                installation_year=1972,
                created_by=admin.id,
            ),
            # e019 — Toiture Biel: bitumen with HAP
            Material(
                id=uuid.uuid4(),
                element_id=e019.id,
                material_type="metal",
                name="Bac acier toiture",
                installation_year=1972,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e019.id,
                material_type="bitumen",
                name="Étanchéité bitumineuse toiture",
                description="Membrane bitumineuse d'étanchéité de toiture",
                installation_year=1972,
                contains_pollutant=True,
                pollutant_type="hap",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Bitume d'origine 1972, susceptible de contenir des HAP",
                created_by=diagnostician.id,
            ),
            # e020 — Sol garage Biel: clean
            Material(
                id=uuid.uuid4(),
                element_id=e020.id,
                material_type="concrete",
                name="Béton industriel garage",
                installation_year=1972,
                created_by=admin.id,
            ),
            # e023 — Collecteur: asbestos joints
            Material(
                id=uuid.uuid4(),
                element_id=e023.id,
                material_type="sealant",
                name="Joints amiantés collecteur",
                description="Joints en fibrociment entre éléments de fonte",
                installation_year=1962,
                contains_pollutant=True,
                pollutant_type="asbestos",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Joints typiques des collecteurs pré-1990",
                created_by=diagnostician.id,
            ),
            # e025 — Parquet 2ème: adhesive with HAP
            Material(
                id=uuid.uuid4(),
                element_id=e025.id,
                material_type="wood",
                name="Parquet chêne massif",
                installation_year=1962,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e025.id,
                material_type="adhesive",
                name="Colle bitumineuse parquet",
                description="Colle noire bitumineuse sous les lames de parquet",
                installation_year=1962,
                contains_pollutant=True,
                pollutant_type="hap",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Colle bitumineuse noire typique des années 50-70",
                created_by=diagnostician.id,
            ),
            # e027 — Balcons: bitumen with HAP
            Material(
                id=uuid.uuid4(),
                element_id=e027.id,
                material_type="concrete",
                name="Béton armé balcon",
                installation_year=1962,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e027.id,
                material_type="bitumen",
                name="Étanchéité bitumineuse balcon",
                description="Membrane bitumineuse d'étanchéité des balcons",
                installation_year=1962,
                contains_pollutant=True,
                pollutant_type="hap",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Étanchéité d'origine suspecte de HAP",
                created_by=diagnostician.id,
            ),
            # e030 — Réseau air comprimé Biel: PCB in sealant
            Material(
                id=uuid.uuid4(),
                element_id=e030.id,
                material_type="metal",
                name="Tuyauterie acier air comprimé",
                installation_year=1972,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e030.id,
                material_type="sealant",
                name="Mastic joints air comprimé",
                description="Mastic d'étanchéité aux raccords",
                installation_year=1972,
                contains_pollutant=True,
                pollutant_type="pcb",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Mastic d'étanchéité de l'époque PCB (1972)",
                created_by=diagnostician.id,
            ),
            # e033 — Peinture sol atelier: lead paint
            Material(
                id=uuid.uuid4(),
                element_id=e033.id,
                material_type="paint",
                name="Peinture époxy sol atelier",
                description="Peinture de sol industrielle potentiellement au plomb",
                installation_year=1980,
                contains_pollutant=True,
                pollutant_type="lead",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Peinture industrielle ancienne, test plomb recommandé",
                created_by=diagnostician.id,
            ),
            # e034 — Isolation combles: clean (recent)
            Material(
                id=uuid.uuid4(),
                element_id=e034.id,
                material_type="mineral_wool",
                name="Laine minérale soufflée",
                description="Isolation récente (1988) en laine de roche",
                installation_year=1988,
                created_by=admin.id,
            ),
            # e035 — Fenêtres Genève: putty with PCB
            Material(
                id=uuid.uuid4(),
                element_id=e035.id,
                material_type="wood",
                name="Cadre bois fenêtre",
                installation_year=1955,
                created_by=admin.id,
            ),
            Material(
                id=uuid.uuid4(),
                element_id=e035.id,
                material_type="sealant",
                name="Mastic vitrier PCB",
                description="Mastic de vitrage d'origine",
                installation_year=1955,
                contains_pollutant=True,
                pollutant_type="pcb",
                pollutant_confirmed=False,
                source="visual_inspection",
                notes="Mastic de vitrage 1955, période d'utilisation du PCB",
                created_by=diagnostician.id,
            ),
        ]
        db.add_all(mat_list)
        await db.flush()

        # ── Interventions ──────────────────────────────────────────────
        iv001 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            intervention_type="renovation",
            title="Rénovation cuisine 2ème étage",
            description="Rénovation complète de la cuisine de l'appartement 2.1",
            status="completed",
            date_start=date(2018, 3, 1),
            date_end=date(2018, 5, 15),
            contractor_name="Bati-Rénov SA",
            cost_chf=45000.0,
            zones_affected=[str(z004.id)],
            created_by=admin.id,
        )
        iv002 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            intervention_type="renovation",
            title="Remplacement fenêtres 1er étage",
            description="Remplacement de toutes les fenêtres du 1er étage par du PVC double vitrage",
            status="completed",
            date_start=date(2010, 6, 1),
            date_end=date(2010, 8, 30),
            contractor_name="Vitroplus Sàrl",
            cost_chf=28000.0,
            zones_affected=[str(z003.id)],
            created_by=admin.id,
        )
        iv003 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            intervention_type="inspection",
            title="Inspection conduite eau",
            description="Inspection par caméra des conduites d'eau chaude et froide",
            status="completed",
            date_start=date(2023, 11, 15),
            date_end=date(2023, 11, 15),
            zones_affected=[str(z001.id), str(z008.id)],
            created_by=admin.id,
        )
        iv004 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            intervention_type="asbestos_removal",
            title="Désamiantage partiel faux plafonds",
            description="Retrait des plaques fibrociment amiantées dans le hall d'entrée",
            status="completed",
            date_start=date(2019, 9, 1),
            date_end=date(2019, 10, 15),
            contractor_name="Sanacore Bau GmbH",
            cost_chf=35000.0,
            zones_affected=[str(z010.id)],
            created_by=admin.id,
        )
        iv005 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            intervention_type="diagnostic",
            title="Diagnostic amiante avant travaux",
            description="Diagnostic amiante complet avant les travaux de désamiantage",
            status="completed",
            date_start=date(2019, 7, 1),
            date_end=date(2019, 7, 15),
            diagnostic_id=diag1.id,
            created_by=diagnostician.id,
        )
        iv006 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            intervention_type="maintenance",
            title="Réfection étanchéité toiture",
            description="Réfection complète de l'étanchéité de la toiture plate",
            status="planned",
            date_start=date(2025, 6, 1),
            cost_chf=55000.0,
            zones_affected=[str(z005.id)],
            notes="Devis reçu de 3 entreprises. Choix en attente.",
            created_by=admin.id,
        )
        iv007 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            intervention_type="repair",
            title="Remplacement conduite chauffage",
            description="Remplacement des conduites de chauffage avec calorifuge amianté",
            status="in_progress",
            date_start=date(2026, 2, 1),
            contractor_name="Sanacore Bau GmbH",
            cost_chf=15000.0,
            zones_affected=[str(z011.id)],
            created_by=admin.id,
        )
        iv008 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            intervention_type="diagnostic",
            title="Diagnostic polluants complet",
            description="Diagnostic complet amiante, PCB, plomb avant transformation commerciale",
            status="completed",
            date_start=date(2022, 4, 1),
            date_end=date(2022, 5, 15),
            diagnostic_id=diag2.id,
            created_by=diagnostician.id,
        )
        iv009 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[1].id,
            intervention_type="maintenance",
            title="Maintenance ascenseur",
            description="Maintenance annuelle de l'ascenseur et mise aux normes",
            status="completed",
            date_start=date(2023, 3, 10),
            date_end=date(2023, 3, 10),
            cost_chf=3500.0,
            created_by=admin.id,
        )
        iv010 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            intervention_type="installation",
            title="Construction extension garage",
            description="Agrandissement du garage avec nouvelle dalle béton",
            status="completed",
            date_start=date(2015, 4, 1),
            date_end=date(2015, 9, 30),
            contractor_name="Bau+Werk AG",
            cost_chf=80000.0,
            zones_affected=[str(z017.id)],
            created_by=admin.id,
        )
        iv011 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            intervention_type="maintenance",
            title="Peinture façade",
            description="Nettoyage et peinture complète des façades",
            status="completed",
            date_start=date(2020, 5, 1),
            date_end=date(2020, 6, 15),
            contractor_name="Maler Schmidt GmbH",
            cost_chf=12000.0,
            created_by=admin.id,
        )
        iv012 = Intervention(
            id=uuid.uuid4(),
            building_id=buildings[2].id,
            intervention_type="inspection",
            title="Inspection radon",
            description="Pose de dosimètres radon dans les locaux du rez-de-chaussée",
            status="planned",
            date_start=date(2025, 10, 1),
            zones_affected=[str(z015.id)],
            notes="Zone à risque radon élevé (canton BE)",
            created_by=admin.id,
        )

        all_interventions = [
            iv001,
            iv002,
            iv003,
            iv004,
            iv005,
            iv006,
            iv007,
            iv008,
            iv009,
            iv010,
            iv011,
            iv012,
        ]
        db.add_all(all_interventions)
        await db.flush()

        # ── Technical Plans ────────────────────────────────────────────
        tech_plans = [
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                plan_type="floor_plan",
                title="Plan étage rez-de-chaussée",
                description="Plan du rez-de-chaussée avec cotations",
                floor_number=0,
                version="1.0",
                file_path="plans/building-1/plan-rdc.pdf",
                file_name="plan-rdc.pdf",
                mime_type="application/pdf",
                file_size_bytes=2500000,
                zone_id=z002.id,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                plan_type="floor_plan",
                title="Plan étage 1er",
                description="Plan du 1er étage avec appartements",
                floor_number=1,
                version="1.0",
                file_path="plans/building-1/plan-1er.pdf",
                file_name="plan-1er.pdf",
                mime_type="application/pdf",
                file_size_bytes=2300000,
                zone_id=z003.id,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                plan_type="floor_plan",
                title="Plan étage 2ème",
                description="Plan du 2ème étage avec appartements",
                floor_number=2,
                version="1.0",
                file_path="plans/building-1/plan-2eme.pdf",
                file_name="plan-2eme.pdf",
                mime_type="application/pdf",
                file_size_bytes=2400000,
                zone_id=z004.id,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                plan_type="cross_section",
                title="Coupe longitudinale",
                description="Coupe longitudinale du bâtiment",
                version="1.0",
                file_path="plans/building-1/coupe-longitudinale.pdf",
                file_name="coupe-longitudinale.pdf",
                mime_type="application/pdf",
                file_size_bytes=1800000,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[0].id,
                plan_type="technical_schema",
                title="Schéma technique chauffage",
                description="Schéma du réseau de chauffage",
                version="2.1",
                file_path="plans/building-1/schema-chauffage.pdf",
                file_name="schema-chauffage.pdf",
                mime_type="application/pdf",
                file_size_bytes=1200000,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                plan_type="site_plan",
                title="Plan de situation",
                description="Plan de situation avec emprise au sol et accès",
                version="1.0",
                file_path="plans/building-2/plan-situation.pdf",
                file_name="plan-situation.pdf",
                mime_type="application/pdf",
                file_size_bytes=3200000,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[2].id,
                plan_type="floor_plan",
                title="Plan rez-de-chaussée",
                description="Plan du rez-de-chaussée de l'usine",
                floor_number=0,
                version="1.0",
                file_path="plans/building-3/plan-rdc.pdf",
                file_name="plan-rdc.pdf",
                mime_type="application/pdf",
                file_size_bytes=4100000,
                zone_id=z015.id,
                uploaded_by=admin.id,
            ),
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=buildings[1].id,
                plan_type="elevation",
                title="Élévation façade sud",
                description="Élévation architecturale de la façade sud",
                version="1.0",
                file_path="plans/building-2/elevation-facade-sud.pdf",
                file_name="elevation-facade-sud.pdf",
                mime_type="application/pdf",
                file_size_bytes=1500000,
                uploaded_by=admin.id,
            ),
        ]
        db.add_all(tech_plans)
        await db.flush()

        # ── Evidence Links ─────────────────────────────────────────────
        # Fetch risk scores for the 3 buildings
        b1_risk_result = await db.execute(
            select(BuildingRiskScore).where(BuildingRiskScore.building_id == buildings[0].id)
        )
        b1_risk = b1_risk_result.scalar_one()

        b2_risk_result = await db.execute(
            select(BuildingRiskScore).where(BuildingRiskScore.building_id == buildings[1].id)
        )
        b2_risk = b2_risk_result.scalar_one()

        b3_risk_result = await db.execute(
            select(BuildingRiskScore).where(BuildingRiskScore.building_id == buildings[2].id)
        )
        b3_risk = b3_risk_result.scalar_one()

        evidence_links = [
            # Building 1: sample proves risk_score
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample1_1.id,
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="proves",
                confidence=0.95,
                legal_reference="CFST 6503 Art. 3.2",
                explanation=(
                    "Échantillon LS-2025-001 confirme présence d'amiante chrysotile 15% dans les dalles vinyle"
                ),
                created_by=diagnostician.id,
            ),
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample1_2.id,
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="proves",
                confidence=0.95,
                legal_reference="ORRChim Annexe 2.15",
                explanation=(
                    "Échantillon LS-2025-002 confirme PCB 1250 mg/kg dans les joints de façade (seuil: 50 mg/kg)"
                ),
                created_by=diagnostician.id,
            ),
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="diagnostic",
                source_id=diag1.id,
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="supports",
                confidence=0.90,
                explanation="Diagnostic complet AvT confirme la présence de polluants multiples",
                created_by=diagnostician.id,
            ),
            # Material (suspected) supports risk_score
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="material",
                source_id=mat_list[7].id,  # Panneaux isolants fibreux (e005)
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="supports",
                confidence=0.70,
                explanation=("Panneaux isolants fibreux en état critique — visuel compatible avec amiante"),
                created_by=diagnostician.id,
            ),
            # Sample triggers action_item (asbestos removal)
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample1_1.id,
                target_type="action_item",
                target_id=action_defs[0].id,
                relationship="triggers",
                confidence=0.95,
                legal_reference="CFST 6503",
                explanation=("Résultat positif amiante déclenche l'obligation de planifier le retrait"),
                created_by=diagnostician.id,
            ),
            # Pollutant rule requires action_item
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="pollutant_rule",
                source_id=pollutant_rules[0].id,
                target_type="action_item",
                target_id=action_defs[0].id,
                relationship="requires",
                confidence=1.0,
                legal_reference="OTConst Art. 60a",
                explanation=("La réglementation exige le retrait de l'amiante avant travaux de rénovation"),
                created_by=admin.id,
            ),
            # Sample triggers action_item (PCB decontamination)
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample1_2.id,
                target_type="action_item",
                target_id=action_defs[1].id,
                relationship="triggers",
                confidence=0.95,
                legal_reference="ORRChim Annexe 2.15",
                explanation=("PCB 25x au-dessus du seuil réglementaire — décontamination obligatoire"),
                created_by=diagnostician.id,
            ),
            # Building 2: sample proves risk_score
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample2_1.id,
                target_type="building_risk_score",
                target_id=b2_risk.id,
                relationship="proves",
                confidence=0.85,
                legal_reference="CFST 6503 Art. 4.1",
                explanation=("Flocage friable identifié — risque critique d'exposition à l'amiante"),
                created_by=diagnostician.id,
            ),
            # Diagnostic supports risk_score (building 2)
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="diagnostic",
                source_id=diag2.id,
                target_type="building_risk_score",
                target_id=b2_risk.id,
                relationship="supports",
                confidence=0.80,
                explanation=("Diagnostic en cours avec flocage suspect — confirme le risque élevé"),
                created_by=diagnostician.id,
            ),
            # Material (flocage) supports action_item (building 2)
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="material",
                source_id=mat_list[22].id,  # Flocage amiante chaufferie
                target_type="action_item",
                target_id=action_defs[2].id,
                relationship="supports",
                confidence=0.90,
                legal_reference="CFST 6503",
                explanation=("Matériau flocage friable renforce l'urgence de finaliser le diagnostic"),
                created_by=diagnostician.id,
            ),
            # Intervention (désamiantage) supersedes risk
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="intervention",
                source_id=iv004.id,
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="supersedes",
                confidence=0.85,
                explanation=("Le désamiantage partiel des faux plafonds réduit le risque dans le hall"),
                created_by=admin.id,
            ),
            # Sample (lead under threshold) contradicts risk
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample1_3.id,
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="contradicts",
                confidence=0.80,
                legal_reference="ORRChim Annexe 2.18",
                explanation=("Plomb 4200 mg/kg sous le seuil de 5000 mg/kg — risque plomb inférieur au modèle"),
                created_by=diagnostician.id,
            ),
            # Building 3: material (bitumen HAP) supports risk_score
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="material",
                source_id=mat_list[28].id,  # Étanchéité bitumineuse toiture
                target_type="building_risk_score",
                target_id=b3_risk.id,
                relationship="supports",
                confidence=0.60,
                explanation=("Étanchéité bitumineuse d'origine 1972, suspicion de HAP par inspection visuelle"),
                created_by=diagnostician.id,
            ),
            # Pollutant rule (radon) requires action
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="pollutant_rule",
                source_id=pollutant_rules[9].id,  # Radon 300 Bq/m3
                target_type="action_item",
                target_id=action_defs[4].id,
                relationship="requires",
                confidence=1.0,
                legal_reference="ORaP Art. 110",
                explanation=("La réglementation impose la mesure du radon en zone à risque"),
                created_by=admin.id,
            ),
            # Material (PCB sealant) supports risk_score (building 3)
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="material",
                source_id=mat_list[36].id,  # Mastic joints air comprimé
                target_type="building_risk_score",
                target_id=b3_risk.id,
                relationship="supports",
                confidence=0.65,
                legal_reference="ORRChim Annexe 2.15",
                explanation=("Mastic d'étanchéité de 1972, période d'utilisation courante du PCB"),
                created_by=diagnostician.id,
            ),
            # Diagnostic supports intervention (désamiantage)
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="diagnostic",
                source_id=diag1.id,
                target_type="intervention",
                target_id=iv004.id,
                relationship="supports",
                confidence=0.95,
                explanation=("Le diagnostic AvT a identifié les zones nécessitant un désamiantage"),
                created_by=diagnostician.id,
            ),
            # Intervention (fenêtres) contradicts PCB risk
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="intervention",
                source_id=iv002.id,
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="contradicts",
                confidence=0.70,
                explanation=("Le remplacement des fenêtres en 2010 a éliminé le mastic PCB potentiel au 1er étage"),
                created_by=admin.id,
            ),
            # Material (lead paint door) supports risk_score
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="material",
                source_id=mat_list[13].id,  # Peinture porte au plomb
                target_type="building_risk_score",
                target_id=b1_risk.id,
                relationship="supports",
                confidence=0.55,
                explanation=("Peinture multicouche 1975 suspecte de plomb — inspection visuelle uniquement"),
                created_by=diagnostician.id,
            ),
            # Sample (flocage Genève) triggers action_item
            EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=sample2_1.id,
                target_type="action_item",
                target_id=action_defs[2].id,
                relationship="triggers",
                confidence=0.90,
                legal_reference="CFST 6503 Art. 4.1",
                explanation=("Flocage friable identifié — le diagnostic doit être finalisé en priorité"),
                created_by=diagnostician.id,
            ),
        ]
        db.add_all(evidence_links)
        await db.flush()

        # ── Campaigns ──────────────────────────────────────────────────
        campaign_buildings_diag = [str(b.id) for b in all_buildings[:5]]
        campaign_buildings_maint = [str(b.id) for b in all_buildings[:3]]
        campaign_buildings_urgent = [str(b.id) for b in all_buildings[:2]]
        campaigns_seed = [
            Campaign(
                id=uuid.uuid4(),
                title="Campagne diagnostic amiante 2026",
                description="Diagnostic amiante systématique sur le portefeuille VD/GE avant rénovation.",
                campaign_type="diagnostic",
                status="active",
                priority="high",
                organization_id=org1.id,
                building_ids=campaign_buildings_diag,
                target_count=len(campaign_buildings_diag),
                completed_count=1,
                date_start=date(2026, 1, 15),
                date_end=date(2026, 6, 30),
                budget_chf=75000.0,
                spent_chf=12500.0,
                created_by=admin.id,
            ),
            Campaign(
                id=uuid.uuid4(),
                title="Maintenance préventive Q2",
                description="Inspections préventives trimestrielles sur les bâtiments résidentiels.",
                campaign_type="maintenance",
                status="draft",
                priority="medium",
                organization_id=org1.id,
                building_ids=campaign_buildings_maint,
                target_count=len(campaign_buildings_maint),
                completed_count=0,
                date_start=date(2026, 4, 1),
                date_end=date(2026, 6, 30),
                budget_chf=15000.0,
                created_by=admin.id,
            ),
            Campaign(
                id=uuid.uuid4(),
                title="Désamiantage urgent",
                description="Désamiantage prioritaire suite à diagnostic positif confirmé.",
                campaign_type="remediation",
                status="active",
                priority="critical",
                organization_id=org1.id,
                building_ids=campaign_buildings_urgent,
                target_count=len(campaign_buildings_urgent),
                completed_count=0,
                date_start=date(2026, 2, 1),
                date_end=date(2026, 4, 30),
                budget_chf=180000.0,
                spent_chf=35000.0,
                created_by=admin.id,
            ),
        ]
        db.add_all(campaigns_seed)
        await db.flush()

        # ── Commit ─────────────────────────────────────────────────────
        await db.commit()

        # ── Auto-generate actions from completed/validated diagnostics ─
        # Must run after commit so diagnostics + samples are persisted.
        # generate_actions_from_diagnostic is idempotent (checks existing keys).
        auto_generated_actions: list = []
        completed_diags = [
            (buildings[0].id, diag1.id),  # completed
            (extra_buildings[1].id, diag4.id),  # validated
            (extra_buildings[3].id, diag5.id),  # completed (PCB Basel)
            (extra_buildings[5].id, diag7.id),  # completed (HAP Fribourg)
            (SCENARIO_IDS["contradiction"], sc_diag_pos.id),  # scenario: contradiction
            (SCENARIO_IDS["nearly_ready"], sc_diag_ready.id),  # scenario: nearly-ready
            (SCENARIO_IDS["post_works"], sc_diag_pw.id),  # scenario: post-works
        ]
        for b_id, d_id in completed_diags:
            generated = await generate_actions_from_diagnostic(db, b_id, d_id)
            auto_generated_actions.extend(generated)

        n_buildings = len(all_buildings)
        n_total_events = n_buildings + 2 + len(rich_events)
        n_total_actions = len(action_defs) + len(auto_generated_actions)
        print("[SEED] Database seeded successfully!")
        print("  - 5 organizations")
        print("  - 7 users (admin/diagnostician/owner/architect/authority/contractor + 1 inactive)")
        print(f"  - {n_buildings} buildings across multiple cantons (with jurisdiction_id)")
        print(f"  - {len(pollutant_rules)} pollutant rules")
        print("  - 7 diagnostics (draft/in_progress/completed/validated)")
        print("  - ~15 samples")
        print(f"  - {n_buildings} building risk scores")
        print("  - 6 documents")
        print(
            f"  - {n_total_actions} action items ({len(action_defs)} manual + {len(auto_generated_actions)} auto-generated)"
        )
        print(f"  - {n_total_events} events (construction + diagnostic + rich timeline)")
        print(f"  - {len(invitations)} invitations")
        print(f"  - {len(assignments)} assignments")
        print(f"  - {len(notifications)} notifications")
        print(f"  - {len(export_jobs)} export jobs")
        print("  - 6 notification preferences")
        print(f"  - {len(all_zones)} zones")
        print(f"  - {len(all_elements)} building elements")
        print(f"  - {len(mat_list)} materials")
        print(f"  - {len(all_interventions)} interventions")
        print(f"  - {len(tech_plans)} technical plans")
        print(f"  - {len(evidence_links)} evidence links")
        print(f"  - {len(campaigns_seed)} campaigns")
        print(
            f"  - {len(scenario_buildings)} scenario buildings (contradiction/nearly-ready/post-works/portfolio/empty)"
        )


if __name__ == "__main__":
    asyncio.run(seed())
