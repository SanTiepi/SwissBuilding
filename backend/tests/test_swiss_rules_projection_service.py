from __future__ import annotations

from app.schemas.swiss_rules import BuildingContext, ProjectContext
from app.services.swiss_rules_projection_service import build_projection_bundle
from app.services.swiss_rules_spine_service import build_core_swiss_rules_enablement_pack, evaluate_enablement_pack


def test_projection_bundle_for_vd_asbestos_project():
    pack = build_core_swiss_rules_enablement_pack()
    evaluations = evaluate_enablement_pack(
        pack,
        BuildingContext(canton="VD"),
        ProjectContext(
            project_kind="renovation",
            pollutants_detected=["asbestos", "pcb"],
            waste_categories=["special"],
            requires_permit=True,
            touches_structure=True,
        ),
    )

    bundle = build_projection_bundle(pack, evaluations)

    procedure_codes = {procedure.procedure_code for procedure in bundle.procedures}
    requirement_codes = {obligation.requirement_code for obligation in bundle.obligations}
    action_types = {action.action_type for action in bundle.actions}

    assert "vd_camac_permit" in procedure_codes
    assert "suva_asbestos_notification" in procedure_codes
    assert "asbestos_diagnostic" in requirement_codes
    assert "suva_notification_requirement" in requirement_codes
    assert "procedural_blocker" not in action_types
    assert "regulatory_filing" in action_types
    assert "procedure_start" in action_types


def test_projection_bundle_marks_manual_review_as_procedural_blocker():
    pack = build_core_swiss_rules_enablement_pack()
    evaluations = evaluate_enablement_pack(
        pack,
        BuildingContext(canton="GE", outside_building_zone=True, protected_building=True),
        ProjectContext(
            project_kind="transformation",
            requires_permit=True,
            touches_structure=True,
        ),
    )

    bundle = build_projection_bundle(pack, evaluations)

    blocker_actions = [action for action in bundle.actions if action.action_type == "procedural_blocker"]
    assert blocker_actions
    assert any(action.manual_review for action in blocker_actions)
    assert any(action.priority_bucket == "critical" for action in blocker_actions)


def test_projection_bundle_routes_waste_requirements_to_contractor():
    pack = build_core_swiss_rules_enablement_pack()
    evaluations = evaluate_enablement_pack(
        pack,
        BuildingContext(canton="FR"),
        ProjectContext(
            project_kind="demolition",
            pollutants_detected=["hap"],
            waste_categories=["type_e"],
            requires_permit=True,
            involves_demolition=True,
        ),
    )

    bundle = build_projection_bundle(pack, evaluations)

    waste_requirements = [item for item in bundle.obligations if item.requirement_code == "waste_manifest_requirement"]
    assert waste_requirements
    assert waste_requirements[0].responsible_role == "contractor"
    assert waste_requirements[0].integration_target == "regulatory_filing"
