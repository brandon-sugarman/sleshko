from __future__ import annotations

import re

from domain.extraction_result import RawValue

_EIN_RE = re.compile(r"^\s*(\d{2})-?(\d{7})\s*$")
_NON_NUMERIC = re.compile(r"[,$\s]")


def normalize_int(raw: RawValue) -> int:
    """Coerce a raw cell to an integer under the eval-set conventions:
    commas/`$`/whitespace stripped, parentheses → negative, blank → 0, decimals
    truncated toward zero. Used for integer-typed fields on both sides.
    """

    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    text = raw.strip()
    if not text:
        return 0
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = _NON_NUMERIC.sub("", text)
    if not text or text == "-":
        return 0
    value = int(float(text))
    return -value if negative else value


def normalize_ein(raw: RawValue) -> str:
    text = "" if raw is None else str(raw)
    match = _EIN_RE.match(text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return normalize_text(raw)


def normalize_text(raw: RawValue) -> str:
    """Case-insensitive, whitespace-collapsed comparison form for string fields."""

    if raw is None:
        return ""
    return re.sub(r"\s+", " ", str(raw)).strip().lower()
