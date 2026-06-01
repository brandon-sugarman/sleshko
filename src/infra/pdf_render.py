"""Rasterize PDF pages to PNG bytes for vision-based analysis.

Isolated here so analysis strategies depend on a small, named helper rather than
importing pymupdf and repeating pixmap/zoom boilerplate.
"""

from __future__ import annotations

import pymupdf

_POINTS_PER_INCH = 72


def render_page_pngs(pdf_bytes: bytes, dpi: int, page_indices: list[int] | None = None) -> dict[int, bytes]:
    """Render the requested pages (default: all) to PNG bytes.

    Returns a {page_index: png_bytes} map. Page indices are zero-based and match
    `ExtractedPage.page` so callers can align images with already-extracted text.
    """
    zoom = dpi / _POINTS_PER_INCH
    matrix = pymupdf.Matrix(zoom, zoom)
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        wanted = page_indices if page_indices is not None else list(range(doc.page_count))
        out: dict[int, bytes] = {}
        for idx in wanted:
            if 0 <= idx < doc.page_count:
                pix = doc.load_page(idx).get_pixmap(matrix=matrix, alpha=False)
                out[idx] = pix.tobytes("png")
        return out
    finally:
        doc.close()
