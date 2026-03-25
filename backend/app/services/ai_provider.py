"""BatiConnect — AI Provider adapter (stub + OpenAI).

Provides a unified interface for AI extraction. Returns OpenAI if
OPENAI_API_KEY is set, otherwise falls back to StubAIProvider.
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class AIProviderBase(ABC):
    """Abstract base for AI extraction providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    async def extract(
        self,
        input_text: str,
        extraction_type: str,
        schema_hint: dict | None = None,
    ) -> dict:
        """Returns {fields: {}, confidence: float, ambiguous: [], unknown: []}."""
        ...


# ---------------------------------------------------------------------------
# Stub (tests / dev)
# ---------------------------------------------------------------------------

_STUB_EXTRACTIONS: dict[str, dict[str, Any]] = {
    "quote_pdf": {
        "fields": {
            "scope_items": ["asbestos_removal", "waste_disposal", "air_monitoring"],
            "exclusions": ["scaffolding", "permits"],
            "timeline_weeks": 6,
            "amount_chf": 45000.0,
        },
        "confidence": 0.80,
        "ambiguous": [{"field": "timeline_weeks", "reason": "Multiple timelines mentioned"}],
        "unknown": [{"field": "payment_terms"}],
    },
    "completion_report": {
        "fields": {
            "completed_items": ["asbestos_removal", "waste_disposal", "final_report"],
            "residual_items": ["air_monitoring_post"],
            "final_amount_chf": 43500.0,
        },
        "confidence": 0.85,
        "ambiguous": [{"field": "residual_items", "reason": "Partial completion noted"}],
        "unknown": [],
    },
    "certificate": {
        "fields": {
            "certificate_type": "clearance",
            "issuer": "SUVA",
            "date_issued": "2025-06-15",
            "building_ref": "EGID-12345",
            "pollutant": "asbestos",
            "result": "cleared",
        },
        "confidence": 0.90,
        "ambiguous": [],
        "unknown": [{"field": "validity_period"}],
    },
}


class StubAIProvider(AIProviderBase):
    """Returns mock extractions for tests/dev."""

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def model_version(self) -> str:
        return "stub-v0"

    async def extract(
        self,
        input_text: str,
        extraction_type: str,
        schema_hint: dict | None = None,
    ) -> dict:
        template = _STUB_EXTRACTIONS.get(extraction_type, _STUB_EXTRACTIONS["quote_pdf"])
        return {
            "fields": template["fields"],
            "confidence": template["confidence"],
            "ambiguous": template["ambiguous"],
            "unknown": template["unknown"],
        }


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

_PROMPTS: dict[str, str] = {
    "quote_pdf": (
        "Extract structured data from this remediation quote. "
        "Return JSON with: scope_items (list), exclusions (list), timeline_weeks (int|null), "
        "amount_chf (float|null). Also identify any ambiguous or unknown fields."
    ),
    "completion_report": (
        "Extract structured data from this completion report. "
        "Return JSON with: completed_items (list), residual_items (list), "
        "final_amount_chf (float|null). Identify ambiguous/unknown fields."
    ),
    "certificate": (
        "Extract structured data from this certificate/clearance document. "
        "Return JSON with: certificate_type, issuer, date_issued, building_ref, "
        "pollutant, result. Identify ambiguous/unknown fields."
    ),
}

_PROMPT_VERSION = "v1.0"


class OpenAIProvider(AIProviderBase):
    """Real provider using OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_version(self) -> str:
        return self._model

    async def extract(
        self,
        input_text: str,
        extraction_type: str,
        schema_hint: dict | None = None,
    ) -> dict:
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed — required for OpenAI provider")
            raise RuntimeError("httpx package required for OpenAI provider") from None

        system_prompt = _PROMPTS.get(extraction_type, _PROMPTS["quote_pdf"])
        if schema_hint:
            system_prompt += f"\n\nExpected schema hint: {json.dumps(schema_hint)}"

        system_prompt += (
            "\n\nReturn valid JSON with keys: fields (object), confidence (float 0-1), "
            "ambiguous (list of {field, reason}), unknown (list of {field})."
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()

        latency_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        result = {
            "fields": parsed.get("fields", {}),
            "confidence": parsed.get("confidence", 0.5),
            "ambiguous": parsed.get("ambiguous", []),
            "unknown": parsed.get("unknown", []),
            "_latency_ms": latency_ms,
        }
        return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROMPT_VERSION_CURRENT = _PROMPT_VERSION


def get_prompt_version() -> str:
    return _PROMPT_VERSION_CURRENT


def get_ai_provider() -> AIProviderBase:
    """Factory: returns OpenAI if OPENAI_API_KEY set, else Stub."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAIProvider(api_key=api_key, model=model)
    return StubAIProvider()
