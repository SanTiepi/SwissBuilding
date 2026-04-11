import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import normalize_sample_unit
from app.database import get_db
from app.dependencies import require_permission
from app.limiter import limiter
from app.models.user import User
from app.schemas.diagnostic import (
    ApplyReportRequest,
    DiagnosticCreate,
    DiagnosticRead,
    DiagnosticUpdate,
    ParsedSampleData,
    ParseReportResponse,
)
from app.schemas.sample import SampleRead
from app.services.audit_service import log_action
from app.services.diagnostic_service import (
    create_diagnostic,
    get_diagnostic,
    list_diagnostics,
    update_diagnostic,
    validate_diagnostic,
)
from app.services.risk_engine import update_risk_score

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/buildings/{building_id}/diagnostics", response_model=list[DiagnosticRead])
async def list_diagnostics_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all diagnostics for a building."""
    diagnostics = await list_diagnostics(db, building_id)
    return diagnostics


@router.post("/buildings/{building_id}/diagnostics", response_model=DiagnosticRead, status_code=201)
async def create_diagnostic_endpoint(
    building_id: UUID,
    data: DiagnosticCreate,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new diagnostic for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    diagnostic = await create_diagnostic(db, building_id, data, current_user.id)
    await log_action(db, current_user.id, "create", "diagnostic", diagnostic.id)
    from app.services.action_service import sync_building_system_actions

    await sync_building_system_actions(db, building_id)
    try:
        from app.services.search_service import index_diagnostic

        index_diagnostic(diagnostic)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return diagnostic


@router.get("/diagnostics/{diagnostic_id}", response_model=DiagnosticRead)
async def get_diagnostic_endpoint(
    diagnostic_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single diagnostic with its samples."""
    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    return diagnostic


