from __future__ import annotations

from dataclasses import dataclass, field

BBox = tuple[float, float, float, float]
"""(x0, top, x1, bottom) in PDF points, origin top-left."""


@dataclass(frozen=True)
class Word:
    text: str
    bbox: BBox
    page: int


@dataclass(frozen=True)
class FormField:
    name: str
    value: str
    page: int


@dataclass(frozen=True)
class RenderedPage:
    page: int
    image_png: bytes
    dpi: int


@dataclass(frozen=True)
class ExtractedPage:
    """One page of an `ExtractedDocument`.

    Extraction strategies fill only the facets meaningful to their technique:
    a text extractor fills `text` (and maybe `words`); the AcroForm extractor
    fills `form_fields`; a vision extractor fills `rendered`.
    """

    page: int
    text: str = ""
    words: tuple[Word, ...] = ()
    form_fields: tuple[FormField, ...] = ()
    rendered: RenderedPage | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    """The intermediate representation shared by both pipeline layers.

    Produced by an `ExtractionStrategy`, consumed by an `AnalysisStrategy`.
    """

    doc_name: str
    producer: str
    pages: tuple[ExtractedPage, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def words(self) -> tuple[Word, ...]:
        return tuple(w for p in self.pages for w in p.words)

    @property
    def form_fields(self) -> tuple[FormField, ...]:
        return tuple(f for p in self.pages for f in p.form_fields)

    @property
    def rendered_pages(self) -> tuple[RenderedPage, ...]:
        return tuple(p.rendered for p in self.pages if p.rendered is not None)
