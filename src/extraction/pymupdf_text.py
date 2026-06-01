from __future__ import annotations

import pymupdf

from config import Settings
from domain.document import ExtractedDocument, ExtractedPage
from logger import make_logger

log = make_logger("extraction.pymupdf_text")


class PyMuPdfTextExtractor:
    """Extracts embedded text from every PDF page using PyMuPDF.

    Fills the `text` facet of each `ExtractedPage`. Works on both fillable and
    flattened PDFs. Important characteristics of the sample set:
      - doc_2 page 2: a statement page rendered as a raster image — text will
        be empty; use gemini_pdf analysis to read it.
      - doc_3 pages 1-2: transmittal sheet and cover letter (not K-1 data).
      - doc_3 page 3: the actual K-1 cover (not the first page).
      - doc_3 page 7: generic IRS instruction/code page — 7 000+ chars of
        non-taxpayer text that can cause LLM hallucination if not filtered.
        The gemini_text prompt explicitly instructs Gemini to ignore such pages.
    """

    name = "pymupdf_text"

    def __init__(self, store_source: bool = False) -> None:
        # store_source=True preserves raw PDF bytes in ExtractedDocument so a
        # downstream gemini_pdf analyzer can send them natively to Gemini.
        self._store_source = store_source

    def extract(self, doc_name: str, pdf_bytes: bytes) -> ExtractedDocument:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        try:
            producer = doc.metadata.get("producer", "") or ""
            pages: list[ExtractedPage] = []
            for page_idx in range(doc.page_count):
                text = doc.load_page(page_idx).get_text("text")
                pages.append(ExtractedPage(page=page_idx, text=text))
        finally:
            doc.close()

        total_chars = sum(len(p.text) for p in pages)
        log.info(
            "pymupdf_text extract done",
            {"doc": doc_name, "pages": len(pages), "total_chars": total_chars},
        )
        return ExtractedDocument(
            doc_name=doc_name,
            producer=producer,
            pages=tuple(pages),
            source_bytes=pdf_bytes if self._store_source else None,
        )


def build(settings: Settings) -> PyMuPdfTextExtractor:
    return PyMuPdfTextExtractor(store_source=False)


class PyMuPdfFullExtractor(PyMuPdfTextExtractor):
    """Same as PyMuPdfTextExtractor but stores raw PDF bytes in source_bytes.

    Required by gemini_pdf analysis, which sends the original bytes to Gemini
    natively so it can read image-only pages (e.g. scanned supplement pages).
    """

    name = "pymupdf_full"

    def __init__(self) -> None:
        super().__init__(store_source=True)


def build_with_bytes(settings: Settings) -> PyMuPdfFullExtractor:
    """Factory variant that preserves raw PDF bytes for gemini_pdf analysis."""
    return PyMuPdfFullExtractor()
