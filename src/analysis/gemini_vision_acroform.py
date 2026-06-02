"""Vision-first extraction with AcroForm cover values overlaid as authoritative overrides.

`gemini_vision` consistently misses 2 non-zero fields on doc_1 (cover page fields
that are machine-readable from the AcroForm widget layer). `acroform_gemini_selective`
recovers those fields but hallucinates on docs with rich statement pages because it
narrows the Gemini call to only "still-missing" fields, creating pressure to invent them.

This strategy avoids both failure modes:
  1. Run full gemini_vision (image + advisory text, all pages) — complete spatial coverage.
  2. Run AcroFormCoverAnalyzer (deterministic, no API call) — exact cover page values.
  3. Merge: vision fills everything; acroform overrides on conflict.

Step 3 is safe because AcroForm widget values on the IRS K-1 template are exact
machine-readable integers/strings — more reliable than OCR for cover fields. When
the AcroForm is absent (flattened PDFs), step 3 is a no-op and the result equals
pure gemini_vision.
"""

from __future__ import annotations

from analysis.acroform_cover import AcroFormCoverAnalyzer
from analysis.gemini_vision import GeminiVisionAnalyzer
from config import Settings
from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult
from infra.gemini_client import build_client
from logger import make_logger

log = make_logger("analysis.gemini_vision_acroform")


class GeminiVisionAcroformAnalyzer:
    """Full vision extraction with AcroForm cover values applied as authoritative overrides."""

    name = "gemini_vision_acroform"

    def __init__(self, vision: GeminiVisionAnalyzer, acroform: AcroFormCoverAnalyzer) -> None:
        self._vision = vision
        self._acroform = acroform

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        vision_result = self._vision.analyze(document)
        acroform_result = self._acroform.analyze(document)

        merged = dict(vision_result.fields)
        merged.update(acroform_result.fields)

        log.info(
            "gemini_vision_acroform done",
            {
                "doc": document.doc_name,
                "vision_fields": len(vision_result.fields),
                "acroform_fields": len(acroform_result.fields),
                "merged_fields": len(merged),
            },
        )
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=merged)


def build(settings: Settings) -> GeminiVisionAcroformAnalyzer:
    client = build_client(settings.gemini)
    vision = GeminiVisionAnalyzer(client=client, dpi=settings.vision_dpi)
    acroform = AcroFormCoverAnalyzer()
    return GeminiVisionAcroformAnalyzer(vision=vision, acroform=acroform)
