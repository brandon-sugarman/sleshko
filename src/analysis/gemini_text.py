from __future__ import annotations

from config import Settings
from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult
from domain.field_catalog import build_catalog
from infra.gemini_client import GeminiClient, build_client, parse_gemini_fields
from logger import make_logger
from prompts.k1_extraction import build_text_prompt

log = make_logger("analysis.gemini_text")


class GeminiTextAnalyzer:
    """Sends the full extracted text to Gemini and parses a structured JSON response.

    Works best with `pymupdf_text` extraction, which fills the `text` facet on
    every page including supplemental statement pages that have embedded text.
    Scanned/image-only pages (like doc_2 page 1) will be empty, so those fields
    will be missed — use `gemini_pdf` for full coverage on image-heavy docs.
    """

    name = "gemini_text"

    def __init__(self, client: GeminiClient, chunk_size: int) -> None:
        self._client = client
        self._chunk_size = chunk_size
        self._catalog = list(build_catalog())

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        text = document.full_text.strip()
        if not text:
            log.info("no text to analyze", {"doc": document.doc_name})
            return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields={})

        emitted: dict = {}
        fields = self._catalog
        for chunk_start in range(0, len(fields), self._chunk_size):
            chunk = fields[chunk_start : chunk_start + self._chunk_size]
            prompt = build_text_prompt(text, chunk)
            log.info(
                "gemini_text chunk",
                {"doc": document.doc_name, "chunk_start": chunk_start, "chunk_len": len(chunk)},
            )
            response = self._client.generate([prompt])
            emitted.update(parse_gemini_fields(response, chunk))

        log.info("gemini_text done", {"doc": document.doc_name, "fields_emitted": len(emitted)})
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)


def build(settings: Settings) -> GeminiTextAnalyzer:
    client = build_client(settings.gemini)
    return GeminiTextAnalyzer(client=client, chunk_size=settings.pydantic_chunk_size)
