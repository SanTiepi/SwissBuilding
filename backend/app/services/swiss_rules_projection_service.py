"""Projection helpers from SwissRules evaluations to existing product anchors."""

from __future__ import annotations

from app.schemas.swiss_rules import (
    ApplicabilityEvaluation,
    ApplicabilityStatus,
    ProcedureTemplate,
    RequirementTemplate,
    RuleTemplate,
    SwissRulesEnablementPack,
)
from app.schemas.swiss_rules_projection import (
    ControlTowerActionCandidate,
    ObligationCandidate,
    ProcedureCandidate,
    ProjectionBundle,
)


def _rule_index(pack: SwissRulesEnablementPack) -> dict[str, RuleTemplate]:
    return {rule.code: rule for rule in pack.rule_templates}


def _requirement_index(pack: SwissRulesEnablementPack) -> dict[str, RequirementTemplate]:
    return {requirement.code: requirement for requirement in pack.requirement_templates}


def _procedure_index(pack: SwissRulesEnablementPack) -> dict[str, ProcedureTemplate]:
    return {procedure.code: procedure for procedure in pack.procedure_templates}


def _priority_for_rule(rule: RuleTemplate, evaluation: ApplicabilityEvaluation) -> str:
    if evaluation.status == ApplicabilityStatus.MANUAL_REVIEW:
        return "critical"
    if "notification" in rule.domain_tags or "permit" in rule.domain_tags or "manual_review" in rule.domain_tags:
        return "high"
    if "waste" in rule.domain_tags or "fire" in rule.domain_tags or "radon" in rule.domain_tags:
        return "medium"
    return "medium"


def _action_type_for_rule(rule: RuleTemplate, evaluation: ApplicabilityEvaluation) -> str:
    if evaluation.status == ApplicabilityStatus.MANUAL_REVIEW:
        return "procedural_blocker"
    if "notification" in rule.domain_tags or "declaration" in rule.domain_tags:
        return "regulatory_filing"
    if "permit" in rule.domain_tags:
        return "procedure_start"
    if "waste" in rule.domain_tags:
        return "waste_compliance"
    return "evidence_gap"


def project_procedure_candidates(
    pack: SwissRulesEnablementPack,
    evaluations: list[ApplicabilityEvaluation],
) -> list[ProcedureCandidate]:
    procedures = _procedure_index(pack)
    projected: list[ProcedureCandidate] = []
    seen: set[tuple[str, str]] = set()

    for evaluation in evaluations:
        if evaluation.status == ApplicabilityStatus.NOT_APPLICABLE:
            continue
        for procedure_code in evaluation.required_procedure_codes:
            procedure = procedures.get(procedure_code)
            if procedure is None:
                continue
            key = (evaluation.rule_code, procedure_code)
            if key in seen:
                continue
            seen.add(key)
            projected.append(
                ProcedureCandidate(
                    procedure_code=procedure.code,
                    title=procedure.title,
                    summary=procedure.summary,
                    procedure_type=procedure.procedure_type,
                    authority_code=procedure.authority_code,
                    jurisdiction_code=procedure.jurisdiction_code,
                    source_rule_code=evaluation.rule_code,
                    blocking=any(step.blocking for step in procedure.steps),
                    rationale=evaluation.reasons + evaluation.manual_review_reasons,
                )
            )

    return projected


def project_obligation_candidates(
    pack: SwissRulesEnablementPack,
    evaluations: list[ApplicabilityEvaluation],
) -> list[ObligationCandidate]:
    rules = _rule_index(pack)
    requirements = _requirement_index(pack)
    projected: list[ObligationCandidate] = []
    seen: set[tuple[str, str]] = set()

    for evaluation in evaluations:
        if evaluation.status == ApplicabilityStatus.NOT_APPLICABLE:
            continue
        rule = rules[evaluation.rule_code]
        priority = _priority_for_rule(rule, evaluation)
        for requirement_code in evaluation.required_requirement_codes:
            requirement = requirements.get(requirement_code)
            if requirement is None:
                continue
            key = (evaluation.rule_code, requirement_code)
            if key in seen:
                continue
            seen.add(key)
            projected.append(
                ObligationCandidate(
                    requirement_code=requirement.code,
                    source_rule_code=evaluation.rule_code,
                    title=requirement.title,
                    description=requirement.summary,
                    obligation_type="authority_submission"
                    if requirement.integration_target in {"regulatory_filing", "authority_pack"}
                    else "regulatory_inspection",
                    priority=priority,
                    responsible_role=requirement.responsible_role,
                    due_hint=requirement.due_hint,
                    integration_target=requirement.integration_target,
                    legal_basis_source_ids=list(requirement.legal_basis_source_ids),
                )
            )

    return projected


def project_control_tower_actions(
    pack: SwissRulesEnablementPack,
    evaluations: list[ApplicabilityEvaluation],
) -> list[ControlTowerActionCandidate]:
    rules = _rule_index(pack)
    projected: list[ControlTowerActionCandidate] = []
    seen: set[str] = set()

    for evaluation in evaluations:
        if evaluation.status == ApplicabilityStatus.NOT_APPLICABLE:
            continue
        rule = rules[evaluation.rule_code]
        priority = _priority_for_rule(rule, evaluation)
        action_type = _action_type_for_rule(rule, evaluation)
        action_key = f"{evaluation.rule_code}:{action_type}"
        if action_key in seen:
            continue
        seen.add(action_key)
        projected.append(
            ControlTowerActionCandidate(
                action_key=action_key,
                source_rule_code=evaluation.rule_code,
                title=rule.title,
                description=" ".join(evaluation.reasons) if evaluation.reasons else rule.summary,
                priority_bucket=priority,
                action_type=action_type,
                responsible_role=_responsible_role_for_rule(rule, pack, evaluation),
                integration_target="control_tower",
                legal_basis_source_ids=list(rule.source_ids),
                manual_review=evaluation.status == ApplicabilityStatus.MANUAL_REVIEW,
                rationale=evaluation.reasons + evaluation.manual_review_reasons,
            )
        )

    return projected


def _responsible_role_for_rule(
    rule: RuleTemplate,
    pack: SwissRulesEnablementPack,
    evaluation: ApplicabilityEvaluation,
) -> str:
    requirements = _requirement_index(pack)
    for requirement_code in evaluation.required_requirement_codes:
        requirement = requirements.get(requirement_code)
        if requirement is not None:
            return requirement.responsible_role
    if "permit" in rule.domain_tags:
        return "property_manager"
    if "waste" in rule.domain_tags:
        return "contractor"
    return "property_manager"


def build_projection_bundle(
    pack: SwissRulesEnablementPack,
    evaluations: list[ApplicabilityEvaluation],
) -> ProjectionBundle:
    return ProjectionBundle(
        procedures=project_procedure_candidates(pack, evaluations),
        obligations=project_obligation_candidates(pack, evaluations),
        actions=project_control_tower_actions(pack, evaluations),
    )
