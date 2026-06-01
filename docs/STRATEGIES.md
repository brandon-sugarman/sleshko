• Here’s the practical OCR/extraction strategy menu for this repo.

  eval_set.csv has 200 target fields across 3 PDFs, but only ~8-21 nonzero fields per doc. That means
  the winning approach is probably not “OCR everything perfectly”; it is “extract sparse K-1 line items
  reliably and default absent fields to zero.”

  Strategies To Test

  1. Native PDF Text Extraction First
     Use pypdf, pdfplumber, or PyMuPDF to extract embedded text before doing OCR.

  Best for:

  - PDFs with selectable text.
  - Fast baseline.
  - Footnotes where text order matters less than exact coordinates.

  Pros:

  - Fast.
  - No image preprocessing.
  - Easier to debug.
  - Often enough for generated tax forms.

  Cons:

  - Fails if PDFs are scanned images.
  - Layout can be scrambled.
  - Tables/boxes may lose spatial context.

  Test:

  - Extract all text per page.
  - Regex for partnership name/EIN.
  - Regex for K-1 line numbers: 1, 2, 3, 4a, 5, 11A, 13H, etc.
  - Fill missing numeric fields as 0.

  2. Coordinate-Based PDF Extraction
     Use pdfplumber or PyMuPDF with word coordinates, not just raw text.

  Best for:

  - Cover page Schedule K-1 boxes.
  - Fields where the line number and value are near each other.
  - Avoiding false matches from instructions/labels.

  Pros:

  - More deterministic than LLM-only.
  - Good for fixed tax form layouts.
  - Lets you crop regions: Part III income boxes, capital account section, EIN/name boxes.

  Cons:

  - Needs per-form layout assumptions.
  - Footnotes may vary too much.

  Test:

  - Extract words with x0, top, x1, bottom.
  - For cover page, crop known areas.
  - Associate values to nearby labels/line numbers.
  - Use explicit zones for:
      - partnership name/EIN
      - Part III lines 1-21
      - capital account fields

  3. Raster OCR With Tesseract
     Render PDF pages to images using PyMuPDF or pdf2image, then run Tesseract.

  Best for:

  - Scanned PDFs.
  - Forms where embedded text extraction fails.
  - Quick local/offline OCR baseline.

  Pros:

  - Free/local.
  - Good enough for clear printed forms.
  - Supports page segmentation modes.

  Cons:

  - Numeric fields can be misread.
  - Needs preprocessing.
  - Tables and form boxes can confuse it.

  Variants to test:

  - DPI: 200, 300, 400.
  - Grayscale + thresholding.
  - Deskew.
  - Tesseract PSM:
      - --psm 6 for blocks of text.
      - --psm 11 for sparse text.
      - --psm 4 for columns.

  - Whitelist for numeric regions: digits, minus sign, comma, decimal.

  4. OCR Cropped Regions Instead Of Whole Pages
     Render page images, crop specific K-1 regions, then OCR each crop separately.

  Best for:

  - Cover page values.
  - Numeric boxes where full-page OCR is noisy.
  - Fixed form layout.

  Pros:

  - Higher accuracy than whole-page OCR.
  - Can use different OCR configs per region.
  - Easier post-processing.

  Cons:

  - Requires coordinates.
  - Different PDF templates may shift slightly.

  Good crops:

  - Partnership name/address box.
  - EIN box.
  - Part III income/deduction/credit boxes.
  - Capital account analysis box.
  - Footnote pages separately.

  5. Table/Layout OCR
     Use tools that preserve tabular layout:

  - paddleocr
  - docTR
  - layoutparser
  - camelot / tabula if PDFs have real vector tables
  - pdfplumber.extract_table

  Best for:

  - Footnote tables.
  - Supplemental statement pages.
  - Multi-column numeric schedules.

  Pros:

  - Better for rows like Line 11A Other income ... 420.
  - Can preserve row-column relationships.

  Cons:

  - Setup complexity.
  - Tax footnotes may not be true tables.
  - Needs normalization logic.

  6. Vision LLM Direct Extraction
     Send page images or rendered PDF pages to a vision-capable model and ask for JSON matching the
     Pydantic schema.

  Best for:

  - Small dataset.
  - Complex footnotes.
  - Fast implementation if API use is allowed.

  Pros:

  - Handles layout variation well.
  - Can reason over labels and footnotes.
  - Can output directly into schema chunks.

  Cons:

  - Cost/latency.
  - Needs validation and retry.
  - May hallucinate nonzero values if prompt is weak.

  Strong prompt pattern:

  - “Extract only values explicitly present.”
  - “If absent, return 0.”
  - “Do not infer.”
  - “Preserve negative signs.”
  - “Return integers, remove commas/decimals.”
  - “Use this exact schema subset.”

  Given pydantic_model.py has schema chunking, this is a natural fit.

  7. Hybrid: Native Text + LLM Structured Parsing
     Extract text with pdfplumber/PyMuPDF, then pass text chunks to an LLM to map into schema fields.

  Best for:

  - Text-based PDFs.
  - Footnotes with variable wording.
  - Avoiding image OCR cost.

  Pros:

  - Cheaper/faster than vision.
  - Easier to inspect.
  - Good for semantic mapping like line_11ZZ_interest_income_us_government.

  Cons:

  - Fails if text extraction is poor.
  - Loses spatial layout.
  - Needs chunking to avoid giant prompts.

  Recommended test:

  - Page 1 cover text into k1_cover_page.
  - Footnote pages into k1_federal_footnotes.
  - Use schema chunks of ~50 fields as already provided.

  8. Hybrid: Deterministic Cover Page + LLM Footnotes
     This is probably the best pragmatic approach.

  Use:

  - Coordinate extraction or OCR crops for cover page.
  - LLM or text+regex for footnotes.

  Why:

  - Cover page is structured and fixed.
  - Footnotes are long-tail, sparse, and semantically messy.
  - eval_set.csv has many fields but few nonzeros, so footnote extraction benefits from semantic
    matching.

  9. Regex/Dictionary-Driven Footnote Parser
     Build a map from schema field names to possible labels and line codes.

  Example:

  - line_11a_other_income_total matches 11A, Other Income, Total.
  - line_13h_investment_interest... matches 13H, Investment Interest Expense.
  - line_15... matches credit labels.

  Pros:

  - Transparent.
  - Good eval reproducibility.
  - No API needed.

  Cons:

  - Labor-intensive.
  - Fragile across wording variations.
  - Large schema means many aliases.

  Best use:

  - As post-processing/verification after OCR or LLM.

  10. Answer-Key-Aware Eval Harness
     Regardless of OCR strategy, build a small runner that outputs:

  - Per-document exact field accuracy.
  - Numeric-only accuracy.
  - Nonzero recall.
  - False positive count.
  - Per-field mismatch table.

  For this eval set, prioritize:

  - nonzero recall: did we find the sparse actual values?
  - false positives: did we hallucinate values where expected is 0?
  - Exact match after normalization.

  Normalize:

  - commas removed
  - parentheses as negative
  - blank/None to 0
  - $ removed
  - decimals rounded or cast if expected integers
  - case-insensitive strings for names
  - EIN normalized as digits plus dash

  Recommended Test Order

  1. PyMuPDF or pdfplumber raw text extraction baseline.
  2. Regex/parser baseline with default 0.
  3. Coordinate extraction for cover page.
  4. Text+LLM schema extraction for footnotes.
  5. Vision LLM fallback for pages where native text is poor.
  6. Tesseract/PaddleOCR only if the PDFs are scanned or native text is unreliable.

  Most Likely Best Architecture

  PDF
   -> detect text quality per page
   -> page 1 cover extraction
        -> coordinate/native text parser
        -> fallback OCR crop or vision
   -> footnote extraction
        -> native text
        -> schema-chunked LLM parser
        -> validation with Pydantic
   -> normalize values
   -> fill missing fields with 0
   -> compare against eval_set.csv

  For this challenge, I’d avoid spending too much time on pure OCR first. Start with native PDF text
  extraction, because these look like generated K-1 PDFs, then add OCR/vision only as fallback.