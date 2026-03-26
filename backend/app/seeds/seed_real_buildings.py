"""
SwissBuildingOS - Real Swiss Buildings Seed
Idempotent seed with ~40 real buildings from 3 property managers in canton VD.

Organizations:
  1. Gérance Borgeaud SA (property_management) — 15 buildings
  2. Ville de Lausanne (authority) — 15 buildings
  3. Etat de Vaud - DGIP (authority) — 10 buildings

Also seeds diagnostics, obligations, and permit procedures for a subset.

Usage:
    python -m app.seeds.seed_real_buildings
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.models.permit_procedure import PermitProcedure
from app.models.sample import Sample
from app.models.user import User
from app.seeds.seed_jurisdictions import ID_CH_VD

logger = logging.getLogger(__name__)

# ── UUID5 namespace for idempotent IDs ──────────────────────────────────────
_NS = uuid.UUID("c4d5e6f7-a8b9-0123-cdef-456789abcdef")


def _id(key: str) -> uuid.UUID:
    return uuid.uuid5(_NS, key)


# ── Organization IDs ────────────────────────────────────────────────────────
ORG_BORGEAUD_ID = _id("org-gerance-borgeaud")
ORG_VILLE_LAUSANNE_ID = _id("org-ville-de-lausanne")
ORG_DGIP_ID = _id("org-etat-de-vaud-dgip")


# ── Risk score helper (from seed_data.py) ───────────────────────────────────
def _risk_score(construction_year: int | None, building_type: str) -> dict:
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

    if construction_year is None:
        hap = 0.3
    elif construction_year < 1960:
        hap = 0.65
    elif construction_year <= 1975:
        hap = 0.45
    else:
        hap = 0.10

    radon = 0.40  # VD = medium radon zone

    if building_type == "industrial":
        asb = min(asb * 1.15, 1.0)
        pcb = min(pcb * 1.20, 1.0)
        hap = min(hap * 1.30, 1.0)

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


# ── Building type mapping ──────────────────────────────────────────────────
_TYPE_MAP = {
    "Immeuble locatif": "residential",
    "Bâtiment public": "public",
    "Bâtiment industriel": "industrial",
    "École/Formation": "educational",
    "Immeuble de bureaux": "commercial",
    "Bâtiment agricole": "agricultural",
}

# ── Building definitions ───────────────────────────────────────────────────
# Each tuple: (address, postal_code, city, eca, construction_year, genre, surface_m2, egid, lat, lon)

BORGEAUD_BUILDINGS = [
    (
        "Avenue Charles Ferdinand Ramuz 94",
        "1009",
        "Pully",
        "ECA 1261",
        1950,
        "Immeuble locatif",
        1890.0,
        1041261,
        46.5103,
        6.6615,
    ),
    (
        "Avenue Eugène-Rambert 12",
        "1005",
        "Lausanne",
        "ECA 10249",
        1932,
        "Immeuble locatif",
        1200.0,
        1102490,
        46.5230,
        6.6345,
    ),
    (
        "Avenue Rumine 34-36",
        "1000",
        "Lausanne",
        "ECA 10438",
        1933,
        "Immeuble locatif",
        3600.0,
        1104380,
        46.5210,
        6.6370,
    ),
    ("Avenue Vinet 29", "1004", "Lausanne", "ECA 4962", 1950, "Immeuble locatif", 1400.0, 1049620, 46.5220, 6.6240),
    ("Avenue de Floréal 35", "1008", "Prilly", "ECA 1174", 1953, "Immeuble locatif", 1100.0, 1011740, 46.5280, 6.6050),
    (
        "Avenue de la Vallonnette 3",
        "1012",
        "Lausanne",
        "ECA 12588",
        1954,
        "Immeuble locatif",
        1300.0,
        1125880,
        46.5340,
        6.6520,
    ),
    ("Avenue du Léman 4", "1005", "Lausanne", "ECA 6372", 1930, "Immeuble locatif", 1050.0, 1063720, 46.5120, 6.6280),
    ("Chemin de Beau-Val 2", "1012", "Lausanne", "ECA 9467", 1960, "Immeuble locatif", 980.0, 1094670, 46.5360, 6.6490),
    (
        "Chemin des Fauvettes 6",
        "1012",
        "Lausanne",
        "ECA 6624",
        1960,
        "Immeuble locatif",
        920.0,
        1066240,
        46.5350,
        6.6510,
    ),
    ("Chemin des Roses 1-3", "1009", "Pully", "ECA 2098", 1970, "Immeuble locatif", 2400.0, 1020980, 46.5090, 6.6600),
    ("Rue de l'Ale 38", "1003", "Lausanne", "ECA 5194", 1930, "Immeuble locatif", 1150.0, 1051940, 46.5260, 6.6310),
    ("Vallonnette 1", "1012", "Lausanne", "ECA 13126", 1960, "Immeuble locatif", 1050.0, 1131260, 46.5342, 6.6515),
    (
        "Avenue Antoine-Henri Jomini 22",
        "1004",
        "Lausanne",
        "ECA 14754",
        1950,
        "Immeuble locatif",
        1350.0,
        1147540,
        46.5195,
        6.6180,
    ),
    (
        "Chemin de Contigny 15",
        "1007",
        "Lausanne",
        "ECA 12415",
        1960,
        "Immeuble locatif",
        1250.0,
        1124150,
        46.5170,
        6.6400,
    ),
    ("Rue de l'Ale 30", "1003", "Lausanne", "ECA 11800", 1930, "Immeuble locatif", 1100.0, 1118000, 46.5258, 6.6305),
]

VILLE_LAUSANNE_BUILDINGS = [
    (
        "Avenue Emile-Henri Jaques-Dalcroze 5",
        "1007",
        "Lausanne",
        "ECA 14586",
        1964,
        "Bâtiment public",
        3850.0,
        1145860,
        46.5070,
        6.6040,
    ),
    (
        "Avenue Frédéric-César-de-La-Harpe 52-56",
        "1007",
        "Lausanne",
        "ECA 1778",
        1888,
        "Immeuble locatif",
        6000.0,
        1017780,
        46.5135,
        6.6290,
    ),
    (
        "Avenue Jean-Jacques Mercier 3",
        "1003",
        "Lausanne",
        "ECA 191",
        1960,
        "Bâtiment industriel",
        2200.0,
        1001910,
        46.5185,
        6.6260,
    ),
    ("Avenue d'Ouchy 45", "1006", "Lausanne", "ECA 6733", 1980, "École/Formation", 4000.0, 1067330, 46.5100, 6.6250),
    (
        "Avenue de Villamont 4",
        "1005",
        "Lausanne",
        "ECA 14554",
        1962,
        "Bâtiment industriel",
        1800.0,
        1145540,
        46.5210,
        6.6360,
    ),
    (
        "Avenue de la Sallaz 38",
        "1010",
        "Lausanne",
        "ECA 12800",
        1955,
        "École/Formation",
        2500.0,
        1128000,
        46.5380,
        6.6440,
    ),
    (
        "Avenue des Bergières 44",
        "1004",
        "Lausanne",
        "ECA 15612",
        1972,
        "École/Formation",
        1600.0,
        1156120,
        46.5310,
        6.6200,
    ),
    (
        "Place Chauderon 4",
        "1002",
        "Lausanne",
        "ECA 15847",
        1977,
        "Immeuble de bureaux",
        4440.0,
        1158470,
        46.5225,
        6.6285,
    ),
    (
        "Place de la Cathédrale 12",
        "1005",
        "Lausanne",
        "ECA 8960",
        1904,
        "Bâtiment public",
        950.0,
        1089600,
        46.5230,
        6.6340,
    ),
    (
        "Place de la Cathédrale 2-4",
        "1005",
        "Lausanne",
        "ECA 8970",
        1903,
        "Bâtiment public",
        2100.0,
        1089700,
        46.5228,
        6.6338,
    ),
    ("Escaliers du Marché 27", "1003", "Lausanne", None, 1884, "Immeuble locatif", 850.0, None, 46.5240, 6.6330),
    (
        "Chemin des Pêcheurs 3",
        "1007",
        "Lausanne",
        "ECA 15333",
        1970,
        "Immeuble de bureaux",
        1900.0,
        1153330,
        46.5060,
        6.6070,
    ),
    ("Escaliers Arlaud", "1003", "Lausanne", "ECA 5411", 1860, "Bâtiment industriel", 1200.0, 1054110, 46.5238, 6.6325),
    (
        "Avenue du Chablais 46",
        "1007",
        "Lausanne",
        "ECA 13630",
        1956,
        "Immeuble de bureaux",
        1700.0,
        1136300,
        46.5150,
        6.6420,
    ),
    ("Route d'Oron 127", "1010", "Lausanne", "ECA 7109", 1920, "Bâtiment agricole", 2300.0, 1071090, 46.5400, 6.6500),
]

DGIP_BUILDINGS = [
    ("Rue Mercerie 22", "1003", "Lausanne", "ECA 9038", None, "Bâtiment public", 1500.0, 1090380, 46.5235, 6.6335),
    ("Rue Mercerie 24", "1003", "Lausanne", "ECA 9036", 1766, "Bâtiment public", 1600.0, 1090360, 46.5234, 6.6336),
    ("Rue Pierre Viret 2", "1005", "Lausanne", "ECA 9289", 1929, "Bâtiment public", 2200.0, 1092890, 46.5225, 6.6350),
    ("Rue Dr-César-Roux 2", "1005", "Lausanne", "ECA 8827", 1898, "Bâtiment public", 3000.0, 1088270, 46.5220, 6.6365),
    (
        "Avenue de Cour 14 bis",
        "1007",
        "Lausanne",
        "ECA 11372",
        1970,
        "Bâtiment public",
        1800.0,
        1113720,
        46.5130,
        6.6300,
    ),
    (
        "Avenue de Cour 33 bis",
        "1007",
        "Lausanne",
        "ECA 13912",
        1960,
        "Bâtiment public",
        2500.0,
        1139120,
        46.5115,
        6.6280,
    ),
    (
        "Route de la Maladière 43",
        "1022",
        "Chavannes-près-Renens",
        "ECA 453",
        1960,
        "Bâtiment public",
        3200.0,
        1004530,
        46.5290,
        6.5950,
    ),
    (
        "Avenue de l'Elysée 4",
        "1006",
        "Lausanne",
        "ECA 14277",
        1962,
        "Bâtiment public",
        1400.0,
        1142770,
        46.5110,
        6.6230,
    ),
    (
        "Quartier Centre-Dorigny",
        "1024",
        "Ecublens",
        "ECA 1641",
        1979,
        "École/Formation",
        8500.0,
        1016410,
        46.5250,
        6.5800,
    ),
    (
        "Place de la Riponne 2bis",
        "1005",
        "Lausanne",
        "ECA 5408",
        1839,
        "Bâtiment public",
        5200.0,
        1054080,
        46.5245,
        6.6330,
    ),
]

# ── Diagnostics (10 buildings) ──────────────────────────────────────────────
# Keys match building address slugs for UUID5 derivation
_DIAG_BUILDINGS = [
    # Borgeaud (4)
    "Avenue Charles Ferdinand Ramuz 94",
    "Avenue Rumine 34-36",
    "Avenue Vinet 29",
    "Chemin des Roses 1-3",
    # Ville de Lausanne (4)
    "Avenue Emile-Henri Jaques-Dalcroze 5",
    "Place Chauderon 4",
    "Place de la Cathédrale 2-4",
    "Route d'Oron 127",
    # DGIP (2)
    "Rue Dr-César-Roux 2",
    "Place de la Riponne 2bis",
]

_DIAG_META = {
    "Avenue Charles Ferdinand Ramuz 94": {
        "date_inspection": date(2024, 3, 15),
        "date_report": date(2024, 4, 2),
        "laboratory": "Analytica SA, Lausanne",
        "laboratory_report_number": "ANA-2024-1261",
        "summary": "Diagnostic amiante avant travaux — présence d'amiante chrysotile dans les colles de faïence (cuisine, SdB) et dans les joints de dilatation en façade. État non dégradé.",
        "conclusion": "positive",
        "samples": [
            (
                "AMI-R94-01",
                "1er étage",
                "Cuisine",
                "Colle de faïence sous carrelage",
                "asbestos",
                "chrysotile",
                2.5,
                "percent_weight",
                True,
                "medium",
                "medium",
            ),
            (
                "AMI-R94-02",
                "Façade",
                "Joint de dilatation",
                "Mastic de joint extérieur",
                "asbestos",
                "chrysotile",
                8.0,
                "percent_weight",
                True,
                "high",
                "major",
            ),
            (
                "AMI-R94-03",
                "Sous-sol",
                "Local technique",
                "Flocage sur conduites",
                "asbestos",
                None,
                0.0,
                "percent_weight",
                False,
                "low",
                None,
            ),
        ],
    },
    "Avenue Rumine 34-36": {
        "date_inspection": date(2024, 6, 10),
        "date_report": date(2024, 7, 1),
        "laboratory": "Suisse Labo Environnement SA",
        "laboratory_report_number": "SLE-2024-0438",
        "summary": "Diagnostic complet polluants — amiante dans colles et flocages, PCB dans joints de fenêtres. Bâtiment à risque élevé.",
        "conclusion": "positive",
        "samples": [
            (
                "AMI-AR34-01",
                "2e étage",
                "Salon",
                "Colle de sol vinyle",
                "asbestos",
                "chrysotile",
                5.2,
                "percent_weight",
                True,
                "high",
                "medium",
            ),
            (
                "PCB-AR34-01",
                "3e étage",
                "Fenêtre",
                "Joint de vitrage",
                "pcb",
                None,
                85.0,
                "mg/kg",
                True,
                "high",
                "medium",
            ),
            (
                "AMI-AR34-02",
                "Sous-sol",
                "Chaufferie",
                "Flocage calorifuge",
                "asbestos",
                "amosite",
                12.0,
                "percent_weight",
                True,
                "critical",
                "major",
            ),
        ],
    },
    "Avenue Vinet 29": {
        "date_inspection": date(2025, 1, 20),
        "date_report": date(2025, 2, 10),
        "laboratory": "Analytica SA, Lausanne",
        "laboratory_report_number": "ANA-2025-4962",
        "summary": "Diagnostic amiante AvT — aucune présence d'amiante détectée dans les matériaux analysés.",
        "conclusion": "negative",
        "samples": [
            (
                "AMI-V29-01",
                "RdC",
                "Hall d'entrée",
                "Colle de carrelage",
                "asbestos",
                None,
                0.0,
                "percent_weight",
                False,
                "low",
                None,
            ),
            (
                "AMI-V29-02",
                "2e étage",
                "Salle de bain",
                "Joint de baignoire",
                "asbestos",
                None,
                0.0,
                "percent_weight",
                False,
                "low",
                None,
            ),
        ],
    },
    "Chemin des Roses 1-3": {
        "date_inspection": date(2024, 9, 5),
        "date_report": date(2024, 10, 1),
        "laboratory": "Environnement Mesures SA",
        "laboratory_report_number": "EM-2024-2098",
        "summary": "Diagnostic polluants — plomb dans peintures anciennes des cages d'escalier. Amiante non détecté.",
        "conclusion": "positive",
        "samples": [
            (
                "PB-CR13-01",
                "Cage A",
                "Escalier",
                "Peinture murale cage d'escalier",
                "lead",
                None,
                8500.0,
                "mg/kg",
                True,
                "high",
                "medium",
            ),
            (
                "AMI-CR13-01",
                "Sous-sol",
                "Parking",
                "Flocage plafond",
                "asbestos",
                None,
                0.0,
                "percent_weight",
                False,
                "low",
                None,
            ),
        ],
    },
    "Avenue Emile-Henri Jaques-Dalcroze 5": {
        "date_inspection": date(2023, 11, 15),
        "date_report": date(2024, 1, 10),
        "laboratory": "Suisse Labo Environnement SA",
        "laboratory_report_number": "SLE-2023-T001",
        "summary": "Diagnostic amiante Théâtre de Vidy — amiante dans les dalles de faux-plafond et dans l'isolation des conduites techniques. Intervention planifiée.",
        "conclusion": "positive",
        "samples": [
            (
                "AMI-TV-01",
                "Foyer",
                "Plafond",
                "Dalle de faux-plafond",
                "asbestos",
                "chrysotile",
                3.8,
                "percent_weight",
                True,
                "high",
                "medium",
            ),
            (
                "AMI-TV-02",
                "Sous-scène",
                "Technique",
                "Isolation conduite chauffage",
                "asbestos",
                "amosite",
                15.0,
                "percent_weight",
                True,
                "critical",
                "major",
            ),
            (
                "AMI-TV-03",
                "Loge artiste",
                "Sol",
                "Colle linoléum",
                "asbestos",
                "chrysotile",
                1.2,
                "percent_weight",
                True,
                "medium",
                "minor",
            ),
        ],
    },
    "Place Chauderon 4": {
        "date_inspection": date(2024, 5, 20),
        "date_report": date(2024, 6, 15),
        "laboratory": "Analytica SA, Lausanne",
        "laboratory_report_number": "ANA-2024-C004",
        "summary": "Diagnostic polluants immeuble administratif — PCB dans joints de façade (années 70). Amiante dans flocage technique au sous-sol.",
        "conclusion": "positive",
        "samples": [
            (
                "PCB-CH4-01",
                "Façade Est",
                "Joint",
                "Joint de dilatation façade",
                "pcb",
                None,
                120.0,
                "mg/kg",
                True,
                "high",
                "medium",
            ),
            (
                "AMI-CH4-01",
                "Sous-sol",
                "Local CTA",
                "Flocage anti-feu",
                "asbestos",
                "chrysotile",
                6.5,
                "percent_weight",
                True,
                "high",
                "major",
            ),
        ],
    },
    "Place de la Cathédrale 2-4": {
        "date_inspection": date(2024, 2, 28),
        "date_report": date(2024, 3, 25),
        "laboratory": "Environnement Mesures SA",
        "laboratory_report_number": "EM-2024-MH01",
        "summary": "Diagnostic polluants Musée Historique — plomb dans peintures murales anciennes, HAP dans étanchéité toiture.",
        "conclusion": "positive",
        "samples": [
            (
                "PB-MH-01",
                "1er étage",
                "Salle exposition",
                "Peinture murale décorative",
                "lead",
                None,
                12000.0,
                "mg/kg",
                True,
                "critical",
                "major",
            ),
            (
                "HAP-MH-01",
                "Toiture",
                "Étanchéité",
                "Membrane bitumineuse",
                "hap",
                None,
                450.0,
                "mg/kg",
                True,
                "high",
                "medium",
            ),
        ],
    },
    "Route d'Oron 127": {
        "date_inspection": date(2024, 8, 12),
        "date_report": date(2024, 9, 5),
        "laboratory": "Agri-Labo SA",
        "laboratory_report_number": "AL-2024-F127",
        "summary": "Diagnostic polluants ferme communale — amiante dans plaques fibrociment de la toiture. PCB non détecté.",
        "conclusion": "positive",
        "samples": [
            (
                "AMI-FE-01",
                "Toiture",
                "Couverture",
                "Plaque fibrociment ondulée",
                "asbestos",
                "chrysotile",
                11.0,
                "percent_weight",
                True,
                "high",
                "medium",
            ),
        ],
    },
    "Rue Dr-César-Roux 2": {
        "date_inspection": date(2024, 4, 10),
        "date_report": date(2024, 5, 5),
        "laboratory": "Suisse Labo Environnement SA",
        "laboratory_report_number": "SLE-2024-CR02",
        "summary": "Diagnostic amiante et plomb — amiante dans colles anciennes, plomb dans peintures de cage d'escalier.",
        "conclusion": "positive",
        "samples": [
            (
                "AMI-CR2-01",
                "RdC",
                "Hall",
                "Colle de carrelage ancien",
                "asbestos",
                "chrysotile",
                4.0,
                "percent_weight",
                True,
                "high",
                "medium",
            ),
            (
                "PB-CR2-01",
                "Cage escalier",
                "Murs",
                "Peinture au plomb",
                "lead",
                None,
                9200.0,
                "mg/kg",
                True,
                "critical",
                "major",
            ),
        ],
    },
    "Place de la Riponne 2bis": {
        "date_inspection": date(2025, 2, 3),
        "date_report": date(2025, 3, 1),
        "laboratory": "Analytica SA, Lausanne",
        "laboratory_report_number": "ANA-2025-R002",
        "summary": "Diagnostic polluants Palais de Rumine — plomb dans peintures décoratives, amiante dans flocage combles. Bâtiment classé, intervention coordonnée avec DGIP.",
        "conclusion": "positive",
        "samples": [
            (
                "PB-PR-01",
                "2e étage",
                "Grande salle",
                "Peinture plafond décoratif",
                "lead",
                None,
                15000.0,
                "mg/kg",
                True,
                "critical",
                "major",
            ),
            (
                "AMI-PR-01",
                "Combles",
                "Charpente",
                "Flocage anti-feu",
                "asbestos",
                "chrysotile",
                7.0,
                "percent_weight",
                True,
                "high",
                "major",
            ),
            ("HAP-PR-01", "Sous-sol", "Cave", "Goudron de sol", "hap", None, 320.0, "mg/kg", True, "high", "medium"),
        ],
    },
}

# ── Obligations (for ~10 buildings with diagnostics) ────────────────────────
_OBLIGATION_DEFS = [
    # (building_address, title, type, due_date, recurrence, status, priority)
    (
        "Avenue Charles Ferdinand Ramuz 94",
        "Contrôle amiante périodique — joints façade",
        "regulatory_inspection",
        date(2025, 3, 15),
        "annual",
        "upcoming",
        "high",
    ),
    (
        "Avenue Rumine 34-36",
        "Suivi PCB joints fenêtres — mesure air intérieur",
        "diagnostic_followup",
        date(2025, 7, 1),
        None,
        "upcoming",
        "high",
    ),
    (
        "Avenue Rumine 34-36",
        "Assainissement flocage calorifuge sous-sol",
        "diagnostic_followup",
        date(2025, 12, 31),
        None,
        "upcoming",
        "critical",
    ),
    (
        "Chemin des Roses 1-3",
        "Décapage peinture plomb cage d'escalier A",
        "diagnostic_followup",
        date(2025, 6, 30),
        None,
        "upcoming",
        "high",
    ),
    (
        "Avenue Emile-Henri Jaques-Dalcroze 5",
        "Désamiantage faux-plafond foyer — Théâtre de Vidy",
        "diagnostic_followup",
        date(2025, 9, 1),
        None,
        "upcoming",
        "critical",
    ),
    (
        "Avenue Emile-Henri Jaques-Dalcroze 5",
        "Inspection périodique sécurité incendie — ECA",
        "regulatory_inspection",
        date(2025, 4, 15),
        "annual",
        "due_soon",
        "medium",
    ),
    (
        "Place Chauderon 4",
        "Assainissement PCB joints façade Est",
        "diagnostic_followup",
        date(2025, 8, 31),
        None,
        "upcoming",
        "high",
    ),
    (
        "Place de la Cathédrale 2-4",
        "Conservation peintures plomb — coordination DGIP",
        "diagnostic_followup",
        date(2026, 3, 31),
        None,
        "upcoming",
        "critical",
    ),
    (
        "Place de la Cathédrale 2-4",
        "Réfection étanchéité toiture — HAP",
        "diagnostic_followup",
        date(2025, 10, 15),
        None,
        "upcoming",
        "high",
    ),
    (
        "Route d'Oron 127",
        "Remplacement plaques fibrociment toiture",
        "diagnostic_followup",
        date(2025, 11, 30),
        None,
        "upcoming",
        "high",
    ),
    (
        "Rue Dr-César-Roux 2",
        "Contrôle plomb peintures cage escalier",
        "regulatory_inspection",
        date(2025, 5, 5),
        "biennial",
        "upcoming",
        "high",
    ),
    (
        "Place de la Riponne 2bis",
        "Coordination DGIP — assainissement Palais de Rumine",
        "diagnostic_followup",
        date(2026, 6, 30),
        None,
        "upcoming",
        "critical",
    ),
    (
        "Place de la Riponne 2bis",
        "Inspection quinquennale bâtiment classé",
        "regulatory_inspection",
        date(2026, 2, 3),
        "five_yearly",
        "upcoming",
        "medium",
    ),
]

# ── Permit procedures (5 buildings) ────────────────────────────────────────
_PERMIT_DEFS = [
    # (building_address, procedure_type, title, status, authority_name, reference_number, submitted_at, approved_at)
    (
        "Avenue Rumine 34-36",
        "suva_notification",
        "Notification SUVA — travaux d'assainissement amiante sous-sol",
        "approved",
        "SUVA Lausanne",
        "SUVA-VD-2024-0438",
        datetime(2024, 8, 1),
        datetime(2024, 8, 20),
    ),
    (
        "Avenue Emile-Henri Jaques-Dalcroze 5",
        "cantonal_declaration",
        "Déclaration cantonale — désamiantage Théâtre de Vidy",
        "submitted",
        "DGE-DIREN Canton de Vaud",
        "VD-DEC-2025-T001",
        datetime(2025, 2, 15),
        None,
    ),
    (
        "Place Chauderon 4",
        "suva_notification",
        "Notification SUVA — travaux PCB façade",
        "draft",
        "SUVA Lausanne",
        None,
        None,
        None,
    ),
    (
        "Place de la Riponne 2bis",
        "cantonal_declaration",
        "Déclaration cantonale — Palais de Rumine assainissement polluants",
        "submitted",
        "DGE-DIREN Canton de Vaud",
        "VD-DEC-2025-R002",
        datetime(2025, 3, 10),
        None,
    ),
    (
        "Route d'Oron 127",
        "communal_authorization",
        "Autorisation communale — remplacement toiture fibrociment",
        "approved",
        "Service d'urbanisme, Ville de Lausanne",
        "CAMAC-2024-F127",
        datetime(2024, 10, 1),
        datetime(2024, 11, 15),
    ),
]


async def seed_real_buildings() -> None:
    """Seed ~40 real Swiss buildings with diagnostics, obligations, and permits."""
    async with AsyncSessionLocal() as db:
        # ── Idempotency: check if first org already exists ──────────────
        result = await db.execute(select(Organization).where(Organization.id == ORG_BORGEAUD_ID))
        if result.scalar_one_or_none():
            print("[SEED-REAL] Real buildings already seeded — skipping.")
            return

        # ── Find admin user for created_by ──────────────────────────────
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin = result.scalar_one_or_none()
        if not admin:
            print("[SEED-REAL] No admin user found — run seed_data first.")
            return

        # ── Find diagnostician user ─────────────────────────────────────
        result = await db.execute(select(User).where(User.role == "diagnostician").limit(1))
        diagnostician = result.scalar_one_or_none()

        # ── Organizations ───────────────────────────────────────────────
        org_borgeaud = Organization(
            id=ORG_BORGEAUD_ID,
            name="Gérance Borgeaud SA",
            type="property_management",
            address="Avenue de la Gare 10",
            postal_code="1003",
            city="Lausanne",
            canton="VD",
            email="info@borgeaud-gestion.ch",
            phone="+41 21 312 45 67",
            suva_recognized=False,
            fach_approved=False,
        )
        org_ville = Organization(
            id=ORG_VILLE_LAUSANNE_ID,
            name="Ville de Lausanne",
            type="authority",
            address="Place de la Palud 2",
            postal_code="1003",
            city="Lausanne",
            canton="VD",
            email="info@lausanne.ch",
            phone="+41 21 315 21 11",
            suva_recognized=False,
            fach_approved=False,
        )
        org_dgip = Organization(
            id=ORG_DGIP_ID,
            name="Etat de Vaud - DGIP",
            type="authority",
            address="Place de la Riponne 10",
            postal_code="1014",
            city="Lausanne",
            canton="VD",
            email="info.dgip@vd.ch",
            phone="+41 21 316 73 00",
            suva_recognized=False,
            fach_approved=False,
        )
        db.add_all([org_borgeaud, org_ville, org_dgip])
        await db.flush()

        # ── Helper to create buildings ──────────────────────────────────
        all_buildings: list[Building] = []
        building_by_address: dict[str, Building] = {}

        def _make_building(
            bdef: tuple,
            org_id: uuid.UUID,
        ) -> Building:
            address, postal_code, city, eca, year, genre, surface, egid, lat, lon = bdef
            btype = _TYPE_MAP.get(genre, "residential")
            bid = _id(f"building-{address}")
            b = Building(
                id=bid,
                address=address,
                postal_code=postal_code,
                city=city,
                canton="VD",
                construction_year=year,
                building_type=btype,
                surface_area_m2=surface,
                egid=egid,
                official_id=eca.split()[-1] if eca else None,
                latitude=lat,
                longitude=lon,
                created_by=admin.id,
                status="active",
                jurisdiction_id=ID_CH_VD,
                organization_id=org_id,
                source_metadata_json={"eca": eca, "genre_batiment": genre} if eca else {"genre_batiment": genre},
            )
            all_buildings.append(b)
            building_by_address[address] = b
            return b

        for bdef in BORGEAUD_BUILDINGS:
            _make_building(bdef, ORG_BORGEAUD_ID)
        for bdef in VILLE_LAUSANNE_BUILDINGS:
            _make_building(bdef, ORG_VILLE_LAUSANNE_ID)
        for bdef in DGIP_BUILDINGS:
            _make_building(bdef, ORG_DGIP_ID)

        db.add_all(all_buildings)
        await db.flush()

        # ── Risk scores ─────────────────────────────────────────────────
        risk_scores = []
        for b in all_buildings:
            scores = _risk_score(b.construction_year, b.building_type)
            rs = BuildingRiskScore(
                id=_id(f"risk-{b.address}"),
                building_id=b.id,
                asbestos_probability=scores["asbestos_probability"],
                pcb_probability=scores["pcb_probability"],
                lead_probability=scores["lead_probability"],
                hap_probability=scores["hap_probability"],
                radon_probability=scores["radon_probability"],
                overall_risk_level=scores["overall_risk_level"],
                confidence=scores["confidence"],
                data_source="model",
            )
            risk_scores.append(rs)
        db.add_all(risk_scores)
        await db.flush()

        # ── Diagnostics + Samples ───────────────────────────────────────
        n_diagnostics = 0
        n_samples = 0
        for addr in _DIAG_BUILDINGS:
            b = building_by_address[addr]
            meta = _DIAG_META[addr]
            diag_id = _id(f"diag-{addr}")
            diag = Diagnostic(
                id=diag_id,
                building_id=b.id,
                diagnostic_type="asbestos",
                diagnostic_context="AvT",
                status="completed",
                diagnostician_id=diagnostician.id if diagnostician else admin.id,
                laboratory=meta["laboratory"],
                laboratory_report_number=meta["laboratory_report_number"],
                date_inspection=meta["date_inspection"],
                date_report=meta["date_report"],
                summary=meta["summary"],
                conclusion=meta["conclusion"],
                methodology="FACH 2018",
                suva_notification_required=meta["conclusion"] == "positive",
            )
            db.add(diag)
            n_diagnostics += 1

            for i, s in enumerate(meta["samples"]):
                sample_num, floor, room, mat_desc, poll_type, poll_sub, conc, unit, exceeded, risk, cfst = s
                sample = Sample(
                    id=_id(f"sample-{addr}-{i}"),
                    diagnostic_id=diag_id,
                    sample_number=sample_num,
                    location_floor=floor,
                    location_room=room,
                    material_description=mat_desc,
                    pollutant_type=poll_type,
                    pollutant_subtype=poll_sub,
                    concentration=conc,
                    unit=unit,
                    threshold_exceeded=exceeded,
                    risk_level=risk,
                    cfst_work_category=cfst,
                    action_required="remediation" if exceeded else None,
                    waste_disposal_type="special" if exceeded else None,
                )
                db.add(sample)
                n_samples += 1

        await db.flush()

        # ── Obligations ─────────────────────────────────────────────────
        n_obligations = 0
        for odef in _OBLIGATION_DEFS:
            addr, title, otype, due, recurrence, status, priority = odef
            b = building_by_address[addr]
            obl = Obligation(
                id=_id(f"obligation-{addr}-{title[:40]}"),
                building_id=b.id,
                title=title,
                obligation_type=otype,
                due_date=due,
                recurrence=recurrence,
                status=status,
                priority=priority,
                responsible_org_id=b.organization_id,
            )
            db.add(obl)
            n_obligations += 1
        await db.flush()

        # ── Permit procedures ───────────────────────────────────────────
        n_permits = 0
        for pdef in _PERMIT_DEFS:
            addr, ptype, title, status, authority, ref, submitted, approved = pdef
            b = building_by_address[addr]
            permit = PermitProcedure(
                id=_id(f"permit-{addr}-{ptype}"),
                building_id=b.id,
                procedure_type=ptype,
                title=title,
                status=status,
                authority_name=authority,
                authority_type="cantonal"
                if "canton" in authority.lower()
                else "federal"
                if "suva" in authority.lower()
                else "communal",
                reference_number=ref,
                submitted_at=submitted,
                approved_at=approved,
            )
            db.add(permit)
            n_permits += 1
        await db.flush()

        await db.commit()

        print(f"[SEED-REAL] Seeded {len(all_buildings)} real buildings from 3 organizations:")
        print(f"  - Gérance Borgeaud SA: {len(BORGEAUD_BUILDINGS)} buildings")
        print(f"  - Ville de Lausanne: {len(VILLE_LAUSANNE_BUILDINGS)} buildings")
        print(f"  - Etat de Vaud - DGIP: {len(DGIP_BUILDINGS)} buildings")
        print(f"  - {n_diagnostics} diagnostics ({n_samples} samples)")
        print(f"  - {n_obligations} obligations")
        print(f"  - {n_permits} permit procedures")
        print(f"  - {len(risk_scores)} risk scores")


if __name__ == "__main__":
    asyncio.run(seed_real_buildings())
