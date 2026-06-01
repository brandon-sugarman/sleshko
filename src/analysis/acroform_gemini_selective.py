"""AcroForm-first analysis with selective per-page Gemini fallback.

This strategy keeps the high-confidence AcroForm cover extraction, then asks
Gemini only about unresolved fields on relevant non-AcroForm pages. It avoids
the deterministic statement regexes in hybrid_max_fidelity while keeping the
LLM work bounded and page-local.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from analysis.acroform_cover import AcroFormCoverAnalyzer
from config import Settings
from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult, FieldValue
from domain.field_catalog import FieldSpec, build_catalog
from domain.page_roles import select_data_pages
from infra.gemini_client import GeminiClient, build_client, parse_gemini_fields
from infra.pdf_render import render_page_pngs
from logger import make_logger
from prompts.k1_extraction import build_vision_page_prompt

log = make_logger("analysis.acroform_gemini_selective")

_MAX_PARALLEL_PAGES = 8


class AcroFormGeminiSelectiveAnalyzer:
    """Trust AcroForm values first, then use Gemini only where it adds coverage."""

    name = "acroform_gemini_selective"

    def __init__(self, client: GeminiClient, dpi: int) -> None:
        self._acroform = AcroFormCoverAnalyzer()
        self._client = client
        self._dpi = dpi
        self._catalog = list(build_catalog())

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        if document.source_bytes is None:
            raise ValueError(
                "acroform_gemini_selective requires source_bytes - use 'pymupdf_full'"
            )

        emitted = dict(self._acroform.analyze(document).fields)
        fallback_fields = _unresolved_fields(self._catalog, emitted)
        selected_pages = _select_fallback_pages(document)

        if fallback_fields and selected_pages:
            images = render_page_pngs(document.source_bytes, self._dpi, selected_pages)
            for field in self._extract_pages(images, fallback_fields).values():
                emitted.setdefault(field.field, field)

        log.info(
            "acroform_gemini_selective done",
            {
                "doc": document.doc_name,
                "acroform_fields": len(document.form_fields),
                "fallback_pages": selected_pages,
                "fields_emitted": len(emitted),
            },
        )
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)

    def _extract_pages(
        self,
        images: dict[int, bytes],
        fields: list[FieldSpec],
    ) -> dict[str, FieldValue]:
        ordered = sorted(images.items())
        if not ordered:
            return {}

        prompt = build_vision_page_prompt(fields)
        workers = min(_MAX_PARALLEL_PAGES, len(ordered))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            per_page = list(pool.map(lambda item: self._extract_one(*item, prompt, fields), ordered))
        return _merge_pages(per_page)

    def _extract_one(
        self,
        page_idx: int,
        png: bytes,
        prompt: str,
        fields: list[FieldSpec],
    ) -> tuple[int, dict[str, FieldValue]]:
        response = self._client.generate([self._client.image_part(png), prompt])
        parsed = parse_gemini_fields(response, fields)
        page_fields = {
            name: FieldValue(field=value.field, value=value.value, source=f"selective_vision:p{page_idx + 1}")
            for name, value in parsed.items()
        }
        log.info("acroform_gemini_selective page", {"page": page_idx + 1, "fields": len(page_fields)})
        return page_idx, page_fields


def build(settings: Settings) -> AcroFormGeminiSelectiveAnalyzer:
    client = build_client(settings.gemini)
    return AcroFormGeminiSelectiveAnalyzer(client=client, dpi=settings.vision_dpi)


def _unresolved_fields(catalog: list[FieldSpec], emitted: dict[str, FieldValue]) -> list[FieldSpec]:
    return [field for field in catalog if field.name not in emitted]


def _select_fallback_pages(document: ExtractedDocument) -> list[int]:
    page_texts = {page.page: page.text for page in document.pages}
    data_pages = set(select_data_pages(page_texts))
    return [
        page.page
        for page in document.pages
        if page.page in data_pages and not page.form_fields
    ]


def _merge_pages(per_page: list[tuple[int, dict[str, FieldValue]]]) -> dict[str, FieldValue]:
    merged: dict[str, FieldValue] = {}
    for _page_idx, fields in sorted(per_page):
        for name, value in fields.items():
            merged.setdefault(name, value)
    return merged
