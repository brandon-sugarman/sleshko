from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic_model import k1_cover_page, k1_federal_footnotes

Section = Literal["cover_page", "footnotes"]


class FieldType(StrEnum):
    integer = "integer"
    text = "text"


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: FieldType
    section: Section

    @property
    def zero_default(self) -> int | str:
        return 0 if self.type is FieldType.integer else ""


def _specs_for(model: type, section: Section) -> list[FieldSpec]:
    specs: list[FieldSpec] = []
    for name, info in model.model_fields.items():
        ftype = FieldType.integer if info.annotation is int else FieldType.text
        specs.append(FieldSpec(name=name, type=ftype, section=section))
    return specs


def build_catalog() -> tuple[FieldSpec, ...]:
    """The full target-field universe and each field's type.

    Derived from the challenge pydantic models so the field set stays in sync
    with the provided schema. Drives the absent→0 (int) / absent→"" (text)
    defaulting applied during scoring.
    """

    return tuple(
        _specs_for(k1_cover_page, "cover_page")
        + _specs_for(k1_federal_footnotes, "footnotes")
    )
