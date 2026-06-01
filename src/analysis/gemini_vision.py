"""LLM-forward analysis: extract each K-1 data page from its rendered image.

Whole-document extraction (text or native-PDF) mis-binds numbers to fields on
flattened K-1s because labels and values drift apart in the content stream. This
strategy instead renders each data page to an image and extracts it in
isolation, in parallel. Per-page isolation removes cross-page ambiguity and the
rendered image is immune to the text-layer encoding quirks (e.g. typographic
apostrophes, scrambled reading order) that defeat the deterministic strategies.

It pairs with the `pymupdf_full` extraction strategy, which preserves the raw
PDF bytes needed to render page images and the per-page text used to skip
boilerplate pages.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from config import Settings
from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult, FieldValue
from domain.field_catalog import build_catalog
from domain.page_roles import select_data_pages
from infra.gemini_client import GeminiClient, build_client, parse_gemini_fields
from infra.pdf_render import render_page_pngs
from logger import make_logger
from prompts.k1_extraction import build_vision_page_prompt

log = make_logger("analysis.gemini_vision")

_MAX_PARALLEL_PAGES = 8


class GeminiVisionAnalyzer:
    """Per-page, parallel, vision-based K-1 extraction."""

    name = "gemini_vision"

    def __init__(self, client: GeminiClient, dpi: int) -> None:
        self._client = client
        self._dpi = dpi
        self._catalog = list(build_catalog())
        self._prompt = build_vision_page_prompt(self._catalog)

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        if document.source_bytes is None:
            raise ValueError(
                "gemini_vision requires source_bytes — use 'pymupdf_full' extraction strategy"
            )

        page_texts = {p.page: p.text for p in document.pages}
        selected = select_data_pages(page_texts)
        images = render_page_pngs(document.source_bytes, self._dpi, selected)

        log.info(
            "gemini_vision start",
            {"doc": document.doc_name, "pages_total": len(page_texts), "pages_selected": selected},
        )

        per_page = self._extract_pages(images)
        emitted = _merge_pages(per_page)

        log.info(
            "gemini_vision done",
            {"doc": document.doc_name, "fields_emitted": len(emitted)},
        )
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)

    def _extract_pages(self, images: dict[int, bytes]) -> list[tuple[int, dict[str, FieldValue]]]:
        ordered = sorted(images.items())
        if not ordered:
            return []
        workers = min(_MAX_PARALLEL_PAGES, len(ordered))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(lambda item: self._extract_one(*item), ordered))

    def _extract_one(self, page_idx: int, png: bytes) -> tuple[int, dict[str, FieldValue]]:
        response = self._client.generate([self._client.image_part(png), self._prompt])
        parsed = parse_gemini_fields(response, self._catalog)
        fields = {
            name: FieldValue(field=fv.field, value=fv.value, source=f"vision:p{page_idx + 1}")
            for name, fv in parsed.items()
        }
        log.info("gemini_vision page", {"page": page_idx + 1, "fields": len(fields)})
        return page_idx, fields


def build(settings: Settings) -> GeminiVisionAnalyzer:
    client = build_client(
        settings.gemini_model,
        settings.gemini_max_attempts,
        thinking_budget=settings.vision_thinking_budget,
    )
    return GeminiVisionAnalyzer(client=client, dpi=settings.vision_dpi)


def _merge_pages(per_page: list[tuple[int, dict[str, FieldValue]]]) -> dict[str, FieldValue]:
    """Combine per-page field maps. Earlier (lower-index) pages win on conflict.

    Page order is meaningful: the Schedule K-1 cover precedes its attached
    statements, so when two pages claim the same field the cover's value is kept.
    Most fields are page-exclusive, so conflicts are rare.
    """
    merged: dict[str, FieldValue] = {}
    for _page_idx, fields in sorted(per_page):
        for name, value in fields.items():
            merged.setdefault(name, value)
    return merged
