from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

_DOC_HEADER = "DOC_NAME"

ExpectedRecord = Mapping[str, str]
"""field name → raw expected value (as written in the CSV)."""


def load_eval_set(path: Path) -> dict[str, ExpectedRecord]:
    """Parse `eval_set.csv` into `{doc_name: {field: raw_value}}`.

    Row 0 is `DOC_NAME,<doc>,<doc>,...`; every later row is
    `<field>,<value>,<value>,...` aligned to those document columns. The gradable
    field set for a document is exactly the field rows present here.
    """

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.reader(handle) if row and row[0].strip()]

    header, *body = rows
    if header[0].strip() != _DOC_HEADER:
        raise ValueError(f"expected first column {_DOC_HEADER!r}, got {header[0]!r}")

    doc_names = [name.strip() for name in header[1:]]
    expected: dict[str, dict[str, str]] = {name: {} for name in doc_names}

    for row in body:
        field = row[0].strip()
        for doc_name, value in zip(doc_names, row[1:], strict=False):
            expected[doc_name][field] = value.strip()

    return {name: record for name, record in expected.items()}
