"""Strategy manifest - import this module to populate the registry.

Add one register_* call per new strategy. The eval runner imports this once
before build_matrix(), so every registered pair becomes a leaderboard row.

Extraction strategies:
  acroform       - AcroForm widget fields (fillable PDFs only)
  pymupdf_text   - embedded text from all pages, no source bytes
  pymupdf_full   - embedded text, coordinates, form fields, and raw PDF bytes

Analysis strategies:
  acroform_cover      - deterministic field map for the K-1 AcroForm template
  gemini_text         - full-text to Gemini structured JSON
  gemini_pdf          - raw PDF bytes to Gemini native read
  gemini_vision       - per-page parallel vision extraction (LLM-forward)
  hybrid_max_fidelity - deterministic K-1 extraction with image fallback

See docs/PLANNING.md for the extension guide.
"""

from __future__ import annotations

from analysis import acroform_cover, gemini_pdf, gemini_text, gemini_vision, hybrid_max_fidelity
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
register_analysis(gemini_vision.GeminiVisionAnalyzer.name, gemini_vision.build)
register_analysis(hybrid_max_fidelity.HybridMaxFidelityAnalyzer.name, hybrid_max_fidelity.build)
