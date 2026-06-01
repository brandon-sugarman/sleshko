from __future__ import annotations

import re

from domain.document import ExtractedDocument, ExtractedPage, Word
from domain.extraction_result import FieldValue
from eval.normalize import normalize_int

_NUMBER_RE = re.compile(r"^-?\(?\$?[\d,]+(?:\.\d*)?\)?$")
_EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")


def extract_flattened_cover(document: ExtractedDocument) -> dict[str, FieldValue]:
    page = _find_flattened_cover(document.pages)
    if page is None:
        return {}

    emitted: dict[str, FieldValue] = {}
    ein = _EIN_RE.search(page.text)
    if ein:
        emitted["partnership_employer_identification_number"] = FieldValue(
            field="partnership_employer_identification_number",
            value=ein.group(),
            source=f"layout:p{page.page + 1}:ein",
        )

    name = _line_after_ein(page.text)
    if name:
        emitted["partnership_name"] = FieldValue(
            field="partnership_name",
            value=name,
            source=f"layout:p{page.page + 1}:name",
        )

    _emit_amount_near_label(
        emitted,
        "line_5_interest_income",
        page.words,
        label=("interest", "income"),
        source=f"layout:p{page.page + 1}:line5",
    )
    _emit_amount_near_label(
        emitted,
        "line_6a_ordinary_dividends",
        page.words,
        label=("ordinary", "dividends"),
        source=f"layout:p{page.page + 1}:line6a",
    )
    _emit_amount_near_label(
        emitted,
        "ending_capital_account",
        page.words,
        label=("ending", "capital", "account"),
        source=f"layout:p{page.page + 1}:ending_capital",
    )
    return emitted


def _find_flattened_cover(pages: tuple[ExtractedPage, ...]) -> ExtractedPage | None:
    for page in pages:
        text = page.text
        has_partnership_id = "Partnership's employer identification number" in text
        if has_partnership_id and "Part III" in text and not page.form_fields:
            return page
    return None


def _line_after_ein(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for idx, line in enumerate(lines):
        if _EIN_RE.fullmatch(line):
            for candidate in lines[idx + 1 : idx + 4]:
                if candidate and not _NUMBER_RE.fullmatch(candidate):
                    return candidate
    return ""


def _emit_amount_near_label(
    emitted: dict[str, FieldValue],
    field: str,
    words: tuple[Word, ...],
    *,
    label: tuple[str, ...],
    source: str,
) -> None:
    bbox = _find_label_bbox(words, label)
    if bbox is None:
        return
    _x0, y0, x1, y1 = bbox
    label_mid_y = (y0 + y1) / 2
    candidates = [
        (abs(((w.bbox[1] + w.bbox[3]) / 2) - label_mid_y), w.bbox[0], w.text)
        for w in words
        if w.bbox[0] > x1 and abs(((w.bbox[1] + w.bbox[3]) / 2) - label_mid_y) <= 16
        if _is_numeric(w.text)
    ]
    if not candidates:
        return
    value = normalize_int(sorted(candidates)[0][2])
    if value:
        emitted[field] = FieldValue(field=field, value=value, source=source)


def _find_label_bbox(
    words: tuple[Word, ...],
    label: tuple[str, ...],
) -> tuple[float, float, float, float] | None:
    for line in _word_lines(words):
        tokens = [_normalize_token(w.text) for w in line]
        for start in range(0, len(tokens) - len(label) + 1):
            if tuple(tokens[start : start + len(label)]) != label:
                continue
            match = line[start : start + len(label)]
            return (
                min(w.bbox[0] for w in match),
                min(w.bbox[1] for w in match),
                max(w.bbox[2] for w in match),
                max(w.bbox[3] for w in match),
            )
    return None


def _word_lines(words: tuple[Word, ...]) -> list[list[Word]]:
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (round(w.bbox[1]), w.bbox[0])):
        if not lines or abs(lines[-1][0].bbox[1] - word.bbox[1]) > 3:
            lines.append([word])
        else:
            lines[-1].append(word)
    return lines


def _normalize_token(raw: str) -> str:
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def _is_numeric(raw: str) -> bool:
    return bool(_NUMBER_RE.fullmatch(raw.strip()))
