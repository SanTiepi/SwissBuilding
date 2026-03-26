"""
SwissBuildingOS - Comprehensive Demo Workspace Seed

Creates one stable, operations-rich workspace that can be reused for demos,
manual QA, and end-to-end UI testing.

Idempotent: safe to run multiple times.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_COMPLIANCE,
    ACTION_SOURCE_DIAGNOSTIC,
    ACTION_SOURCE_MANUAL,
    ACTION_STATUS_DONE,
    ACTION_STATUS_IN_PROGRESS,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_NOTIFY_SUVA,
    ACTION_TYPE_REMEDIATION,
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    SAMPLE_UNIT_BQ_PER_M3,
    SAMPLE_UNIT_MG_PER_KG,
    SAMPLE_UNIT_PERCENT_WEIGHT,
)
from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.compliance_artefact import ComplianceArtefact
from app.models.contact import Contact
from app.models.contract import Contract
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.document_link import DocumentLink
from app.models.event import Event
from app.models.field_observation import FieldObservation
from app.models.financial_entry import FinancialEntry
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.lease import Lease
from app.models.material import Material
from app.models.organization import Organization
from app.models.ownership_record import OwnershipRecord
from app.models.sample import Sample
from app.models.unit import Unit
from app.models.unit_zone import UnitZone
from app.models.user import User
from app.models.zone import Zone
from app.services.auth_service import hash_password, verify_password

logger = logging.getLogger(__name__)

T = TypeVar("T")
_NS = uuid.UUID("6c2c995b-4090-4e22-9fb0-7c3966b77cb7")


def _stable_id(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, name)


BUILDING_ID = _stable_id("demo-workspace-building")
DIAGNOSTIC_ID = _stable_id("demo-workspace-diagnostic")
ORG_ID = _stable_id("demo-workspace-org")
USER_IDS = {
    "admin": _stable_id("demo-workspace-user-admin"),
    "diagnostician": _stable_id("demo-workspace-user-diagnostician"),
}
CONTACT_IDS = {
    "owner_primary": _stable_id("demo-workspace-contact-owner-primary"),
    "owner_co": _stable_id("demo-workspace-contact-owner-co"),
    "tenant_pharmacy": _stable_id("demo-workspace-contact-tenant-pharmacy"),
    "tenant_clinic": _stable_id("demo-workspace-contact-tenant-clinic"),
    "tenant_flat": _stable_id("demo-workspace-contact-tenant-flat"),
    "vendor_heating": _stable_id("demo-workspace-contact-vendor-heating"),
    "vendor_cleaning": _stable_id("demo-workspace-contact-vendor-cleaning"),
    "vendor_elevator": _stable_id("demo-workspace-contact-vendor-elevator"),
    "vendor_insurer": _stable_id("demo-workspace-contact-vendor-insurer"),
}
ZONE_IDS = {
    "basement": _stable_id("demo-workspace-zone-basement"),
    "ground_floor": _stable_id("demo-workspace-zone-ground-floor"),
    "first_floor": _stable_id("demo-workspace-zone-first-floor"),
    "roof": _stable_id("demo-workspace-zone-roof"),
    "technical_room": _stable_id("demo-workspace-zone-technical-room"),
    "flat_201": _stable_id("demo-workspace-zone-flat-201"),
}
UNIT_IDS = {
    "pharmacy": _stable_id("demo-workspace-unit-pharmacy"),
    "clinic": _stable_id("demo-workspace-unit-clinic"),
    "flat_201": _stable_id("demo-workspace-unit-flat-201"),
}
UNIT_ZONE_IDS = {
    "pharmacy-ground": _stable_id("demo-workspace-unit-zone-pharmacy-ground"),
    "clinic-ground": _stable_id("demo-workspace-unit-zone-clinic-ground"),
    "flat-201-zone": _stable_id("demo-workspace-unit-zone-flat-201"),
}
ELEMENT_IDS = {
    "basement_pipe": _stable_id("demo-workspace-element-basement-pipe"),
    "roof_insulation": _stable_id("demo-workspace-element-roof-insulation"),
    "flat_flooring": _stable_id("demo-workspace-element-flat-flooring"),
}
SAMPLE_IDS = {
    "asbestos": _stable_id("demo-workspace-sample-asbestos"),
    "pcb": _stable_id("demo-workspace-sample-pcb"),
    "lead": _stable_id("demo-workspace-sample-lead"),
    "radon": _stable_id("demo-workspace-sample-radon"),
}
MATERIAL_IDS = {
    "pipe_wrap": _stable_id("demo-workspace-material-pipe-wrap"),
    "roof_bitumen": _stable_id("demo-workspace-material-roof-bitumen"),
    "vinyl_floor": _stable_id("demo-workspace-material-vinyl-floor"),
}
DOCUMENT_IDS = {
    "diagnostic_report": _stable_id("demo-workspace-document-diagnostic-report"),
    "ownership_extract": _stable_id("demo-workspace-document-ownership-extract"),
    "lease_flat": _stable_id("demo-workspace-document-lease-flat"),
    "service_contract": _stable_id("demo-workspace-document-service-contract"),
    "insurance_certificate": _stable_id("demo-workspace-document-insurance-certificate"),
    "suva_notice": _stable_id("demo-workspace-document-suva-notice"),
}
DOCUMENT_LINK_IDS = {
    "lease_flat": _stable_id("demo-workspace-document-link-lease-flat"),
    "service_contract": _stable_id("demo-workspace-document-link-service-contract"),
    "insurance_certificate": _stable_id("demo-workspace-document-link-insurance"),
    "suva_notice": _stable_id("demo-workspace-document-link-suva"),
}
ARTEFACT_IDS = {
    "suva_notification": _stable_id("demo-workspace-artefact-suva"),
    "cantonal_notice": _stable_id("demo-workspace-artefact-cantonal"),
}
OWNERSHIP_IDS = {
    "favre": _stable_id("demo-workspace-ownership-favre"),
    "lakeview": _stable_id("demo-workspace-ownership-lakeview"),
}
LEASE_IDS = {
    "pharmacy": _stable_id("demo-workspace-lease-pharmacy"),
    "clinic": _stable_id("demo-workspace-lease-clinic"),
    "flat": _stable_id("demo-workspace-lease-flat"),
}
CONTRACT_IDS = {
    "heating": _stable_id("demo-workspace-contract-heating"),
    "cleaning": _stable_id("demo-workspace-contract-cleaning"),
    "insurance": _stable_id("demo-workspace-contract-insurance"),
}
INSURANCE_POLICY_ID = _stable_id("demo-workspace-insurance-policy")
FINANCIAL_ENTRY_IDS = {
    "rent_flat_jan": _stable_id("demo-workspace-financial-rent-flat-jan"),
    "rent_flat_feb": _stable_id("demo-workspace-financial-rent-flat-feb"),
    "rent_pharmacy_jan": _stable_id("demo-workspace-financial-rent-pharmacy-jan"),
    "heating_service": _stable_id("demo-workspace-financial-heating-service"),
    "insurance_premium": _stable_id("demo-workspace-financial-insurance-premium"),
    "intervention_deposit": _stable_id("demo-workspace-financial-intervention-deposit"),
}
INTERVENTION_IDS = {
    "pipe_removal": _stable_id("demo-workspace-intervention-pipe-removal"),
    "roof_encapsulation": _stable_id("demo-workspace-intervention-roof-encapsulation"),
}
OBSERVATION_IDS = {
    "basement_pipe": _stable_id("demo-workspace-observation-basement-pipe"),
    "roof_access": _stable_id("demo-workspace-observation-roof-access"),
}
ACTION_IDS = {
    "remove_pipe": _stable_id("demo-workspace-action-remove-pipe"),
    "notify_suva": _stable_id("demo-workspace-action-notify-suva"),
    "consolidate_docs": _stable_id("demo-workspace-action-consolidate-docs"),
}
EVENT_IDS = {
    "construction": _stable_id("demo-workspace-event-construction"),
    "diagnostic_report": _stable_id("demo-workspace-event-diagnostic-report"),
    "lease_renewal": _stable_id("demo-workspace-event-lease-renewal"),
    "remediation_mobilization": _stable_id("demo-workspace-event-remediation-mobilization"),
}
ASSIGNMENT_IDS = {
    "building_owner": _stable_id("demo-workspace-assignment-building-owner"),
    "building_diagnostician": _stable_id("demo-workspace-assignment-building-diagnostician"),
    "diagnostic_reviewer": _stable_id("demo-workspace-assignment-diagnostic-reviewer"),
}


async def _upsert(db: AsyncSession, model: type[T], data: dict[str, Any]) -> T:
    entity = await db.get(model, data["id"])
    if entity is None:
        entity = model(**data)
        db.add(entity)
    else:
        for field, value in data.items():
            setattr(entity, field, value)
    await db.flush()
    return entity


async def _ensure_demo_users(db: AsyncSession) -> tuple[User, User, Organization]:
    admin_result = await db.execute(select(User).where(User.email == DEMO_ADMIN_EMAIL))
    admin = admin_result.scalar_one_or_none()

    if admin is None:
        org = await _upsert(
            db,
            Organization,
            {
                "id": ORG_ID,
                "name": "Demo Regie SwissBuilding",
                "type": "property_management",
                "address": "Rue Centrale 12",
                "postal_code": "1003",
                "city": "Lausanne",
                "canton": "VD",
                "email": "demo.regie@swissbuildingos.ch",
                "phone": "+41 21 555 10 10",
            },
        )
        admin = await _upsert(
            db,
            User,
            {
                "id": USER_IDS["admin"],
                "email": DEMO_ADMIN_EMAIL,
                "password_hash": hash_password(DEMO_ADMIN_PASSWORD),
                "first_name": "Admin",
                "last_name": "Demo",
                "role": "admin",
                "organization_id": org.id,
                "language": "fr",
                "is_active": True,
            },
        )
    else:
        if not verify_password(DEMO_ADMIN_PASSWORD, admin.password_hash):
            admin.password_hash = hash_password(DEMO_ADMIN_PASSWORD)
        admin.is_active = True
        admin.language = "fr"

        org = await db.get(Organization, admin.organization_id) if admin.organization_id else None
        if org is None:
            org = await _upsert(
                db,
                Organization,
                {
                    "id": ORG_ID,
                    "name": "Demo Regie SwissBuilding",
                    "type": "property_management",
                    "address": "Rue Centrale 12",
                    "postal_code": "1003",
                    "city": "Lausanne",
                    "canton": "VD",
                    "email": "demo.regie@swissbuildingos.ch",
                    "phone": "+41 21 555 10 10",
                },
            )
            admin.organization_id = org.id
        await db.flush()

    diagnostician_result = await db.execute(select(User).where(User.email == "lea.girard@swissbuildingos.ch"))
    diagnostician = diagnostician_result.scalar_one_or_none()
    if diagnostician is None:
        diagnostician = await _upsert(
            db,
            User,
            {
                "id": USER_IDS["diagnostician"],
                "email": "lea.girard@swissbuildingos.ch",
                "password_hash": hash_password("diag-demo-123"),
                "first_name": "Lea",
                "last_name": "Girard",
                "role": "diagnostician",
                "organization_id": admin.organization_id,
                "language": "fr",
                "is_active": True,
            },
        )
    else:
        diagnostician.organization_id = admin.organization_id
        diagnostician.is_active = True
        await db.flush()

    org = await db.get(Organization, admin.organization_id)
    assert org is not None
    return admin, diagnostician, org


async def _seed_building_core(
    db: AsyncSession,
    *,
    admin: User,
    diagnostician: User,
    org: Organization,
) -> Building:
    building = await _upsert(
        db,
        Building,
        {
            "id": BUILDING_ID,
            "egid": 9876543,
            "egrid": "CH410000000001",
            "official_id": "VD-LSN-DEMO-OPS-01",
            "address": "Avenue des Alpes 18",
            "postal_code": "1006",
            "city": "Lausanne",
            "canton": "VD",
            "municipality_ofs": 5586,
            "latitude": 46.5158,
            "longitude": 6.6323,
            "parcel_number": "1247",
            "construction_year": 1967,
            "renovation_year": 2008,
            "building_type": "mixed",
            "floors_above": 5,
            "floors_below": 1,
            "surface_area_m2": 1840.0,
            "volume_m3": 6320.0,
            "created_by": admin.id,
            "owner_id": admin.id,
            "status": "active",
            "source_dataset": "demo-workspace",
            "source_metadata_json": {
                "seed": "seed_demo_workspace",
                "profile": "property_management_ops",
            },
            "organization_id": org.id,
        },
    )

    contacts = [
        {
            "id": CONTACT_IDS["owner_primary"],
            "organization_id": org.id,
            "contact_type": "person",
            "name": "Pierre Favre",
            "email": "demo.owner.favre@swissbuildingos.ch",
            "phone": "+41 79 555 01 01",
            "address": "Chemin du Lac 4",
            "postal_code": "1009",
            "city": "Pully",
            "canton": "VD",
            "notes": "Coproprietaire principal, prefere validation e-mail.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTACT_IDS["owner_co"],
            "organization_id": org.id,
            "contact_type": "company",
            "name": "Lakeview Patrimoine SA",
            "company_name": "Lakeview Patrimoine SA",
            "email": "demo.owner.lakeview@swissbuildingos.ch",
            "phone": "+41 22 555 02 02",
            "address": "Rue du Rhone 55",
            "postal_code": "1204",
            "city": "Geneve",
            "canton": "GE",
            "notes": "Coproprietaire financier, suit les dossiers trimestriels.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTACT_IDS["tenant_pharmacy"],
            "organization_id": org.id,
            "contact_type": "company",
            "name": "Pharmacie de Montchoisi SA",
            "company_name": "Pharmacie de Montchoisi SA",
            "email": "demo.tenant.pharma@swissbuildingos.ch",
            "phone": "+41 21 555 03 03",
            "city": "Lausanne",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "declared",
        },
        {
            "id": CONTACT_IDS["tenant_clinic"],
            "organization_id": org.id,
            "contact_type": "company",
            "name": "Cabinet Physio Lac",
            "company_name": "Cabinet Physio Lac",
            "email": "demo.tenant.physio@swissbuildingos.ch",
            "phone": "+41 21 555 03 04",
            "city": "Lausanne",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "declared",
        },
        {
            "id": CONTACT_IDS["tenant_flat"],
            "organization_id": org.id,
            "contact_type": "person",
            "name": "Camille Rochat",
            "email": "demo.tenant.rochat@swissbuildingos.ch",
            "phone": "+41 79 555 03 05",
            "city": "Lausanne",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "declared",
        },
        {
            "id": CONTACT_IDS["vendor_heating"],
            "organization_id": org.id,
            "contact_type": "supplier",
            "name": "ThermoFlux Services SA",
            "company_name": "ThermoFlux Services SA",
            "email": "demo.vendor.heating@swissbuildingos.ch",
            "phone": "+41 21 555 04 01",
            "city": "Renens",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTACT_IDS["vendor_cleaning"],
            "organization_id": org.id,
            "contact_type": "supplier",
            "name": "NetImmo Proprete SARL",
            "company_name": "NetImmo Proprete SARL",
            "email": "demo.vendor.cleaning@swissbuildingos.ch",
            "phone": "+41 21 555 04 02",
            "city": "Prilly",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTACT_IDS["vendor_elevator"],
            "organization_id": org.id,
            "contact_type": "supplier",
            "name": "Ascenseurs Romands SA",
            "company_name": "Ascenseurs Romands SA",
            "email": "demo.vendor.elevator@swissbuildingos.ch",
            "phone": "+41 21 555 04 03",
            "city": "Lausanne",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTACT_IDS["vendor_insurer"],
            "organization_id": org.id,
            "contact_type": "insurer",
            "name": "Helvetia Immo Lausanne",
            "company_name": "Helvetia Immo Lausanne",
            "email": "demo.vendor.insurer@swissbuildingos.ch",
            "phone": "+41 21 555 04 04",
            "city": "Lausanne",
            "canton": "VD",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
    ]
    for contact in contacts:
        await _upsert(db, Contact, contact)

    zones = [
        {
            "id": ZONE_IDS["basement"],
            "building_id": building.id,
            "parent_zone_id": None,
            "zone_type": "basement",
            "name": "Sous-sol technique",
            "description": "Locaux techniques et gaines.",
            "floor_number": -1,
            "surface_area_m2": 260.0,
            "usage_type": "technical",
            "created_by": admin.id,
        },
        {
            "id": ZONE_IDS["ground_floor"],
            "building_id": building.id,
            "parent_zone_id": None,
            "zone_type": "floor",
            "name": "Rez-de-chaussee commerces",
            "description": "Pharmacie et cabinet de soins.",
            "floor_number": 0,
            "surface_area_m2": 420.0,
            "usage_type": "commercial",
            "created_by": admin.id,
        },
        {
            "id": ZONE_IDS["first_floor"],
            "building_id": building.id,
            "parent_zone_id": None,
            "zone_type": "floor",
            "name": "1er etage logements",
            "description": "Plateau residentiel.",
            "floor_number": 1,
            "surface_area_m2": 360.0,
            "usage_type": "residential",
            "created_by": admin.id,
        },
        {
            "id": ZONE_IDS["roof"],
            "building_id": building.id,
            "parent_zone_id": None,
            "zone_type": "roof",
            "name": "Toiture terrasse",
            "description": "Toiture bitumineuse avec lanterneaux.",
            "floor_number": 5,
            "surface_area_m2": 310.0,
            "usage_type": "common",
            "created_by": admin.id,
        },
        {
            "id": ZONE_IDS["technical_room"],
            "building_id": building.id,
            "parent_zone_id": ZONE_IDS["basement"],
            "zone_type": "technical_room",
            "name": "Chaufferie",
            "description": "Chaufferie et conduite montante.",
            "floor_number": -1,
            "surface_area_m2": 42.0,
            "usage_type": "technical",
            "created_by": admin.id,
        },
        {
            "id": ZONE_IDS["flat_201"],
            "building_id": building.id,
            "parent_zone_id": ZONE_IDS["first_floor"],
            "zone_type": "room",
            "name": "Appartement 201",
            "description": "Appartement 3.5 pieces.",
            "floor_number": 1,
            "surface_area_m2": 88.0,
            "usage_type": "residential",
            "created_by": admin.id,
        },
    ]
    for zone in zones:
        await _upsert(db, Zone, zone)

    units = [
        {
            "id": UNIT_IDS["pharmacy"],
            "building_id": building.id,
            "unit_type": "commercial",
            "reference_code": "COM-RDC-A",
            "name": "Pharmacie RDC",
            "floor": 0,
            "surface_m2": 145.0,
            "rooms": 4.0,
            "status": "active",
            "notes": "Commerce d'angle avec reserve.",
            "created_by": admin.id,
        },
        {
            "id": UNIT_IDS["clinic"],
            "building_id": building.id,
            "unit_type": "commercial",
            "reference_code": "COM-RDC-B",
            "name": "Cabinet Physio",
            "floor": 0,
            "surface_m2": 92.0,
            "rooms": 3.0,
            "status": "active",
            "notes": "Local professionnel avec salle de soins.",
            "created_by": admin.id,
        },
        {
            "id": UNIT_IDS["flat_201"],
            "building_id": building.id,
            "unit_type": "residential",
            "reference_code": "APT-201",
            "name": "Appartement 201",
            "floor": 1,
            "surface_m2": 88.0,
            "rooms": 3.5,
            "status": "active",
            "notes": "Bail principal 3.5 pieces.",
            "created_by": admin.id,
        },
    ]
    for unit in units:
        await _upsert(db, Unit, unit)

    unit_zones = [
        {
            "id": UNIT_ZONE_IDS["pharmacy-ground"],
            "unit_id": UNIT_IDS["pharmacy"],
            "zone_id": ZONE_IDS["ground_floor"],
        },
        {
            "id": UNIT_ZONE_IDS["clinic-ground"],
            "unit_id": UNIT_IDS["clinic"],
            "zone_id": ZONE_IDS["ground_floor"],
        },
        {
            "id": UNIT_ZONE_IDS["flat-201-zone"],
            "unit_id": UNIT_IDS["flat_201"],
            "zone_id": ZONE_IDS["flat_201"],
        },
    ]
    for unit_zone in unit_zones:
        await _upsert(db, UnitZone, unit_zone)

    diagnostic = await _upsert(
        db,
        Diagnostic,
        {
            "id": DIAGNOSTIC_ID,
            "building_id": building.id,
            "diagnostic_type": "full",
            "diagnostic_context": "AvT",
            "status": "validated",
            "diagnostician_id": diagnostician.id,
            "laboratory": "Labo Analytica SA",
            "laboratory_report_number": "LA-OPS-2026-031",
            "date_inspection": date(2026, 1, 18),
            "date_report": date(2026, 1, 26),
            "report_file_path": "demo/workspace/rapport-polluants-ops.pdf",
            "summary": (
                "Diagnostic complet avant travaux sur immeuble mixte. "
                "Amiante positif sur calorifugeage, PCB traces sur toiture, plomb sur sols PVC anciens."
            ),
            "conclusion": "positive",
            "methodology": "Inspection intrusive ciblee + laboratoire accredite ISO 17025",
            "suva_notification_required": True,
            "suva_notification_date": date(2026, 2, 2),
            "canton_notification_date": date(2026, 2, 5),
        },
    )

    samples = [
        {
            "id": SAMPLE_IDS["asbestos"],
            "diagnostic_id": diagnostic.id,
            "sample_number": "OPS-001",
            "location_floor": "Sous-sol",
            "location_room": "Chaufferie",
            "location_detail": "Calorifugeage sur conduite aller-retour",
            "material_category": "piping",
            "material_description": "Calorifugeage fibreux blanc casse",
            "material_state": "degraded",
            "pollutant_type": "asbestos",
            "pollutant_subtype": "chrysotile",
            "concentration": 18.0,
            "unit": SAMPLE_UNIT_PERCENT_WEIGHT,
            "threshold_exceeded": True,
            "risk_level": "high",
            "cfst_work_category": "major",
            "action_required": "Retrait sous confinement",
            "waste_disposal_type": "special",
            "notes": "Fort risque avant travaux de chauffage.",
        },
        {
            "id": SAMPLE_IDS["pcb"],
            "diagnostic_id": diagnostic.id,
            "sample_number": "OPS-002",
            "location_floor": "Toiture",
            "location_room": "Toiture terrasse",
            "location_detail": "Membrane d'etancheite en pied d'acrotere",
            "material_category": "roofing",
            "material_description": "Membrane bitumineuse ancienne",
            "material_state": "intact",
            "pollutant_type": "pcb",
            "concentration": 68.0,
            "unit": SAMPLE_UNIT_MG_PER_KG,
            "threshold_exceeded": True,
            "risk_level": "medium",
            "action_required": "Depose selective lors de refection",
            "waste_disposal_type": "type_e",
            "notes": "A traiter pendant l'assainissement de toiture.",
        },
        {
            "id": SAMPLE_IDS["lead"],
            "diagnostic_id": diagnostic.id,
            "sample_number": "OPS-003",
            "location_floor": "1er etage",
            "location_room": "Appartement 201",
            "location_detail": "Lames PVC sous revetement flottant",
            "material_category": "flooring",
            "material_description": "Dalles PVC vertes 1960s",
            "material_state": "fair",
            "pollutant_type": "lead",
            "concentration": 1220.0,
            "unit": SAMPLE_UNIT_MG_PER_KG,
            "threshold_exceeded": True,
            "risk_level": "medium",
            "action_required": "Depose avec filiere adaptee",
            "waste_disposal_type": "controlled",
            "notes": "Concentration elevee mais materiau peu friable.",
        },
        {
            "id": SAMPLE_IDS["radon"],
            "diagnostic_id": diagnostic.id,
            "sample_number": "OPS-004",
            "location_floor": "Sous-sol",
            "location_room": "Sous-sol technique",
            "location_detail": "Mesure passive 90 jours",
            "material_category": "air",
            "material_description": "Dosimetre radon",
            "material_state": "intact",
            "pollutant_type": "radon",
            "concentration": 290.0,
            "unit": SAMPLE_UNIT_BQ_PER_M3,
            "threshold_exceeded": False,
            "risk_level": "low",
            "notes": "Valeur sous seuil mais a suivre si travaux d'etancheite.",
        },
    ]
    for sample in samples:
        await _upsert(db, Sample, sample)

    elements = [
        {
            "id": ELEMENT_IDS["basement_pipe"],
            "zone_id": ZONE_IDS["technical_room"],
            "element_type": "pipe",
            "name": "Conduite aller chauffage",
            "description": "Conduite acier DN80 calorifugee.",
            "condition": "poor",
            "installation_year": 1967,
            "created_by": admin.id,
        },
        {
            "id": ELEMENT_IDS["roof_insulation"],
            "zone_id": ZONE_IDS["roof"],
            "element_type": "insulation",
            "name": "Complexe toiture terrasse",
            "description": "Couche bitumineuse et isolation existante.",
            "condition": "fair",
            "installation_year": 1984,
            "created_by": admin.id,
        },
        {
            "id": ELEMENT_IDS["flat_flooring"],
            "zone_id": ZONE_IDS["flat_201"],
            "element_type": "floor",
            "name": "Sol sejour appartement 201",
            "description": "Sous-couche ancienne sous parquet flottant.",
            "condition": "fair",
            "installation_year": 1967,
            "created_by": admin.id,
        },
    ]
    for element in elements:
        await _upsert(db, BuildingElement, element)

    materials = [
        {
            "id": MATERIAL_IDS["pipe_wrap"],
            "element_id": ELEMENT_IDS["basement_pipe"],
            "material_type": "insulation_material",
            "name": "Calorifugeage amiante chauffage",
            "description": "Isolation fibreuse ancienne",
            "installation_year": 1967,
            "contains_pollutant": True,
            "pollutant_type": "asbestos",
            "pollutant_confirmed": True,
            "sample_id": SAMPLE_IDS["asbestos"],
            "source": "diagnostic",
            "notes": "Priorite haute avant intervention CVC.",
            "created_by": admin.id,
        },
        {
            "id": MATERIAL_IDS["roof_bitumen"],
            "element_id": ELEMENT_IDS["roof_insulation"],
            "material_type": "bitumen",
            "name": "Membrane toiture bitumineuse",
            "description": "Etancheite ancienne autour des acroteres.",
            "installation_year": 1984,
            "contains_pollutant": True,
            "pollutant_type": "pcb",
            "pollutant_confirmed": True,
            "sample_id": SAMPLE_IDS["pcb"],
            "source": "diagnostic",
            "notes": "Traitement programme pendant refection.",
            "created_by": admin.id,
        },
        {
            "id": MATERIAL_IDS["vinyl_floor"],
            "element_id": ELEMENT_IDS["flat_flooring"],
            "material_type": "flooring",
            "name": "Dalles PVC sejour",
            "description": "Dalles anciennes sous revetement flottant.",
            "installation_year": 1967,
            "contains_pollutant": True,
            "pollutant_type": "lead",
            "pollutant_confirmed": True,
            "sample_id": SAMPLE_IDS["lead"],
            "source": "diagnostic",
            "notes": "Depose selective avant relocation.",
            "created_by": admin.id,
        },
    ]
    for material in materials:
        await _upsert(db, Material, material)

    return building


async def _seed_workspace_operations(
    db: AsyncSession,
    *,
    admin: User,
    diagnostician: User,
    building: Building,
) -> None:
    documents = [
        {
            "id": DOCUMENT_IDS["diagnostic_report"],
            "building_id": building.id,
            "file_path": "demo/workspace/rapport-polluants-ops.pdf",
            "file_name": "rapport-polluants-ops.pdf",
            "file_size_bytes": 2_400_000,
            "mime_type": "application/pdf",
            "document_type": "diagnostic_report",
            "description": "Rapport complet de diagnostic avant travaux.",
            "uploaded_by": diagnostician.id,
        },
        {
            "id": DOCUMENT_IDS["ownership_extract"],
            "building_id": building.id,
            "file_path": "demo/workspace/extrait-registre-foncier.pdf",
            "file_name": "extrait-registre-foncier.pdf",
            "file_size_bytes": 680_000,
            "mime_type": "application/pdf",
            "document_type": "ownership_extract",
            "description": "Extrait foncier consolide pour copropriete.",
            "uploaded_by": admin.id,
        },
        {
            "id": DOCUMENT_IDS["lease_flat"],
            "building_id": building.id,
            "file_path": "demo/workspace/bail-appartement-201.pdf",
            "file_name": "bail-appartement-201.pdf",
            "file_size_bytes": 820_000,
            "mime_type": "application/pdf",
            "document_type": "lease_contract",
            "description": "Bail principal appartement 201.",
            "uploaded_by": admin.id,
        },
        {
            "id": DOCUMENT_IDS["service_contract"],
            "building_id": building.id,
            "file_path": "demo/workspace/contrat-thermoflux.pdf",
            "file_name": "contrat-thermoflux.pdf",
            "file_size_bytes": 550_000,
            "mime_type": "application/pdf",
            "document_type": "service_contract",
            "description": "Contrat d'entretien chauffage annuel.",
            "uploaded_by": admin.id,
        },
        {
            "id": DOCUMENT_IDS["insurance_certificate"],
            "building_id": building.id,
            "file_path": "demo/workspace/attestation-assurance-immeuble.pdf",
            "file_name": "attestation-assurance-immeuble.pdf",
            "file_size_bytes": 490_000,
            "mime_type": "application/pdf",
            "document_type": "insurance_policy",
            "description": "Attestation assurance immeuble et RC proprietaire.",
            "uploaded_by": admin.id,
        },
        {
            "id": DOCUMENT_IDS["suva_notice"],
            "building_id": building.id,
            "file_path": "demo/workspace/notification-suva-2026.pdf",
            "file_name": "notification-suva-2026.pdf",
            "file_size_bytes": 420_000,
            "mime_type": "application/pdf",
            "document_type": "suva_notification",
            "description": "Notification SUVA pre-travaux de retrait amiante.",
            "uploaded_by": admin.id,
        },
    ]
    for document in documents:
        await _upsert(db, Document, document)

    ownership_records = [
        {
            "id": OWNERSHIP_IDS["favre"],
            "building_id": building.id,
            "owner_type": "contact",
            "owner_id": CONTACT_IDS["owner_primary"],
            "share_pct": 65.0,
            "ownership_type": "co_ownership",
            "acquisition_type": "purchase",
            "acquisition_date": date(2012, 6, 1),
            "acquisition_price_chf": 1_450_000.0,
            "land_register_ref": "VD-LSN-2012-98451",
            "status": "active",
            "document_id": DOCUMENT_IDS["ownership_extract"],
            "notes": "Representant principal du dossier.",
            "created_by": admin.id,
            "source_type": "official",
            "confidence": "verified",
        },
        {
            "id": OWNERSHIP_IDS["lakeview"],
            "building_id": building.id,
            "owner_type": "contact",
            "owner_id": CONTACT_IDS["owner_co"],
            "share_pct": 35.0,
            "ownership_type": "co_ownership",
            "acquisition_type": "purchase",
            "acquisition_date": date(2012, 6, 1),
            "acquisition_price_chf": 780_000.0,
            "land_register_ref": "VD-LSN-2012-98452",
            "status": "active",
            "document_id": DOCUMENT_IDS["ownership_extract"],
            "notes": "Participation financiere minoritaire.",
            "created_by": admin.id,
            "source_type": "official",
            "confidence": "verified",
        },
    ]
    for record in ownership_records:
        await _upsert(db, OwnershipRecord, record)

    leases = [
        {
            "id": LEASE_IDS["pharmacy"],
            "building_id": building.id,
            "unit_id": UNIT_IDS["pharmacy"],
            "zone_id": ZONE_IDS["ground_floor"],
            "lease_type": "commercial",
            "reference_code": "LEASE-PHARMA-01",
            "tenant_type": "contact",
            "tenant_id": CONTACT_IDS["tenant_pharmacy"],
            "date_start": date(2023, 7, 1),
            "date_end": date(2030, 6, 30),
            "notice_period_months": 12,
            "rent_monthly_chf": 4_200.0,
            "charges_monthly_chf": 680.0,
            "deposit_chf": 12_600.0,
            "surface_m2": 145.0,
            "rooms": 4.0,
            "status": "active",
            "notes": "Bail commercial indexe ICC.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": LEASE_IDS["clinic"],
            "building_id": building.id,
            "unit_id": UNIT_IDS["clinic"],
            "zone_id": ZONE_IDS["ground_floor"],
            "lease_type": "commercial",
            "reference_code": "LEASE-PHYSIO-01",
            "tenant_type": "contact",
            "tenant_id": CONTACT_IDS["tenant_clinic"],
            "date_start": date(2024, 3, 1),
            "date_end": date(2029, 2, 28),
            "notice_period_months": 6,
            "rent_monthly_chf": 2_950.0,
            "charges_monthly_chf": 430.0,
            "deposit_chf": 8_850.0,
            "surface_m2": 92.0,
            "rooms": 3.0,
            "status": "active",
            "notes": "Bail professionnel avec clause accessibilite.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": LEASE_IDS["flat"],
            "building_id": building.id,
            "unit_id": UNIT_IDS["flat_201"],
            "zone_id": ZONE_IDS["flat_201"],
            "lease_type": "residential",
            "reference_code": "LEASE-APT-201",
            "tenant_type": "contact",
            "tenant_id": CONTACT_IDS["tenant_flat"],
            "date_start": date(2025, 2, 1),
            "date_end": None,
            "notice_period_months": 3,
            "rent_monthly_chf": 1_980.0,
            "charges_monthly_chf": 280.0,
            "deposit_chf": 5_940.0,
            "surface_m2": 88.0,
            "rooms": 3.5,
            "status": "active",
            "notes": "Relocation apres rafraichissement leger.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
    ]
    for lease in leases:
        await _upsert(db, Lease, lease)

    contracts = [
        {
            "id": CONTRACT_IDS["heating"],
            "building_id": building.id,
            "contract_type": "heating",
            "reference_code": "CTR-HEAT-OPS-01",
            "title": "Entretien chauffage et piquet 24/7",
            "counterparty_type": "contact",
            "counterparty_id": CONTACT_IDS["vendor_heating"],
            "date_start": date(2025, 1, 1),
            "date_end": date(2027, 12, 31),
            "annual_cost_chf": 8_400.0,
            "payment_frequency": "quarterly",
            "auto_renewal": True,
            "notice_period_months": 6,
            "status": "active",
            "notes": "Inclut maintenance pre-hiver et depannage sous 4h.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTRACT_IDS["cleaning"],
            "building_id": building.id,
            "contract_type": "cleaning",
            "reference_code": "CTR-CLEAN-OPS-01",
            "title": "Nettoyage parties communes et vitrages",
            "counterparty_type": "contact",
            "counterparty_id": CONTACT_IDS["vendor_cleaning"],
            "date_start": date(2025, 4, 1),
            "date_end": date(2026, 3, 31),
            "annual_cost_chf": 6_300.0,
            "payment_frequency": "monthly",
            "auto_renewal": False,
            "notice_period_months": 3,
            "status": "active",
            "notes": "Passage 3 fois par semaine.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
        {
            "id": CONTRACT_IDS["insurance"],
            "building_id": building.id,
            "contract_type": "insurance",
            "reference_code": "CTR-INS-OPS-01",
            "title": "Police immeuble multirisque et RC proprietaire",
            "counterparty_type": "contact",
            "counterparty_id": CONTACT_IDS["vendor_insurer"],
            "date_start": date(2026, 1, 1),
            "date_end": date(2026, 12, 31),
            "annual_cost_chf": 4_950.0,
            "payment_frequency": "annual",
            "auto_renewal": True,
            "notice_period_months": 3,
            "status": "active",
            "notes": "Couvre incendie, degats d'eau et RC de base.",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "verified",
        },
    ]
    for contract in contracts:
        await _upsert(db, Contract, contract)

    await _upsert(
        db,
        InsurancePolicy,
        {
            "id": INSURANCE_POLICY_ID,
            "building_id": building.id,
            "contract_id": CONTRACT_IDS["insurance"],
            "policy_type": "building_eca",
            "policy_number": "HELV-IMMO-2026-000184",
            "insurer_name": "Helvetia Immo Lausanne",
            "insurer_contact_id": CONTACT_IDS["vendor_insurer"],
            "insured_value_chf": 4_800_000.0,
            "premium_annual_chf": 4_950.0,
            "deductible_chf": 2_500.0,
            "coverage_details_json": {
                "natural_hazard": True,
                "water_damage": True,
                "owner_liability": True,
            },
            "date_start": date(2026, 1, 1),
            "date_end": date(2026, 12, 31),
            "status": "active",
            "notes": "Police consolidee annuelle.",
            "created_by": admin.id,
            "source_type": "official",
            "confidence": "verified",
        },
    )

    artefacts = [
        {
            "id": ARTEFACT_IDS["suva_notification"],
            "building_id": building.id,
            "diagnostic_id": DIAGNOSTIC_ID,
            "document_id": DOCUMENT_IDS["suva_notice"],
            "artefact_type": "suva_notification",
            "status": "submitted",
            "title": "Notification SUVA travaux conduite amiante",
            "description": "Notification prealable pour retrait calorifugeage amiante en chaufferie.",
            "reference_number": "SUVA-OPS-2026-184",
            "authority_name": "SUVA",
            "authority_type": "federal",
            "submitted_at": datetime(2026, 2, 2, 10, 30, tzinfo=UTC),
            "acknowledged_at": datetime(2026, 2, 4, 14, 0, tzinfo=UTC),
            "legal_basis": "OTConst art. 82",
            "created_by": admin.id,
        },
        {
            "id": ARTEFACT_IDS["cantonal_notice"],
            "building_id": building.id,
            "diagnostic_id": DIAGNOSTIC_ID,
            "document_id": DOCUMENT_IDS["diagnostic_report"],
            "artefact_type": "cantonal_notification",
            "status": "submitted",
            "title": "Annonce cantonale assainissement cible",
            "description": "Declaration cantonale avant refection technique et toiture.",
            "reference_number": "VD-DIREN-2026-318",
            "authority_name": "Canton de Vaud - DIREN",
            "authority_type": "cantonal",
            "submitted_at": datetime(2026, 2, 5, 9, 15, tzinfo=UTC),
            "legal_basis": "RLATC art. 13",
            "created_by": admin.id,
        },
    ]
    for artefact in artefacts:
        await _upsert(db, ComplianceArtefact, artefact)

    interventions = [
        {
            "id": INTERVENTION_IDS["pipe_removal"],
            "building_id": building.id,
            "diagnostic_id": DIAGNOSTIC_ID,
            "contract_id": CONTRACT_IDS["heating"],
            "intervention_type": "asbestos_removal",
            "title": "Retrait calorifugeage conduite chaufferie",
            "description": "Confinement local technique, retrait du calorifugeage amiante, evacuation filiere speciale.",
            "status": "planned",
            "date_start": date(2026, 4, 14),
            "date_end": date(2026, 4, 18),
            "contractor_name": "ThermoFlux Services SA",
            "cost_chf": 38_500.0,
            "zones_affected": ["Sous-sol technique", "Chaufferie"],
            "materials_used": ["Confinement PE", "Filtre H14", "Etiquetage dechets"],
            "notes": "Coordination locataires commerces requise.",
            "created_by": admin.id,
        },
        {
            "id": INTERVENTION_IDS["roof_encapsulation"],
            "building_id": building.id,
            "diagnostic_id": DIAGNOSTIC_ID,
            "intervention_type": "renovation",
            "title": "Refection partielle toiture terrasse",
            "description": "Traitement zones PCB et reprise etancheite autour lanterneaux.",
            "status": "in_progress",
            "date_start": date(2026, 3, 3),
            "contractor_name": "Ascenseurs Romands SA",
            "cost_chf": 24_000.0,
            "zones_affected": ["Toiture terrasse"],
            "materials_used": ["Membrane neuve", "Releve etanche", "Protections"],
            "notes": "Suivi photo hebdomadaire en cours.",
            "created_by": admin.id,
        },
    ]
    for intervention in interventions:
        await _upsert(db, Intervention, intervention)

    document_links = [
        {
            "id": DOCUMENT_LINK_IDS["lease_flat"],
            "document_id": DOCUMENT_IDS["lease_flat"],
            "entity_type": "lease",
            "entity_id": LEASE_IDS["flat"],
            "link_type": "attachment",
            "created_by": admin.id,
        },
        {
            "id": DOCUMENT_LINK_IDS["service_contract"],
            "document_id": DOCUMENT_IDS["service_contract"],
            "entity_type": "contract",
            "entity_id": CONTRACT_IDS["heating"],
            "link_type": "reference",
            "created_by": admin.id,
        },
        {
            "id": DOCUMENT_LINK_IDS["insurance_certificate"],
            "document_id": DOCUMENT_IDS["insurance_certificate"],
            "entity_type": "insurance_policy",
            "entity_id": INSURANCE_POLICY_ID,
            "link_type": "certificate",
            "created_by": admin.id,
        },
        {
            "id": DOCUMENT_LINK_IDS["suva_notice"],
            "document_id": DOCUMENT_IDS["suva_notice"],
            "entity_type": "compliance_artefact",
            "entity_id": ARTEFACT_IDS["suva_notification"],
            "link_type": "proof",
            "created_by": admin.id,
        },
    ]
    for link in document_links:
        await _upsert(db, DocumentLink, link)

    financial_entries = [
        {
            "id": FINANCIAL_ENTRY_IDS["rent_flat_jan"],
            "building_id": building.id,
            "entry_type": "income",
            "category": "rent_income",
            "amount_chf": 1_980.0,
            "entry_date": date(2026, 1, 5),
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 31),
            "fiscal_year": 2026,
            "description": "Loyer appartement 201 janvier 2026",
            "lease_id": LEASE_IDS["flat"],
            "status": "recorded",
            "created_by": admin.id,
            "source_type": "import",
            "confidence": "verified",
        },
        {
            "id": FINANCIAL_ENTRY_IDS["rent_flat_feb"],
            "building_id": building.id,
            "entry_type": "income",
            "category": "rent_income",
            "amount_chf": 1_980.0,
            "entry_date": date(2026, 2, 5),
            "period_start": date(2026, 2, 1),
            "period_end": date(2026, 2, 28),
            "fiscal_year": 2026,
            "description": "Loyer appartement 201 fevrier 2026",
            "lease_id": LEASE_IDS["flat"],
            "status": "recorded",
            "created_by": admin.id,
            "source_type": "import",
            "confidence": "verified",
        },
        {
            "id": FINANCIAL_ENTRY_IDS["rent_pharmacy_jan"],
            "building_id": building.id,
            "entry_type": "income",
            "category": "rent_income",
            "amount_chf": 4_200.0,
            "entry_date": date(2026, 1, 7),
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 31),
            "fiscal_year": 2026,
            "description": "Loyer pharmacie janvier 2026",
            "lease_id": LEASE_IDS["pharmacy"],
            "status": "recorded",
            "created_by": admin.id,
            "source_type": "import",
            "confidence": "verified",
        },
        {
            "id": FINANCIAL_ENTRY_IDS["heating_service"],
            "building_id": building.id,
            "entry_type": "expense",
            "category": "heating",
            "amount_chf": 2_100.0,
            "entry_date": date(2026, 1, 15),
            "fiscal_year": 2026,
            "description": "Trimestre entretien chauffage",
            "contract_id": CONTRACT_IDS["heating"],
            "document_id": DOCUMENT_IDS["service_contract"],
            "status": "recorded",
            "created_by": admin.id,
            "source_type": "import",
            "confidence": "verified",
        },
        {
            "id": FINANCIAL_ENTRY_IDS["insurance_premium"],
            "building_id": building.id,
            "entry_type": "expense",
            "category": "insurance_premium",
            "amount_chf": 4_950.0,
            "entry_date": date(2026, 1, 20),
            "fiscal_year": 2026,
            "description": "Prime assurance annuelle immeuble",
            "contract_id": CONTRACT_IDS["insurance"],
            "insurance_policy_id": INSURANCE_POLICY_ID,
            "document_id": DOCUMENT_IDS["insurance_certificate"],
            "status": "recorded",
            "created_by": admin.id,
            "source_type": "import",
            "confidence": "verified",
        },
        {
            "id": FINANCIAL_ENTRY_IDS["intervention_deposit"],
            "building_id": building.id,
            "entry_type": "expense",
            "category": "renovation",
            "amount_chf": 9_500.0,
            "entry_date": date(2026, 3, 10),
            "fiscal_year": 2026,
            "description": "Acompte retrait calorifugeage amiante",
            "intervention_id": INTERVENTION_IDS["pipe_removal"],
            "status": "recorded",
            "created_by": admin.id,
            "source_type": "manual",
            "confidence": "declared",
        },
    ]
    for entry in financial_entries:
        await _upsert(db, FinancialEntry, entry)

    observations = [
        {
            "id": OBSERVATION_IDS["basement_pipe"],
            "building_id": building.id,
            "zone_id": ZONE_IDS["technical_room"],
            "element_id": ELEMENT_IDS["basement_pipe"],
            "observer_id": diagnostician.id,
            "observation_type": "safety_hazard",
            "severity": "major",
            "title": "Gaine de calorifugeage friable accessible",
            "description": "Surface localement degradee au droit du piquage principal.",
            "location_description": "Chaufferie, conduite sud",
            "observed_at": datetime(2026, 1, 18, 11, 20, tzinfo=UTC),
            "photo_reference": "OBS-PIPE-2026-01",
            "verified": True,
            "verified_by_id": admin.id,
            "verified_at": datetime(2026, 1, 19, 9, 5, tzinfo=UTC),
            "metadata_json": '{"ppe":"FFP3","access":"restricted"}',
            "status": "verified",
        },
        {
            "id": OBSERVATION_IDS["roof_access"],
            "building_id": building.id,
            "zone_id": ZONE_IDS["roof"],
            "element_id": ELEMENT_IDS["roof_insulation"],
            "observer_id": admin.id,
            "observation_type": "general_note",
            "severity": "minor",
            "title": "Acces toiture a baliser pendant chantier",
            "description": "Flux livreurs a separer de la zone travaux pendant refection.",
            "location_description": "Escalier technique et sortie toiture",
            "observed_at": datetime(2026, 3, 4, 8, 45, tzinfo=UTC),
            "verified": False,
            "metadata_json": '{"temporary_barrier":true}',
            "status": "draft",
        },
    ]
    for observation in observations:
        await _upsert(db, FieldObservation, observation)

    actions = [
        {
            "id": ACTION_IDS["remove_pipe"],
            "building_id": building.id,
            "diagnostic_id": DIAGNOSTIC_ID,
            "sample_id": SAMPLE_IDS["asbestos"],
            "source_type": ACTION_SOURCE_DIAGNOSTIC,
            "action_type": ACTION_TYPE_REMEDIATION,
            "title": "Planifier retrait calorifugeage amiante",
            "description": "Mandater entreprise reconnue et verrouiller la zone chaufferie.",
            "priority": ACTION_PRIORITY_CRITICAL,
            "status": ACTION_STATUS_OPEN,
            "due_date": date(2026, 4, 1),
            "assigned_to": admin.id,
            "created_by": admin.id,
            "metadata_json": {"zone": "chaufferie", "sample_number": "OPS-001"},
        },
        {
            "id": ACTION_IDS["notify_suva"],
            "building_id": building.id,
            "diagnostic_id": DIAGNOSTIC_ID,
            "source_type": ACTION_SOURCE_COMPLIANCE,
            "action_type": ACTION_TYPE_NOTIFY_SUVA,
            "title": "Suivre accuse SUVA et planning travaux",
            "description": "Confirmer les dates et conserver l'accuse dans le dossier.",
            "priority": ACTION_PRIORITY_HIGH,
            "status": ACTION_STATUS_IN_PROGRESS,
            "due_date": date(2026, 3, 28),
            "assigned_to": admin.id,
            "created_by": admin.id,
            "metadata_json": {"artefact_id": str(ARTEFACT_IDS["suva_notification"])},
        },
        {
            "id": ACTION_IDS["consolidate_docs"],
            "building_id": building.id,
            "source_type": ACTION_SOURCE_MANUAL,
            "action_type": ACTION_TYPE_DOCUMENTATION,
            "title": "Consolider contrats et bail principal dans le coffre",
            "description": "Toutes les pieces contractuelles critiques sont maintenant reliees au batiment.",
            "priority": ACTION_PRIORITY_MEDIUM,
            "status": ACTION_STATUS_DONE,
            "due_date": date(2026, 2, 15),
            "assigned_to": admin.id,
            "created_by": admin.id,
            "metadata_json": {"docs_linked": 4},
            "completed_at": datetime(2026, 2, 14, 16, 20, tzinfo=UTC),
        },
    ]
    for action in actions:
        await _upsert(db, ActionItem, action)

    events = [
        {
            "id": EVENT_IDS["construction"],
            "building_id": building.id,
            "event_type": "construction",
            "date": date(1967, 1, 1),
            "title": "Construction de l'immeuble mixte",
            "description": "Immeuble construit en structure beton avec commerces au RDC.",
            "created_by": admin.id,
            "metadata_json": {"source": "seed_demo_workspace"},
        },
        {
            "id": EVENT_IDS["diagnostic_report"],
            "building_id": building.id,
            "event_type": "diagnostic",
            "date": date(2026, 1, 26),
            "title": "Rapport polluants valide",
            "description": "Rapport complet recu et valide par la regie.",
            "created_by": diagnostician.id,
            "metadata_json": {"diagnostic_id": str(DIAGNOSTIC_ID)},
        },
        {
            "id": EVENT_IDS["lease_renewal"],
            "building_id": building.id,
            "event_type": "lease",
            "date": date(2025, 2, 1),
            "title": "Entree locataire appartement 201",
            "description": "Nouveau bail residentiel signe avec Camille Rochat.",
            "created_by": admin.id,
            "metadata_json": {"lease_id": str(LEASE_IDS["flat"])},
        },
        {
            "id": EVENT_IDS["remediation_mobilization"],
            "building_id": building.id,
            "event_type": "intervention",
            "date": date(2026, 3, 3),
            "title": "Mobilisation chantier toiture",
            "description": "Debut de la refection partielle et mise en securite acces toiture.",
            "created_by": admin.id,
            "metadata_json": {"intervention_id": str(INTERVENTION_IDS["roof_encapsulation"])},
        },
    ]
    for event in events:
        await _upsert(db, Event, event)

    assignments = [
        {
            "id": ASSIGNMENT_IDS["building_owner"],
            "target_type": "building",
            "target_id": building.id,
            "user_id": admin.id,
            "role": "responsible",
            "created_by": admin.id,
        },
        {
            "id": ASSIGNMENT_IDS["building_diagnostician"],
            "target_type": "building",
            "target_id": building.id,
            "user_id": diagnostician.id,
            "role": "diagnostician",
            "created_by": admin.id,
        },
        {
            "id": ASSIGNMENT_IDS["diagnostic_reviewer"],
            "target_type": "diagnostic",
            "target_id": DIAGNOSTIC_ID,
            "user_id": admin.id,
            "role": "reviewer",
            "created_by": admin.id,
        },
    ]
    for assignment in assignments:
        await _upsert(db, Assignment, assignment)


async def seed_demo_workspace(db: AsyncSession) -> dict[str, Any]:
    admin, diagnostician, org = await _ensure_demo_users(db)
    building = await _seed_building_core(db, admin=admin, diagnostician=diagnostician, org=org)
    await _seed_workspace_operations(db, admin=admin, diagnostician=diagnostician, building=building)
    await db.commit()

    summary = {
        "status": "completed",
        "building_id": str(building.id),
        "building_address": building.address,
        "organization_id": str(org.id),
        "contacts_count": len(CONTACT_IDS),
        "zones_count": len(ZONE_IDS),
        "units_count": len(UNIT_IDS),
        "ownership_count": len(OWNERSHIP_IDS),
        "leases_count": len(LEASE_IDS),
        "contracts_count": len(CONTRACT_IDS),
        "documents_count": len(DOCUMENT_IDS),
        "artefacts_count": len(ARTEFACT_IDS),
        "samples_count": len(SAMPLE_IDS),
        "materials_count": len(MATERIAL_IDS),
        "interventions_count": len(INTERVENTION_IDS),
        "observations_count": len(OBSERVATION_IDS),
        "actions_count": len(ACTION_IDS),
        "events_count": len(EVENT_IDS),
    }
    logger.info("Demo workspace seed complete: %s", summary)
    return summary


if __name__ == "__main__":
    import asyncio

    from app.database import AsyncSessionLocal

    async def main() -> None:
        async with AsyncSessionLocal() as db:
            result = await seed_demo_workspace(db)
            print(result)

    asyncio.run(main())
