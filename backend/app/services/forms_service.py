"""
BatiConnect - Forms Workspace Service

Identifies applicable regulatory forms, pre-fills fields from building data,
tracks submission lifecycle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.form_instance import FormInstance, FormTemplate
from app.models.intervention import Intervention
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Source mapping resolution
# ---------------------------------------------------------------------------


def _resolve_source(source: str, context: dict) -> tuple[str | None, str]:
    """
    Resolve a source_mapping string to a value.

    Returns (value, confidence) where confidence is 'high', 'medium', or 'low'.
    """
    building: Building | None = context.get("building")
    diagnostics: list[Diagnostic] = context.get("diagnostics", [])
    samples: list[Sample] = context.get("samples", [])
    intervention: Intervention | None = context.get("intervention")
    _documents: list[Document] = context.get("documents", [])  # reserved for future document source mappings

    if source.startswith("building."):
        if building is None:
            return None, "low"
        attr = source.split(".", 1)[1]
        mapping = {
            "address": building.address,
            "city": building.city,
            "postal_code": building.postal_code,
            "canton": building.canton,
            "egid": str(building.egid) if building.egid else None,
            "egrid": building.egrid,
            "construction_year": str(building.construction_year) if building.construction_year else None,
            "building_type": building.building_type,
            "surface_area_m2": str(building.surface_area_m2) if building.surface_area_m2 else None,
            "owner": None,  # Would need owner lookup
        }
        val = mapping.get(attr)
        return val, "high" if val else "low"

    if source.startswith("diagnostic."):
        attr = source.split(".", 1)[1]
        if attr == "pollutant_types":
            types = sorted({(s.pollutant_type or "").lower() for s in samples if s.pollutant_type})
            val = ", ".join(types) if types else None
            return val, "high" if val else "low"
        if attr == "pollutant_inventory":
            inventory = []
            for s in samples:
                if s.threshold_exceeded:
                    inventory.append(f"{s.pollutant_type}: {s.concentration} {s.unit}")
            val = "; ".join(inventory) if inventory else None
            return val, "high" if val else "low"
        if attr == "references":
            refs = [str(d.id) for d in diagnostics if d.status in ("completed", "validated")]
            val = ", ".join(refs) if refs else None
            return val, "high" if val else "low"
        if attr == "has_positive_asbestos":
            positives = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
            return "Oui" if positives else "Non", "high"
        return None, "low"

    if source.startswith("intervention."):
        if intervention is None:
            return None, "low"
        attr = source.split(".", 1)[1]
        mapping = {
            "type": intervention.intervention_type,
            "scope": intervention.description,
            "start_date": str(intervention.date_start) if intervention.date_start else None,
            "end_date": str(intervention.date_end) if intervention.date_end else None,
            "contractor": intervention.contractor_name,
            "status": intervention.status,
        }
        val = mapping.get(attr)
        return val, "high" if val else "low"

    if source.startswith("waste."):
        attr = source.split(".", 1)[1]
        if attr == "types":
            types = sorted({s.waste_disposal_type for s in samples if s.waste_disposal_type and s.threshold_exceeded})
            val = ", ".join(types) if types else None
            return val, "medium" if val else "low"
        if attr == "quantities":
            return None, "low"  # Needs manual input
        if attr == "disposal_routes":
            return None, "low"
        return None, "low"

    if source == "manual":
        return None, "low"

    return None, "low"


# ---------------------------------------------------------------------------
# Applicability logic
# ---------------------------------------------------------------------------


async def get_applicable_forms(
    db: AsyncSession,
    building_id: UUID,
    intervention_type: str | None = None,
) -> list[dict]:
    """
    Determine which form templates apply to a building based on canton,
    pollutants present, and work type.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    canton = (building.canton or "").upper()

    # Load samples to check pollutant presence
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    diag_ids = [d.id for d in diagnostics]

    samples: list[Sample] = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    has_positive_asbestos = any(
        (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded for s in samples
    )
    has_any_positive = any(s.threshold_exceeded for s in samples)
    positive_pollutants = sorted({(s.pollutant_type or "").lower() for s in samples if s.threshold_exceeded})

    # Load active templates
    template_result = await db.execute(select(FormTemplate).where(FormTemplate.active.is_(True)))
    templates = list(template_result.scalars().all())

    applicable: list[dict] = []

    for tpl in templates:
        reason = _check_applicability(
            tpl,
            canton=canton,
            has_positive_asbestos=has_positive_asbestos,
            has_any_positive=has_any_positive,
            positive_pollutants=positive_pollutants,
            intervention_type=intervention_type,
        )
        if reason:
            applicable.append({"template": tpl, "reason": reason})

    return applicable


def _check_applicability(
    template: FormTemplate,
    *,
    canton: str,
    has_positive_asbestos: bool,
    has_any_positive: bool,
    positive_pollutants: list[str],
    intervention_type: str | None,
) -> str | None:
    """Return applicability reason or None if not applicable."""
    ft = template.form_type

    if ft == "suva_notification":
        if has_positive_asbestos:
            return "Amiante detecte — notification SUVA obligatoire (OTConst Art. 82-86)"
        return None

    if ft == "cantonal_declaration":
        # Cantonal forms apply if template canton matches building canton, or template has no canton (generic)
        if template.canton and template.canton.upper() != canton:
            return None
        if has_any_positive:
            return f"Polluants detectes ({', '.join(positive_pollutants)}) — declaration cantonale requise"
        return None

    if ft == "waste_plan":
        if has_any_positive:
            return "Polluants detectes — plan de gestion des dechets requis (OLED)"
        return None

    if ft == "pollutant_declaration":
        if has_any_positive:
            return f"Polluants detectes: {', '.join(positive_pollutants)}"
        return None

    if ft == "work_permit":
        if intervention_type and intervention_type in ("renovation", "demolition", "transformation"):
            return f"Travaux de type {intervention_type} prevus — permis de construire requis"
        return None

    if ft == "demolition_permit":
        if intervention_type and intervention_type in ("demolition", "demolition_partial"):
            return "Demolition prevue — permis de demolir requis"
        return None

    if ft == "insurance_declaration":
        if has_positive_asbestos:
            return "Amiante detecte — declaration d'assurance recommandee"
        return None

    if ft == "subvention_request":
        return None  # Only manual applicability

    # Generic: always applicable if canton matches or no canton
    if template.canton and template.canton.upper() != canton:
        return None
    return "Formulaire applicable selon la juridiction"


# ---------------------------------------------------------------------------
# Pre-fill
# ---------------------------------------------------------------------------


async def prefill_form(
    db: AsyncSession,
    template_id: UUID,
    building_id: UUID,
    created_by_id: UUID | None = None,
    organization_id: UUID | None = None,
    intervention_id: UUID | None = None,
) -> FormInstance:
    """Create a pre-filled form instance from building data."""
    # Load template
    result = await db.execute(select(FormTemplate).where(FormTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template is None:
        raise ValueError(f"FormTemplate {template_id} not found")

    # Load building context
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # Load diagnostics + samples
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    diag_ids = [d.id for d in diagnostics]
    samples: list[Sample] = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Load intervention if specified
    intervention: Intervention | None = None
    if intervention_id:
        int_result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
        intervention = int_result.scalar_one_or_none()

    # Load documents
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    context = {
        "building": building,
        "diagnostics": diagnostics,
        "samples": samples,
        "intervention": intervention,
        "documents": documents,
    }

    # Pre-fill fields
    fields_schema = template.fields_schema or []
    field_values: dict[str, dict] = {}
    missing_fields: list[str] = []
    confidence_scores: list[float] = []

    confidence_map = {"high": 1.0, "medium": 0.7, "low": 0.0}

    for field_def in fields_schema:
        field_name = field_def.get("name", "")
        source = field_def.get("source_mapping", "manual")
        required = field_def.get("required", False)

        value, confidence = _resolve_source(source, context)

        field_values[field_name] = {
            "value": value,
            "confidence": confidence,
            "source": source,
            "manual_override": False,
        }

        conf_num = confidence_map.get(confidence, 0.0)
        confidence_scores.append(conf_num)

        if value is None and required:
            missing_fields.append(field_name)

    # Check missing attachments
    required_attachments = template.required_attachments or []
    doc_types = {(d.document_type or "").lower() for d in documents}
    missing_attachments = [att for att in required_attachments if att.lower() not in doc_types]

    # Compute overall confidence
    overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    # Determine initial status
    status = "prefilled" if missing_fields or missing_attachments else "reviewed"

    instance = FormInstance(
        template_id=template_id,
        building_id=building_id,
        organization_id=organization_id,
        created_by_id=created_by_id,
        intervention_id=intervention_id,
        status=status,
        field_values=field_values,
        attached_document_ids=[],
        missing_fields=missing_fields,
        missing_attachments=missing_attachments,
        prefill_confidence=round(overall_confidence, 4),
    )
    db.add(instance)
    await db.flush()
    return instance


# ---------------------------------------------------------------------------
# CRUD / lifecycle
# ---------------------------------------------------------------------------


async def get_form_instance(db: AsyncSession, form_id: UUID) -> FormInstance | None:
    result = await db.execute(select(FormInstance).where(FormInstance.id == form_id))
    return result.scalar_one_or_none()


async def list_form_instances(db: AsyncSession, building_id: UUID) -> list[FormInstance]:
    result = await db.execute(
        select(FormInstance).where(FormInstance.building_id == building_id).order_by(FormInstance.created_at.desc())
    )
    return list(result.scalars().all())


async def update_form(
    db: AsyncSession,
    form_id: UUID,
    field_values: dict[str, dict] | None = None,
    attached_document_ids: list[str] | None = None,
) -> FormInstance:
    instance = await get_form_instance(db, form_id)
    if instance is None:
        raise ValueError(f"FormInstance {form_id} not found")
    if instance.status in ("submitted", "acknowledged", "rejected"):
        raise ValueError(f"Cannot update form with status '{instance.status}'")

    if field_values is not None:
        # Merge with existing values, marking overrides
        current = instance.field_values or {}
        for key, val in field_values.items():
            current[key] = {
                "value": val.get("value"),
                "confidence": "high",
                "source": "manual",
                "manual_override": True,
            }
        instance.field_values = current

        # Recalculate missing fields
        missing = [k for k, v in current.items() if v.get("value") is None]
        instance.missing_fields = missing

    if attached_document_ids is not None:
        instance.attached_document_ids = attached_document_ids

    instance.status = "reviewed"
    await db.flush()
    return instance


async def submit_form(
    db: AsyncSession,
    form_id: UUID,
    submission_reference: str | None = None,
) -> FormInstance:
    instance = await get_form_instance(db, form_id)
    if instance is None:
        raise ValueError(f"FormInstance {form_id} not found")
    if instance.status not in ("prefilled", "reviewed", "complement_requested"):
        raise ValueError(f"Cannot submit form with status '{instance.status}'")

    instance.status = "submitted"
    instance.submitted_at = datetime.now(UTC)
    if submission_reference:
        instance.submission_reference = submission_reference
    await db.flush()
    return instance


async def handle_complement(
    db: AsyncSession,
    form_id: UUID,
    complement_details: str,
) -> FormInstance:
    instance = await get_form_instance(db, form_id)
    if instance is None:
        raise ValueError(f"FormInstance {form_id} not found")
    if instance.status != "submitted":
        raise ValueError(f"Cannot request complement for form with status '{instance.status}'")

    instance.status = "complement_requested"
    instance.complement_details = complement_details
    await db.flush()
    return instance


async def acknowledge_form(db: AsyncSession, form_id: UUID) -> FormInstance:
    instance = await get_form_instance(db, form_id)
    if instance is None:
        raise ValueError(f"FormInstance {form_id} not found")
    if instance.status not in ("submitted", "resubmitted"):
        raise ValueError(f"Cannot acknowledge form with status '{instance.status}'")

    instance.status = "acknowledged"
    instance.acknowledged_at = datetime.now(UTC)
    await db.flush()
    return instance
