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


def _field_lines(fields: list[FieldSpec]) -> str:
    return "\n".join(
        f'  "{f.name}": {"integer" if f.type is FieldType.integer else "string"}'
        for f in fields
    )


def build_text_prompt(document_text: str, fields: list[FieldSpec]) -> str:
    """Prompt for the text-based approach: raw extracted text → JSON."""
    return f"""You are extracting specific fields from an IRS Schedule K-1 (Form 1065) tax document.

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
The PDF may contain a cover page, supplemental schedules, and scanned statement pages.

{_RULES}

FIELDS TO EXTRACT (JSON key: expected type):
{{
{_field_lines(fields)}
}}

Read every page of the attached PDF carefully — including any supplemental statement pages.
Return a JSON object containing only the fields you found with non-zero / non-empty values."""
