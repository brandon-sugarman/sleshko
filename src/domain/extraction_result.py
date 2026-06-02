from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

FieldName = str
RawValue = int | str | None


@dataclass(frozen=True)
class FieldValue:
    """One extracted field plus where it came from.

    `source` is provenance for debugging and trust, e.g. `acroform:f1_34`,
    `llm:cover_chunk_0`, `coords:p1`, `default_zero`.
    """

    field: FieldName
    value: RawValue
    source: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    """The canonical output of a `Pipeline`: a flat field→value record.

    Intentionally not a `k1_cover_page` / `k1_federal_footnotes` instance — the
    flat shape maps 1:1 onto `eval_set.csv` and lets analysis strategies emit
    only the fields they actually resolved. The field catalog supplies absent
    fields' defaults at scoring time.
    """

    doc_name: str
    pipeline: str
    fields: Mapping[FieldName, FieldValue]

    def get(self, name: FieldName) -> FieldValue | None:
        return self.fields.get(name)


def merge_pages_first_wins(
    per_page: list[tuple[int, dict[FieldName, FieldValue]]],
) -> dict[FieldName, FieldValue]:
    """Combine per-page field maps, keeping the lowest-index page on conflict.

    Page order is meaningful for K-1 packages: the Schedule K-1 cover precedes
    its attached statements, so when two pages claim the same field the cover's
    value wins. Most fields are page-exclusive, so conflicts are rare. Shared by
    the per-page analysis strategies (vision, routed, acroform-selective).
    """
    merged: dict[FieldName, FieldValue] = {}
    for _page_idx, fields in sorted(per_page):
        for name, value in fields.items():
            merged.setdefault(name, value)
    return merged
