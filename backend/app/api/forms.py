"""
BatiConnect - Forms Workspace API

Routes for regulatory form identification, pre-fill, update, submit, and lifecycle management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.form_instance import FormInstance, FormTemplate
from app.models.user import User
from app.schemas.form_instance import (
    ApplicableFormTemplate,
    FormComplementRequest,
    FormInstanceRead,
    FormInstanceUpdate,
    FormSubmitRequest,
    FormTemplateRead,
)
from app.services.forms_service import (
    acknowledge_form,
    get_applicable_forms,
    get_form_instance,
    handle_complement,
    list_form_instances,
    prefill_form,
    submit_form,
    update_form,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


def _instance_to_read(instance: FormInstance) -> dict:
    """Convert FormInstance to dict with template info."""
    data = {
        "id": instance.id,
        "template_id": instance.template_id,
        "building_id": instance.building_id,
        "organization_id": instance.organization_id,
        "created_by_id": instance.created_by_id,
        "intervention_id": instance.intervention_id,
        "status": instance.status,
        "field_values": instance.field_values,
        "attached_document_ids": instance.attached_document_ids,
        "missing_fields": instance.missing_fields,
        "missing_attachments": instance.missing_attachments,
        "prefill_confidence": instance.prefill_confidence,
        "submitted_at": instance.submitted_at,
        "submission_reference": instance.submission_reference,
        "complement_details": instance.complement_details,
        "acknowledged_at": instance.acknowledged_at,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
        "template_name": instance.template.name if instance.template else None,
        "template_form_type": instance.template.form_type if instance.template else None,
    }
    return data


@router.get(
    "/buildings/{building_id}/forms/applicable",
    response_model=list[ApplicableFormTemplate],
)
async def applicable_forms_endpoint(
    building_id: UUID,
    intervention_type: str | None = Query(None),
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List regulatory forms applicable to a building."""
    await _get_building_or_404(db, building_id)
    try:
        items = await get_applicable_forms(db, building_id, intervention_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return [
        {
            "template": FormTemplateRead.model_validate(item["template"]),
            "reason": item["reason"],
        }
        for item in items
    ]


@router.post(
    "/buildings/{building_id}/forms/{template_id}/prefill",
    response_model=FormInstanceRead,
    status_code=201,
)
async def prefill_form_endpoint(
    building_id: UUID,
    template_id: UUID,
    intervention_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("compliance_artefacts", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Pre-fill a regulatory form from building data."""
    await _get_building_or_404(db, building_id)
    try:
        instance = await prefill_form(
            db,
            template_id=template_id,
            building_id=building_id,
            created_by_id=current_user.id,
            organization_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
            intervention_id=intervention_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    await db.commit()
    await db.refresh(instance)
    # Eagerly load template
    result = await db.execute(select(FormInstance).where(FormInstance.id == instance.id))
    instance = result.scalar_one()
    result2 = await db.execute(select(FormTemplate).where(FormTemplate.id == instance.template_id))
    tpl = result2.scalar_one_or_none()
    instance.template = tpl  # type: ignore[assignment]
    return _instance_to_read(instance)


@router.get(
    "/buildings/{building_id}/forms",
    response_model=list[FormInstanceRead],
)
async def list_forms_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all form instances for a building."""
    await _get_building_or_404(db, building_id)
    instances = await list_form_instances(db, building_id)
    # Load templates for each
    result_list = []
    for inst in instances:
        tpl_result = await db.execute(select(FormTemplate).where(FormTemplate.id == inst.template_id))
        inst.template = tpl_result.scalar_one_or_none()  # type: ignore[assignment]
        result_list.append(_instance_to_read(inst))
    return result_list


@router.get(
    "/forms/{form_id}",
    response_model=FormInstanceRead,
)
async def get_form_endpoint(
    form_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single form instance."""
    instance = await get_form_instance(db, form_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Form instance not found")
    tpl_result = await db.execute(select(FormTemplate).where(FormTemplate.id == instance.template_id))
    instance.template = tpl_result.scalar_one_or_none()  # type: ignore[assignment]
    return _instance_to_read(instance)


@router.put(
    "/forms/{form_id}",
    response_model=FormInstanceRead,
)
async def update_form_endpoint(
    form_id: UUID,
    data: FormInstanceUpdate,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update form field values and attached documents."""
    try:
        instance = await update_form(
            db,
            form_id,
            field_values=data.field_values,
            attached_document_ids=data.attached_document_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(instance)
    tpl_result = await db.execute(select(FormTemplate).where(FormTemplate.id == instance.template_id))
    instance.template = tpl_result.scalar_one_or_none()  # type: ignore[assignment]
    return _instance_to_read(instance)


@router.post(
    "/forms/{form_id}/submit",
    response_model=FormInstanceRead,
)
async def submit_form_endpoint(
    form_id: UUID,
    data: FormSubmitRequest | None = None,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a form (marks as submitted with timestamp)."""
    try:
        instance = await submit_form(
            db,
            form_id,
            submission_reference=data.submission_reference if data else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(instance)
    tpl_result = await db.execute(select(FormTemplate).where(FormTemplate.id == instance.template_id))
    instance.template = tpl_result.scalar_one_or_none()  # type: ignore[assignment]
    return _instance_to_read(instance)


@router.post(
    "/forms/{form_id}/complement",
    response_model=FormInstanceRead,
)
async def complement_form_endpoint(
    form_id: UUID,
    data: FormComplementRequest,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Handle complement request from authority."""
    try:
        instance = await handle_complement(db, form_id, data.complement_details)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(instance)
    tpl_result = await db.execute(select(FormTemplate).where(FormTemplate.id == instance.template_id))
    instance.template = tpl_result.scalar_one_or_none()  # type: ignore[assignment]
    return _instance_to_read(instance)


@router.post(
    "/forms/{form_id}/acknowledge",
    response_model=FormInstanceRead,
)
async def acknowledge_form_endpoint(
    form_id: UUID,
    current_user: User = Depends(require_permission("compliance_artefacts", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a form (submitted -> acknowledged)."""
    try:
        instance = await acknowledge_form(db, form_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(instance)
    tpl_result = await db.execute(select(FormTemplate).where(FormTemplate.id == instance.template_id))
    instance.template = tpl_result.scalar_one_or_none()  # type: ignore[assignment]
    return _instance_to_read(instance)