@router.put("/diagnostics/{diagnostic_id}", response_model=DiagnosticRead)
async def update_diagnostic_endpoint(
    diagnostic_id: UUID,
    data: DiagnosticUpdate,
    current_user: User = Depends(require_permission("diagnostics", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing diagnostic."""
    diagnostic = await update_diagnostic(db, diagnostic_id, data)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    await log_action(db, current_user.id, "update", "diagnostic", diagnostic_id)
    from app.services.action_service import sync_building_system_actions

    await sync_building_system_actions(db, diagnostic.building_id)

    # Auto-generate actions when status transitions to completed/validated
    if data.status in ("completed", "validated"):
        from app.services.action_generator import generate_actions_from_diagnostic

        generated = await generate_actions_from_diagnostic(db, diagnostic.building_id, diagnostic_id)
        if generated:
            diagnostic.generated_actions_count = len(generated)

    try:
        from app.services.search_service import index_diagnostic

        index_diagnostic(diagnostic)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return diagnostic


@router.patch("/diagnostics/{diagnostic_id}/validate", response_model=DiagnosticRead)
async def validate_diagnostic_endpoint(
    diagnostic_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "validate")),
    db: AsyncSession = Depends(get_db),
):
    """Validate a diagnostic (authority only). This locks the diagnostic and triggers risk score recalculation."""
    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    validated = await validate_diagnostic(db, diagnostic_id)
    if not validated:
        raise HTTPException(status_code=400, detail="Diagnostic could not be validated")

    # Recalculate risk score after validation
    await update_risk_score(db, diagnostic.building_id)
    await log_action(db, current_user.id, "validate", "diagnostic", diagnostic_id)
    from app.services.action_service import sync_building_system_actions

    await sync_building_system_actions(db, diagnostic.building_id)

    # Auto-generate actions from diagnostic findings
    from app.services.action_generator import generate_actions_from_diagnostic

    generated = await generate_actions_from_diagnostic(db, diagnostic.building_id, diagnostic_id)
    if generated:
        validated.generated_actions_count = len(generated)

    return validated


# DEPRECATED: Use parse-report + apply-report flow instead.
# This endpoint is kept for backwards compatibility.
@router.post("/diagnostics/{diagnostic_id}/upload-report", response_model=list[SampleRead])
@limiter.limit("10/hour")
async def upload_report_endpoint(
    request: Request,
    diagnostic_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF diagnostic report, parse it, and return extracted samples."""
    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Lazy import to keep module lightweight when parser is not needed
    import os
    import tempfile

    from app.ml.pdf_parser import extract_text_from_pdf, extract_text_with_ocr, parse_diagnostic_report
    from app.models.sample import Sample

    content = await file.read()

    # Write to a temp file for PDF extraction
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Extract text (try text-based first, fall back to OCR)
        text = extract_text_from_pdf(tmp_path)
        if not text or len(text.strip()) < 50:
            text = extract_text_with_ocr(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF")

    parsed = parse_diagnostic_report(text)

    # Create Sample objects from parsed data
    created_samples = []
    for s in parsed.get("samples", []):
        sample = Sample(
            diagnostic_id=diagnostic_id,
            sample_number=s.get("sample_number"),
            location_room=s.get("location"),
            material_description=s.get("material"),
            pollutant_type=s.get("pollutant_type"),
            pollutant_subtype=s.get("pollutant_subtype"),
            concentration=s.get("concentration"),
            unit=normalize_sample_unit(s.get("unit")),
        )
        db.add(sample)
        created_samples.append(sample)

    await db.commit()
    for sample in created_samples:
        await db.refresh(sample)

    await log_action(db, current_user.id, "upload_report", "diagnostic", diagnostic_id)
    from app.services.action_service import sync_building_system_actions

    await sync_building_system_actions(db, diagnostic.building_id)
    return created_samples


@router.post("/diagnostics/{diagnostic_id}/parse-report", response_model=ParseReportResponse)
@limiter.limit("10/hour")
async def parse_report_endpoint(
    request: Request,
    diagnostic_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Parse a PDF diagnostic report without persisting. Returns extracted data for review."""
    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    import os
    import tempfile

    from app.ml.pdf_parser import extract_text_from_pdf, extract_text_with_ocr, parse_diagnostic_report

    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = extract_text_from_pdf(tmp_path)
        if not text or len(text.strip()) < 50:
            text = extract_text_with_ocr(tmp_path)
    finally:
        os.unlink(tmp_path)

    warnings: list[str] = []
    if not text or not text.strip():
        warnings.append("Could not extract text from PDF")
        return ParseReportResponse(
            diagnostic_id=diagnostic_id,
            warnings=warnings,
            text_length=0,
        )

    if len(text.strip()) < 200:
        warnings.append("Very little text extracted — OCR quality may be poor")

    parsed = parse_diagnostic_report(text)

    samples = [
        ParsedSampleData(
            sample_number=s.get("sample_number"),
            location=s.get("location"),
            material=s.get("material"),
            pollutant_type=s.get("pollutant_type"),
            pollutant_subtype=s.get("pollutant_subtype"),
            concentration=s.get("concentration"),
            unit=s.get("unit"),
        )
        for s in parsed.get("samples", [])
    ]

    metadata = {k: v for k, v in parsed.items() if k != "samples" and v is not None}

    return ParseReportResponse(
        diagnostic_id=diagnostic_id,
        metadata=metadata,
        samples=samples,
        warnings=warnings,
        text_length=len(text),
    )


@router.post("/diagnostics/{diagnostic_id}/apply-report", response_model=list[SampleRead])
async def apply_report_endpoint(
    diagnostic_id: UUID,
    data: ApplyReportRequest,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Apply reviewed report data: create samples and update diagnostic metadata."""
    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    from app.models.sample import Sample

    # Update diagnostic metadata if provided
    if data.laboratory is not None:
        diagnostic.laboratory = data.laboratory
    if data.laboratory_report_number is not None:
        diagnostic.laboratory_report_number = data.laboratory_report_number
    if data.date_report is not None:
        diagnostic.date_report = data.date_report
    if data.summary is not None:
        diagnostic.summary = data.summary
    if data.conclusion is not None:
        diagnostic.conclusion = data.conclusion

    # Create samples
    created_samples = []
    for idx, s in enumerate(data.samples):
        sample = Sample(
            diagnostic_id=diagnostic_id,
            sample_number=s.sample_number or f"S-{idx + 1}",
            location_room=s.location,
            material_category=s.material or "unknown",
            material_description=s.material,
            pollutant_type=s.pollutant_type or "unknown",
            pollutant_subtype=s.pollutant_subtype,
            concentration=s.concentration,
            unit=normalize_sample_unit(s.unit) or "mg_per_kg",
        )
        db.add(sample)
        created_samples.append(sample)

    await db.commit()
    for sample in created_samples:
        await db.refresh(sample)

    await log_action(db, current_user.id, "apply_report", "diagnostic", diagnostic_id)
    return created_samples
