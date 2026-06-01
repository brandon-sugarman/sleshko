"""Gemini SDK adapter — the single file that imports google-genai.

Domain and analysis modules must not import this directly; they receive a
GeminiClient instance via their build(settings) factory.

Also exports `parse_gemini_fields` — the shared response parser used by all
Gemini analysis strategies so the JSON-coercion logic lives in one place.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from domain.extraction_result import FieldValue
from domain.field_catalog import FieldSpec, FieldType
from eval.normalize import normalize_int
from logger import make_logger

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

log = make_logger("infra.gemini_client")

_NO_THINKING = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)


def _load_dotenv() -> None:
    """Best-effort .env loader so the API key works without exporting it."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class GeminiClient:
    """Synchronous Gemini wrapper with linear retry backoff.

    `contents` passed to `generate` follow the google-genai SDK convention:
    a list of strings and/or `types.Part` objects (text, images, PDF bytes).
    """

    def __init__(self, model: str, max_attempts: int = 3) -> None:
        _load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set — add it to .env or export it")
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.max_attempts = max_attempts

    def generate(self, contents: list[Any]) -> str:
        """Call Gemini and return the response text. Retries up to max_attempts."""
        last_err: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                t0 = time.monotonic()
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=_NO_THINKING,
                )
                latency_ms = round((time.monotonic() - t0) * 1000)
                log.info("gemini ok", {"model": self.model, "attempt": attempt + 1, "latency_ms": latency_ms})
                return response.text or ""
            except Exception as exc:
                last_err = exc
                log.warning(
                    "gemini attempt failed",
                    {"attempt": attempt + 1, "max": self.max_attempts, "error": str(exc)},
                )
                if attempt < self.max_attempts - 1:
                    time.sleep(1.5 * (2**attempt))
        raise RuntimeError(f"Gemini gave up after {self.max_attempts} attempts: {last_err}")

    def pdf_part(self, pdf_bytes: bytes) -> types.Part:
        return types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    def image_part(self, png_bytes: bytes) -> types.Part:
        return types.Part.from_bytes(data=png_bytes, mime_type="image/png")


def build_client(model: str, max_attempts: int) -> GeminiClient:
    return GeminiClient(model=model, max_attempts=max_attempts)


def parse_gemini_fields(raw: str, fields: list[FieldSpec]) -> dict[str, FieldValue]:
    """Parse a Gemini JSON response into a {field_name: FieldValue} mapping.

    Tolerates prose or markdown fences around the JSON object. Only emits
    non-zero integer values and non-empty text values — absent fields default
    to zero at scoring time so there is no benefit to emitting explicit zeros.
    """
    match = _JSON_RE.search(raw)
    if not match:
        log.warning("no JSON object in gemini response", {"preview": raw[:200]})
        return {}
    try:
        data: dict = json.loads(match.group())
    except json.JSONDecodeError as exc:
        log.warning("gemini JSON parse failed", {"error": str(exc), "preview": raw[:200]})
        return {}

    spec_map = {f.name: f for f in fields}
    emitted: dict[str, FieldValue] = {}
    for key, raw_val in data.items():
        spec = spec_map.get(key)
        if spec is None or raw_val is None:
            continue
        if spec.type is FieldType.integer:
            val = normalize_int(str(raw_val))
            if val != 0:
                emitted[key] = FieldValue(field=key, value=val, source="gemini")
        else:
            text_val = str(raw_val).strip()
            if text_val:
                emitted[key] = FieldValue(field=key, value=text_val, source="gemini")
    return emitted
