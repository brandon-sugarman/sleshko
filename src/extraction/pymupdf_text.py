from __future__ import annotations

import pymupdf

from config import Settings
from domain.document import ExtractedDocument, ExtractedPage, FormField, Word
from logger import make_logger

log = make_logger("extraction.pymupdf_text")


class PyMuPdfTextExtractor:
    """Extracts embedded text from every PDF page using PyMuPDF.

    Fills the `text` facet of each `ExtractedPage`. Works on both fillable and
    flattened PDFs.
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
                page = doc.load_page(page_idx)
                text = page.get_text("text")
                words = tuple(_to_word(page_idx, raw) for raw in page.get_text("words"))
                form_fields = tuple(_to_form_field(page_idx, widget) for widget in page.widgets() or [])
                pages.append(
                    ExtractedPage(
                        page=page_idx,
                        text=text,
                        words=words,
                        form_fields=form_fields,
                    )
                )
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


def _to_word(page_idx: int, raw: tuple) -> Word:
    x0, y0, x1, y1, text, *_ = raw
    return Word(text=str(text), bbox=(x0, y0, x1, y1), page=page_idx)


def _to_form_field(page_idx: int, widget: pymupdf.Widget) -> FormField:
    short_name = widget.field_name.split(".")[-1]
    raw_value = widget.field_value
    value = str(raw_value).strip() if raw_value is not None else ""
    return FormField(name=short_name, value=value, page=page_idx)
