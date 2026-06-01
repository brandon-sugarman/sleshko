"""Strategy manifest — import this module to populate the registry.

Add one register_* call per new strategy. The eval runner imports this once
before build_matrix(), so every registered pair becomes a leaderboard row.

Extraction strategies:
  acroform       — AcroForm widget fields (fillable PDFs only)
  pymupdf_text   — embedded text from all pages, no source bytes
  pymupdf_full   — embedded text + raw PDF bytes (required for gemini_pdf)

Analysis strategies:
  acroform_cover — deterministic field map for the K-1 AcroForm template
  gemini_text    — full-text → Gemini → structured JSON (needs text in IR)
  gemini_pdf     — raw PDF bytes → Gemini native read (needs source_bytes in IR)

See docs/PLANNING.md §8 for the extension guide.
"""

from __future__ import annotations

from analysis import acroform_cover, gemini_pdf, gemini_text
from extraction import acroform, pymupdf_text
from registry import register_analysis, register_extraction

# --- extraction ---
register_extraction(acroform.AcroFormExtractor.name, acroform.build)
register_extraction(pymupdf_text.PyMuPdfTextExtractor.name, pymupdf_text.build)
register_extraction(pymupdf_text.PyMuPdfFullExtractor.name, pymupdf_text.build_with_bytes)

# --- analysis ---
register_analysis(acroform_cover.AcroFormCoverAnalyzer.name, acroform_cover.build)
register_analysis(gemini_text.GeminiTextAnalyzer.name, gemini_text.build)
register_analysis(gemini_pdf.GeminiPdfAnalyzer.name, gemini_pdf.build)
