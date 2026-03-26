"""Tests for seed_demo_workspace.py — rich demo workspace seeding."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.compliance_artefact import ComplianceArtefact
from app.models.contact import Contact
from app.models.contract import Contract
from app.models.diagnostic import Diagnostic
from app.models.document import Document
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
from app.models.user import User
from app.models.zone import Zone
from app.seeds.seed_demo_workspace import BUILDING_ID, DIAGNOSTIC_ID, seed_demo_workspace


async def test_seed_demo_workspace_creates_rich_workspace(db_session):
    result = await seed_demo_workspace(db_session)

    assert result["status"] == "completed"
    assert result["building_id"]
    assert result["contacts_count"] >= 9
    assert result["leases_count"] == 3
    assert result["contracts_count"] == 3
    assert result["documents_count"] == 6
    assert result["samples_count"] == 4
    assert result["actions_count"] == 3

    building = await db_session.get(Building, BUILDING_ID)
    assert building is not None
    assert building.organization_id is not None
    assert building.egid == 9876543
    assert building.egrid == "CH410000000001"

    diagnostic = await db_session.get(Diagnostic, DIAGNOSTIC_ID)
    assert diagnostic is not None
    assert diagnostic.status == "validated"
    assert diagnostic.suva_notification_required is True


async def test_seed_demo_workspace_links_operational_records(db_session):
    await seed_demo_workspace(db_session)

    building = await db_session.get(Building, BUILDING_ID)
    assert building is not None

    org = await db_session.get(Organization, building.organization_id)
    assert org is not None

    contacts = (
        (
            await db_session.execute(
                select(Contact).where(Contact.organization_id == building.organization_id),
            )
        )
        .scalars()
        .all()
    )
    assert len(contacts) >= 9

    leases = (await db_session.execute(select(Lease).where(Lease.building_id == building.id))).scalars().all()
    contracts = (await db_session.execute(select(Contract).where(Contract.building_id == building.id))).scalars().all()
    ownerships = (
        (await db_session.execute(select(OwnershipRecord).where(OwnershipRecord.building_id == building.id)))
        .scalars()
        .all()
    )
    interventions = (
        (await db_session.execute(select(Intervention).where(Intervention.building_id == building.id))).scalars().all()
    )
    observations = (
        (await db_session.execute(select(FieldObservation).where(FieldObservation.building_id == building.id)))
        .scalars()
        .all()
    )
    assert len(leases) == 3
    assert len(contracts) == 3
    assert len(ownerships) == 2
    assert len(interventions) == 2
    assert len(observations) == 2

    units = (await db_session.execute(select(Unit).where(Unit.building_id == building.id))).scalars().all()
    zones = (await db_session.execute(select(Zone).where(Zone.building_id == building.id))).scalars().all()
    elements = (
        (
            await db_session.execute(
                select(BuildingElement).where(BuildingElement.zone_id.in_([zone.id for zone in zones])),
            )
        )
        .scalars()
        .all()
    )
    materials = (
        (
            await db_session.execute(
                select(Material).where(Material.element_id.in_([element.id for element in elements])),
            )
        )
        .scalars()
        .all()
    )
    assert len(units) == 3
    assert len(zones) == 6
    assert len(elements) == 3
    assert len(materials) == 3

    documents = (await db_session.execute(select(Document).where(Document.building_id == building.id))).scalars().all()
    artefacts = (
        (await db_session.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building.id)))
        .scalars()
        .all()
    )
    policies = (
        (await db_session.execute(select(InsurancePolicy).where(InsurancePolicy.building_id == building.id)))
        .scalars()
        .all()
    )
    finance_entries = (
        (await db_session.execute(select(FinancialEntry).where(FinancialEntry.building_id == building.id)))
        .scalars()
        .all()
    )
    actions = (
        (await db_session.execute(select(ActionItem).where(ActionItem.building_id == building.id))).scalars().all()
    )
    assignments = (
        (await db_session.execute(select(Assignment).where(Assignment.target_id.in_([building.id, DIAGNOSTIC_ID]))))
        .scalars()
        .all()
    )
    samples = (await db_session.execute(select(Sample).where(Sample.diagnostic_id == DIAGNOSTIC_ID))).scalars().all()

    assert len(documents) == 6
    assert len(artefacts) == 2
    assert len(policies) == 1
    assert len(finance_entries) == 6
    assert len(actions) == 3
    assert len(assignments) == 3
    assert {sample.pollutant_type for sample in samples} == {"asbestos", "pcb", "lead", "radon"}


async def test_seed_demo_workspace_is_idempotent(db_session):
    first = await seed_demo_workspace(db_session)
    second = await seed_demo_workspace(db_session)

    assert first["building_id"] == second["building_id"]

    count_expectations = {
        Building: 1,
        Diagnostic: 1,
        Contact: 9,
        Zone: 6,
        Unit: 3,
        OwnershipRecord: 2,
        Lease: 3,
        Contract: 3,
        InsurancePolicy: 1,
        Document: 6,
        ComplianceArtefact: 2,
        Sample: 4,
        BuildingElement: 3,
        Material: 3,
        Intervention: 2,
        FieldObservation: 2,
        FinancialEntry: 6,
        ActionItem: 3,
        Assignment: 3,
        User: 2,
    }

    for model, expected in count_expectations.items():
        result = await db_session.execute(select(func.count()).select_from(model))
        assert result.scalar() == expected, model.__name__
