from __future__ import annotations

import re

from domain.document import ExtractedDocument
from domain.extraction_result import FieldValue
from eval.normalize import normalize_int
from k1_codes import field_for_code

# NOTE: regex-based extractor that can be expanded on to be more generalized

_AMOUNT = r"\(?-?\$?[\d,]+(?:\.\d*)?\)?"
_TOTAL_AFTER_RE = re.compile(
    rf"TOTAL TO SCHEDULE K-1,\s*(?:BOX|LINE)\s*(?P<box>\d+),?\s*"
    rf"(?:CODE\s*)?(?P<code>[A-Z]+)\s*\n(?P<amount>{_AMOUNT})",
    re.IGNORECASE,
)
_TOTAL_BEFORE_RE = re.compile(
    rf"(?P<amount>{_AMOUNT})\s*\nTOTAL TO SCHEDULE K-1,\s*(?:BOX|LINE)\s*"
    r"(?P<box>\d+),?\s*(?:CODE\s*)?(?P<code>[A-Z]+)",
    re.IGNORECASE,
)
_BOX_CODE_AMOUNT_RE = re.compile(
    rf"(?:BOX|LINE)\s*(?P<box>\d+),?\s*(?:CODE\s*)?(?P<code>[A-Z]+)"
    rf"[^\n$()\-0-9]{{0,120}}(?P<amount>{_AMOUNT})",
    re.IGNORECASE,
)


def extract_statement_totals(document: ExtractedDocument) -> dict[str, FieldValue]:
    emitted: dict[str, FieldValue] = {}
    for page in document.pages:
        if _is_instruction_page(page.text):
            continue
        matches = list(_TOTAL_AFTER_RE.finditer(page.text))
        matches.extend(_TOTAL_BEFORE_RE.finditer(page.text))
        matches.extend(_BOX_CODE_AMOUNT_RE.finditer(page.text))
        for match in matches:
            box = match.group("box").upper()
            code = match.group("code").upper()
            field = field_for_code(box, code)
            if not field:
                continue
            amount = normalize_int(match.group("amount"))
            if amount:
                emitted[field] = FieldValue(
                    field=field,
                    value=amount,
                    source=f"statement:p{page.page + 1}:box{box}:{code}",
                )
    return emitted


def _is_instruction_page(text: str) -> bool:
    return "Code\nReport on" in text or "See the Partner's Instructions" in text
