"""Material recognition endpoint — upload a photo, get AI identification."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_element import BuildingElement
from app.models.material import Material
from app.models.user import User
from app.models.zone import Zone
from app.schemas.material_recognition import MaterialRecognitionResult
from app.services.material_recognition_service import (
    MaterialRecognitionError,
    get_dominant_pollutant,
    has_high_risk_pollutant,
    recognize_material,
)

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post(
    "/buildings/{building_id}/materials/recognize",
    response_model=MaterialRecognitionResult,
    tags=["Material Recognition"],
)
async def recognize_material_endpoint(
    building_id: UUID,
    file: UploadFile = File(...),
    zone_id: str | None = Form(None),
    element_id: str | None = Form(None),
    save: bool = Form(False),
    current_user: User = Depends(require_permission("materials", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a material photo for AI-based identification.

    Returns material type, estimated year, likely pollutants and confidence score.
    Optionally saves the result as a Material record when save=true and element_id is provided.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    media_type = file.content_type or "image/jpeg"
    if not media_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="File must be an image (JPEG, PNG, WebP)")

    try:
        result = await recognize_material(content, media_type)
    except MaterialRecognitionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    high_risk = has_high_risk_pollutant(result)
    dominant = get_dominant_pollutant(result)

    # Optionally persist as Material record
    if save and element_id:
        elem_uuid = UUID(element_id)
        zone_uuid = UUID(zone_id) if zone_id else None

        # Verify element exists for this building
        query = select(BuildingElement).where(BuildingElement.id == elem_uuid)
        if zone_uuid:
            query = query.join(Zone).where(Zone.building_id == building_id, Zone.id == zone_uuid)
        el = (await db.execute(query)).scalar_one_or_none()
        if not el:
            raise HTTPException(status_code=404, detail="Element not found")

        # Parse year from range
        year_range = result.get("estimated_year_range", "")
        year_est = None
        if "-" in year_range:
            try:
                parts = year_range.split("-")
                year_est = (int(parts[0]) + int(parts[1])) // 2
            except (ValueError, IndexError):
                pass

        material = Material(
            element_id=elem_uuid,
            material_type=result.get("material_type", "autre"),
            name=result.get("material_name", "AI-identified material"),
            description=result.get("description", ""),
            installation_year=year_est,
            contains_pollutant=high_risk,
            pollutant_type=dominant,
            source="ai_recognition",
            identified_by_ai=True,
            ai_confidence=result.get("confidence_overall", 0.0),
            year_estimated=year_est,
            ai_pollutants=result.get("likely_pollutants"),
            ai_recommendations=result.get("recommendations", []),
            created_by=current_user.id,
        )
        db.add(material)
        await db.commit()

    return MaterialRecognitionResult(
        material_type=result.get("material_type", "autre"),
        material_name=result.get("material_name", ""),
        estimated_year_range=result.get("estimated_year_range", ""),
        identified_materials=result.get("identified_materials", []),
        likely_pollutants=result.get("likely_pollutants", {}),
        confidence_overall=result.get("confidence_overall", 0.0),
        recommendations=result.get("recommendations", []),
        description=result.get("description", ""),
        has_high_risk=high_risk,
    )
