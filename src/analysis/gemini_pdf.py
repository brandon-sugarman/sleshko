from __future__ import annotations

from config import Settings
from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult
from domain.field_catalog import build_catalog
from infra.gemini_client import GeminiClient, build_client, parse_gemini_fields
from logger import make_logger
from prompts.k1_extraction import build_pdf_prompt

log = make_logger("analysis.gemini_pdf")


class GeminiPdfAnalyzer:
    """Sends the raw PDF bytes natively to Gemini — no text pre-extraction.

    Handles every page type present in the K-1 sample set:
      - fillable AcroForm cover pages (doc_1, doc_2 page 1)
      - attached statement pages rendered as raster images (doc_2 page 2)
      - flattened multi-page packages with transmittal sheets and cover letters
        where the actual K-1 cover may not be the first page (doc_3 page 3)
      - generic IRS instruction pages that should be ignored (doc_3 page 7)

    Requires an extractor that sets `ExtractedDocument.source_bytes`; use the
    `pymupdf_full` extraction strategy (same as `pymupdf_text` but with bytes).

    Uses a single call per document (no chunking) because Gemini reads the full
    PDF in one shot and the field list fits comfortably in its context window.
    """

    name = "gemini_pdf"

    def __init__(self, client: GeminiClient) -> None:
        self._client = client
        self._catalog = list(build_catalog())

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        if document.source_bytes is None:
            raise ValueError(
                "gemini_pdf requires source_bytes — use 'pymupdf_full' extraction strategy"
            )

        prompt = build_pdf_prompt(self._catalog)
        pdf_part = self._client.pdf_part(document.source_bytes)

        log.info("gemini_pdf call", {"doc": document.doc_name, "bytes": len(document.source_bytes)})
        response = self._client.generate([pdf_part, prompt])
        emitted = parse_gemini_fields(response, self._catalog)

        log.info("gemini_pdf done", {"doc": document.doc_name, "fields_emitted": len(emitted)})
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)


def build(settings: Settings) -> GeminiPdfAnalyzer:
    client = build_client(settings.gemini)
    return GeminiPdfAnalyzer(client=client)
