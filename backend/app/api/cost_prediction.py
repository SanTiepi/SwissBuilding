"""RénoPredict — Remediation cost estimation API."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cost_prediction import CostPredictionRequest, CostPredictionResponse
from app.services.cost_predictor_service import CostPredictionError, predict_cost
from app.services.gotenberg_service import html_to_pdf

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/predict/cost",
    response_model=CostPredictionResponse,
    summary="Estimate remediation cost for a pollutant",
    description=(
        "Compute a fourchette (min/median/max) for pollutant remediation "
        "based on Swiss market averages, canton coefficients, and accessibility."
    ),
)
async def predict_cost_endpoint(
    request: CostPredictionRequest,
    current_user: User = Depends(require_permission("simulations", "read")),
    db: AsyncSession = Depends(get_db),
) -> CostPredictionResponse:
    try:
        return await predict_cost(db, request)
    except CostPredictionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _format_chf(amount: float) -> str:
    """Format a number as CHF with thousands separator."""
    return f"CHF {amount:,.2f}".replace(",", "'")


def _build_cost_pdf_html(result: CostPredictionResponse, request: CostPredictionRequest) -> str:
    """Build an HTML document for cost estimation PDF export."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    breakdown_rows = ""
    for item in result.breakdown:
        breakdown_rows += (
            f"<tr>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb;'>{item.label}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb;text-align:right;'>{item.percentage}%</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb;text-align:right;'>{_format_chf(item.amount_min)}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;'>{_format_chf(item.amount_median)}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb;text-align:right;'>{_format_chf(item.amount_max)}</td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><style>
body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1f2937; margin: 0; padding: 40px; }}
h1 {{ font-size: 22px; margin-bottom: 4px; }}
.subtitle {{ color: #6b7280; font-size: 13px; margin-bottom: 24px; }}
.card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.grid {{ display: flex; gap: 16px; margin-bottom: 16px; }}
.grid .cell {{ flex: 1; }}
.label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
.value {{ font-size: 16px; font-weight: 600; }}
.range {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
.range .min {{ color: #16a34a; }}
.range .median {{ color: #2563eb; font-weight: 700; font-size: 18px; }}
.range .max {{ color: #ea580c; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 8px 10px; background: #f9fafb; border-bottom: 2px solid #e5e7eb; font-weight: 600; }}
th:not(:first-child) {{ text-align: right; }}
.disclaimer {{ margin-top: 24px; padding: 12px; background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px; font-size: 12px; color: #92400e; font-style: italic; }}
.footer {{ margin-top: 32px; font-size: 10px; color: #9ca3af; text-align: center; }}
</style></head>
<body>
<h1>Estimation des couts de remediation</h1>
<p class="subtitle">Genere le {now} — BatiConnect RenoPredict</p>

<div class="grid">
  <div class="cell card">
    <div class="label">Polluant</div>
    <div class="value">{result.pollutant_type}</div>
  </div>
  <div class="cell card">
    <div class="label">Materiau</div>
    <div class="value">{result.material_type}</div>
  </div>
  <div class="cell card">
    <div class="label">Surface</div>
    <div class="value">{result.surface_m2} m²</div>
  </div>
  <div class="cell card">
    <div class="label">Canton</div>
    <div class="value">{request.canton} (x{result.canton_coefficient:.2f})</div>
  </div>
</div>

<div class="grid">
  <div class="cell card">
    <div class="label">Accessibilite</div>
    <div class="value">{request.accessibility} (x{result.accessibility_coefficient:.2f})</div>
  </div>
  <div class="cell card">
    <div class="label">Condition</div>
    <div class="value">{request.condition}</div>
  </div>
  <div class="cell card">
    <div class="label">Methode</div>
    <div class="value">{result.method}</div>
  </div>
  <div class="cell card">
    <div class="label">Complexite / Delai</div>
    <div class="value">{result.complexity} — {result.duration_days} jours</div>
  </div>
</div>

<div class="card">
  <div class="label">Fourchette de cout</div>
  <div class="range" style="margin-top:8px;">
    <span class="min">{_format_chf(result.cost_min)}</span>
    <span class="median">{_format_chf(result.cost_median)}</span>
    <span class="max">{_format_chf(result.cost_max)}</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>Poste</th><th>%</th><th>Min</th><th>Median</th><th>Max</th>
    </tr>
  </thead>
  <tbody>{breakdown_rows}</tbody>
</table>

<div class="disclaimer">{result.disclaimer}</div>
<div class="footer">BatiConnect — Building Intelligence Network — batiscan.ch</div>
</body></html>"""


@router.post(
    "/predict/cost/pdf",
    summary="Export cost estimation as PDF",
    response_class=Response,
)
async def predict_cost_pdf_endpoint(
    request: CostPredictionRequest,
    current_user: User = Depends(require_permission("simulations", "read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        result = await predict_cost(db, request)
    except CostPredictionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    html = _build_cost_pdf_html(result, request)
    try:
        pdf_bytes = await html_to_pdf(html)
    except Exception as exc:
        logger.error("Gotenberg PDF generation failed: %s", exc)
        raise HTTPException(status_code=502, detail="PDF generation service unavailable") from exc

    filename = f"estimation-{result.pollutant_type}-{request.canton}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
