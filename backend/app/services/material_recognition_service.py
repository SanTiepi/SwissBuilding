"""Material recognition via Claude Vision API.

Upload a photo of a building material → Claude identifies type, estimated year,
and associated pollutants (asbestos, PCB, lead, HAP, radon, PFAS).
"""

import base64
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

MATERIAL_RECOGNITION_PROMPT = """
Vous êtes un expert en matériaux de construction suisse.
Analysez cette photo de matériau et répondez UNIQUEMENT en JSON valide (pas de markdown, pas de commentaire):
{
  "material_type": "joint_carrelage | vinyl | mousse_isolante | peinture | fibre_ciment | platre | beton | bitume | mastic | autre",
  "material_name": "Nom descriptif du matériau identifié",
  "estimated_year_range": "1970-1980",
  "identified_materials": ["ciment", "vinyle", "..."],
  "likely_pollutants": {
    "asbestos": {"probability": 0.75, "reason": "Explication courte"},
    "pcb": {"probability": 0.2, "reason": "Explication courte"},
    "lead": {"probability": 0.05, "reason": "Explication courte"},
    "hap": {"probability": 0.0, "reason": "Explication courte"},
    "radon": {"probability": 0.0, "reason": "Non applicable pour ce matériau"},
    "pfas": {"probability": 0.0, "reason": "Explication courte"}
  },
  "confidence_overall": 0.82,
  "recommendations": ["Recommande test laboratoire amiante avant travaux", "..."],
  "description": "Description courte du matériau observé et son contexte typique dans les bâtiments suisses"
}

Règles:
- Probabilités entre 0.0 et 1.0
- confidence_overall entre 0.0 et 1.0
- Basez-vous sur la période de construction suisse et les matériaux typiques
- Si la photo est floue ou ambiguë, baissez la confidence
- Toujours recommander un test labo si probabilité polluant > 0.5
"""

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class MaterialRecognitionError(Exception):
    """Raised when material recognition fails."""


async def recognize_material(image_data: bytes, media_type: str) -> dict:
    """Analyze a material photo via Claude Vision API.

    Args:
        image_data: Raw image bytes (max 5 MB).
        media_type: MIME type (image/jpeg, image/png, etc.).

    Returns:
        Parsed JSON dict with material identification results.

    Raises:
        MaterialRecognitionError: If API call fails or response can't be parsed.
    """
    if len(image_data) > MAX_FILE_SIZE:
        raise MaterialRecognitionError(f"File too large: {len(image_data)} bytes (max {MAX_FILE_SIZE})")

    if media_type not in ALLOWED_MIME_TYPES:
        raise MaterialRecognitionError(
            f"Unsupported image type: {media_type}. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise MaterialRecognitionError("ANTHROPIC_API_KEY not configured")

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    b64_image = base64.b64encode(image_data).decode()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": b64_image,
                                    },
                                },
                                {"type": "text", "text": MATERIAL_RECOGNITION_PROMPT},
                            ],
                        }
                    ],
                },
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Claude API HTTP error: %s %s", exc.response.status_code, exc.response.text[:200])
        raise MaterialRecognitionError(f"Claude API error: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.error("Claude API request error: %s", exc)
        raise MaterialRecognitionError("Claude API connection error") from exc

    data = resp.json()
    raw_text = data.get("content", [{}])[0].get("text", "")

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Claude response as JSON: %s", raw_text[:300])
        raise MaterialRecognitionError("Invalid JSON response from Claude") from exc

    return _validate_result(result)


def _validate_result(result: dict) -> dict:
    """Validate and normalize the recognition result."""
    confidence = result.get("confidence_overall", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    result["confidence_overall"] = max(0.0, min(1.0, float(confidence)))

    pollutants = result.get("likely_pollutants", {})
    if isinstance(pollutants, dict):
        for _key, val in pollutants.items():
            if isinstance(val, dict) and "probability" in val:
                val["probability"] = max(0.0, min(1.0, float(val["probability"])))
    result["likely_pollutants"] = pollutants

    if "material_type" not in result:
        result["material_type"] = "autre"
    if "material_name" not in result:
        result["material_name"] = result["material_type"]
    if "recommendations" not in result:
        result["recommendations"] = []
    if "description" not in result:
        result["description"] = ""

    return result


def has_high_risk_pollutant(result: dict, threshold: float = 0.5) -> bool:
    """Check if any pollutant exceeds the risk threshold."""
    pollutants = result.get("likely_pollutants", {})
    return any(isinstance(v, dict) and v.get("probability", 0) >= threshold for v in pollutants.values())


def get_dominant_pollutant(result: dict) -> str | None:
    """Return the pollutant with highest probability, or None."""
    pollutants = result.get("likely_pollutants", {})
    best_key, best_prob = None, 0.0
    for key, val in pollutants.items():
        if isinstance(val, dict):
            prob = val.get("probability", 0)
            if prob > best_prob:
                best_key, best_prob = key, prob
    return best_key if best_prob > 0 else None
