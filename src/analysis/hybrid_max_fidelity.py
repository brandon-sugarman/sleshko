from __future__ import annotations

from collections.abc import Iterable

import pymupdf

from analysis.acroform_cover import AcroFormCoverAnalyzer
from analysis.flattened_cover import extract_flattened_cover
from analysis.statement_totals import extract_statement_totals
from config import Settings
from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult, FieldValue
from domain.field_catalog import FieldSpec, build_catalog
from infra.gemini_client import GeminiClient, build_client, parse_gemini_fields
from k1_codes import TEXTLESS_STATEMENT_FIELD_NAMES, TEXTLESS_STATEMENT_OVERRIDE_FIELD_NAMES
from logger import make_logger

log = make_logger("analysis.hybrid_max_fidelity")


class HybridMaxFidelityAnalyzer:
    """High-precision K-1 analyzer with deterministic extraction first.

    It trusts AcroForm cover fields, statement-page totals, and flattened-cover
    coordinates before using Gemini on pages that have no text layer.
    """

    name = "hybrid_max_fidelity"

    def __init__(self, client: GeminiClient | None) -> None:
        self._acroform = AcroFormCoverAnalyzer()
        self._client = client
        self._catalog = list(build_catalog())
        self._fallback_fields = [f for f in self._catalog if f.name in TEXTLESS_STATEMENT_FIELD_NAMES]

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        emitted: dict[str, FieldValue] = {}
        self._merge(emitted, self._acroform.analyze(document).fields.values())
        self._merge(emitted, extract_statement_totals(document).values())
        self._merge(emitted, extract_flattened_cover(document).values())
        self._apply_textless_page_fallback(document, emitted)

        log.info(
            "hybrid_max_fidelity done",
            {"doc": document.doc_name, "fields_emitted": len(emitted)},
        )
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)

    def _merge(self, emitted: dict[str, FieldValue], values: Iterable[FieldValue]) -> None:
        for value in values:
            emitted[value.field] = value

    def _apply_textless_page_fallback(
        self,
        document: ExtractedDocument,
        emitted: dict[str, FieldValue],
    ) -> None:
        if self._client is None or document.source_bytes is None:
            return
        textless_pages = [p.page for p in document.pages if p.page > 0 and not p.text.strip()]
        if not textless_pages:
            return

        pdf = pymupdf.open(stream=document.source_bytes, filetype="pdf")
        try:
            for page_idx in textless_pages:
                pix = pdf.load_page(page_idx).get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                prompt = _build_image_prompt(self._fallback_fields)
                response = self._client.generate([self._client.image_part(pix.tobytes("png")), prompt])
                for value in parse_gemini_fields(response, self._fallback_fields).values():
                    if value.field not in emitted or value.field in TEXTLESS_STATEMENT_OVERRIDE_FIELD_NAMES:
                        emitted[value.field] = FieldValue(
                            field=value.field,
                            value=value.value,
                            source=f"gemini_image:p{page_idx + 1}",
                        )
        finally:
            pdf.close()


def build(settings: Settings) -> HybridMaxFidelityAnalyzer:
    try:
        client = build_client(settings.gemini_model, settings.gemini_max_attempts)
    except ValueError as exc:
        log.warning("gemini fallback disabled", {"error": str(exc)})
        client = None
    return HybridMaxFidelityAnalyzer(client=client)


def _build_image_prompt(fields: list[FieldSpec]) -> str:
    field_lines = "\n".join(f'  "{field.name}": integer' for field in fields)
    return f"""Extract only taxpayer-specific non-zero amounts from this Schedule K-1 statement image.
Ignore instructions, examples, labels, page numbers, percentages, addresses, and generic code descriptions.
Return only valid JSON with keys from this list. Omit absent fields.

FIELDS:
{{
{field_lines}
}}
"""
