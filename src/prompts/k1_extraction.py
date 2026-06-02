"""Prompt builders for K-1 field extraction.

Keeping prompts in a dedicated module lets us tune wording without touching
strategy logic, and makes it easy to A/B test prompt variants.
"""

from __future__ import annotations

from domain.field_catalog import FieldSpec, FieldType

_RULES = """
EXTRACTION RULES (follow exactly):
1. Extract ONLY values that appear explicitly in the document. Do NOT infer or calculate.
2. Integers: strip commas, dollar signs, and whitespace. Parentheses mean negative: (1,234) → -1234.
3. Text fields: return the literal text as written (names, EINs, codes).
4. If a field is absent or blank: omit it from your response entirely.
5. NEVER emit a non-zero integer unless that exact number appears in the document for that field.
6. Return ONLY a valid JSON object — no markdown fences, no explanation.
""".strip()

# K-1 packages often include non-data pages mixed in with the real content.
# Gemini must be told to ignore them, otherwise it hallucinates values from
# generic IRS instructions, cover letters, and transmittal sheets.
_PAGE_TYPE_GUIDANCE = """
PAGE TYPE GUIDANCE:
The document may contain several page types — only extract data from the relevant pages:
  - IGNORE: mailing/transmittal cover sheets (recipient address, "SAMPLE" watermarks)
  - IGNORE: cover letters (explanatory prose, "please replace your K-1" language)
  - IGNORE: generic IRS instruction/code pages (tables of box codes and where to report them,
            starting with headings like "Code", "Report on", line-by-line instructions)
  - EXTRACT FROM: the actual K-1 cover page (IRS Schedule K-1 Form 1065 with Part I/II/III boxes)
  - EXTRACT FROM: attached statement pages (supplemental detail for "SEE STMT" items)
  - EXTRACT FROM: formal footnote pages (narrative notes directly referencing K-1 line items)

Note: the actual K-1 cover page is not always the first page in the PDF.
""".strip()


def _field_lines(fields: list[FieldSpec]) -> str:
    return "\n".join(
        f'  "{f.name}": {"integer" if f.type is FieldType.integer else "string"}'
        for f in fields
    )


def build_text_prompt(document_text: str, fields: list[FieldSpec]) -> str:
    """Prompt for the text-based approach: raw extracted text → JSON."""
    return f"""You are extracting specific fields from an IRS Schedule K-1 (Form 1065) tax document.

{_PAGE_TYPE_GUIDANCE}

{_RULES}

FIELDS TO EXTRACT (JSON key: expected type):
{{
{_field_lines(fields)}
}}

DOCUMENT TEXT:
---
{document_text}
---

Return a JSON object containing only the fields you found with non-zero / non-empty values."""


def build_pdf_prompt(fields: list[FieldSpec]) -> str:
    """Prompt for the native-PDF approach: Gemini reads the attached PDF directly."""
    return f"""You are extracting specific fields from the attached IRS Schedule K-1 (Form 1065) PDF.

{_PAGE_TYPE_GUIDANCE}

{_RULES}

FIELDS TO EXTRACT (JSON key: expected type):
{{
{_field_lines(fields)}
}}

Read every relevant page of the attached PDF carefully.
Return a JSON object containing only the fields you found with non-zero / non-empty values."""


# Rules specific to reading ONE page in isolation. The biggest failure mode of
# whole-document extraction on flattened K-1s is binding a number to the wrong
# field because labels and values are far apart in the text stream; isolating a
# single page image and forbidding cross-page inference removes that ambiguity.
_VISION_PAGE_RULES = """
EXTRACTION RULES (follow exactly):
1. This is ONE page of a larger K-1 package. Extract ONLY values printed on THIS page.
2. If this page is a cover letter, FAQ, transmittal sheet, or generic IRS instruction
   page — or has no taxpayer-specific amounts — return an empty object: {}.
3. Read a value only when its line number / label is printed next to it on this page.
   Do NOT infer, calculate, or carry values over from another page.
4. Each printed amount maps to at most one field. Never reuse the same number for
   multiple fields, and never split a label's value across unrelated fields.
5. Extract only from labeled data rows or boxes. Ignore amounts that appear inside
   explanatory sentences, footnote prose, or notes that merely mention a box/line
   number (e.g. "...included in the net amount reported in Box 1 and Box 13V...").
6. Integers: strip commas and dollar signs. Parentheses or a leading minus mean
   negative: (1,234) -> -1234. A value shown as a reduction (e.g. withdrawals &
   distributions in the capital account) is negative.
7. Text fields (names, EINs, codes): copy the characters exactly as printed.
8. For "*_logic" text fields: fill only with a full descriptive clause if one is
   printed. Never put a bare code letter (like "V" or "Z") in a logic field.
9. Omit absent or blank fields entirely. Never emit a zero.
10. Return ONLY a valid JSON object — no markdown fences, no commentary.
""".strip()


def build_vision_page_prompt(fields: list[FieldSpec]) -> str:
    """Prompt for per-page vision extraction: one rendered page image → JSON."""
    return f"""You are extracting fields from a single rendered page of an IRS Schedule K-1
(Form 1065) tax package shown as an image.

{_VISION_PAGE_RULES}

FIELDS TO EXTRACT (JSON key: expected type):
{{
{_field_lines(fields)}
}}

Return a JSON object containing only the fields printed on this page with
non-zero / non-empty values, or {{}} if this page has none."""


def build_page_text_context(page_text: str) -> str:
    """Advisory embedded-text-layer block to accompany a rendered page image.

    The rasterized image stays authoritative because scanned statement pages
    carry little or no text layer. When a text layer is present it lets Gemini
    read the exact digits, EINs, and codes that rasterization renders
    ambiguously — but reading order in flattened K-1s is scrambled, so the text
    is explicitly advisory and must not be used to pair labels with values.

    Returns "" when there is no usable text, so callers can omit it entirely.
    """
    text = page_text.strip()
    if not text:
        return ""
    return (
        "EMBEDDED TEXT LAYER for this page (advisory only). The image above is "
        "authoritative for which value belongs to which field. Use this text only "
        "to read exact digits, EINs, and codes that are hard to make out in the "
        "image. Its reading order may be scrambled, so never infer field/value "
        "pairings from it:\n"
        f"{text}"
    )
