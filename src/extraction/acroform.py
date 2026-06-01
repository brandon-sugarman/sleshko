from __future__ import annotations

import pymupdf

from config import Settings
from domain.document import ExtractedDocument, ExtractedPage, FormField
from logger import make_logger

log = make_logger("extraction.acroform")


class AcroFormExtractor:
    """Reads AcroForm widget fields from fillable PDFs.

    Populates the `form_fields` facet of each `ExtractedPage`. For flattened
    PDFs (no widgets) this produces an empty document — the analysis layer
    will see no form fields and emit nothing (all fields default to 0/"" at
    scoring time).
    """

    name = "acroform"

    def extract(self, doc_name: str, pdf_bytes: bytes) -> ExtractedDocument:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        try:
            producer = doc.metadata.get("producer", "") or ""
            pages: list[ExtractedPage] = []
            for page_idx in range(doc.page_count):
                page = doc.load_page(page_idx)
                fields: list[FormField] = []
                for widget in page.widgets() or []:
                    # Store only the last dotted segment as the field name so
                    # the analysis layer can use short keys like "f1_34[0]".
                    short_name = widget.field_name.split(".")[-1]
                    raw_value = widget.field_value
                    value = str(raw_value).strip() if raw_value is not None else ""
                    fields.append(FormField(name=short_name, value=value, page=page_idx))
                pages.append(ExtractedPage(page=page_idx, form_fields=tuple(fields)))

        finally:
            doc.close()

        total_fields = sum(len(p.form_fields) for p in pages)
        log.info("acroform extract done", {"doc": doc_name, "form_fields": total_fields})
        return ExtractedDocument(doc_name=doc_name, producer=producer, pages=tuple(pages))


def build(settings: Settings) -> AcroFormExtractor:
    return AcroFormExtractor()
