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
from domain.extraction_result import ExtractionResult, FieldValue, merge_pages_first_wins
from domain.field_catalog import build_catalog
from domain.page_roles import select_data_pages
from infra.gemini_client import GeminiClient, build_client, parse_gemini_fields
from infra.pdf_render import render_page_pngs
from logger import make_logger
from prompts.k1_extraction import build_page_text_context, build_vision_page_prompt

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

        per_page = self._extract_pages(images, page_texts)
        emitted = merge_pages_first_wins(per_page)

        log.info(
            "gemini_vision done",
            {"doc": document.doc_name, "fields_emitted": len(emitted)},
        )
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)

    def _extract_pages(
        self, images: dict[int, bytes], page_texts: dict[int, str]
    ) -> list[tuple[int, dict[str, FieldValue]]]:
        ordered = sorted(images.items())
        if not ordered:
            return []
        workers = min(_MAX_PARALLEL_PAGES, len(ordered))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(
                pool.map(
                    lambda item: self._extract_one(item[0], item[1], page_texts.get(item[0], "")),
                    ordered,
                )
            )

    def _extract_one(
        self, page_idx: int, png: bytes, page_text: str
    ) -> tuple[int, dict[str, FieldValue]]:
        contents: list = [self._client.image_part(png)]
        text_context = build_page_text_context(page_text)
        if text_context:
            contents.append(text_context)
        contents.append(self._prompt)
        response = self._client.generate(contents)
        parsed = parse_gemini_fields(response, self._catalog)
        fields = {
            name: FieldValue(field=fv.field, value=fv.value, source=f"vision:p{page_idx + 1}")
            for name, fv in parsed.items()
        }
        log.info("gemini_vision page", {"page": page_idx + 1, "fields": len(fields)})
        return page_idx, fields


def build(settings: Settings) -> GeminiVisionAnalyzer:
    client = build_client(settings.gemini)
    return GeminiVisionAnalyzer(client=client, dpi=settings.vision_dpi)
