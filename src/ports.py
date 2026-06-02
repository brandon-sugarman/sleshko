from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult

try:
    from pydantic import BaseModel
except ImportError:  # pydantic is a hard dependency; this only eases tooling before sync
    BaseModel = object  # type: ignore[assignment, misc]

# NOTE: akin to interfaces

@runtime_checkable
class ExtractionStrategy(Protocol):
    """Turn raw PDF bytes into the shared IR. The "OCR"/extraction layer.

    Fill only the IR facets meaningful to the technique (text, words+bbox,
    form_fields, rendered image). Adding a new OCR engine means adding one class
    that satisfies this protocol and registering it — nothing else changes.
    """

    name: str

    def extract(self, doc_name: str, pdf_bytes: bytes) -> ExtractedDocument: ...


@runtime_checkable
class AnalysisStrategy(Protocol):
    """Turn the IR into a flat field→value result. The analysis layer.

    Implementations range from no-LLM deterministic field maps to chunked LLM
    structured output to agentic field-by-field resolution. All satisfy this one
    method, so any analysis composes with any extraction.
    """

    name: str

    def analyze(self, document: ExtractedDocument) -> ExtractionResult: ...


@runtime_checkable
class LlmClient(Protocol):
    """Provider-agnostic LLM port. Concrete adapter (Gemini) lives in infra and
    is the only place the SDK is imported. Per AGENTS §6, the adapter retries
    with backoff and never silently returns empty output.
    """

    def generate_structured(
        self,
        *,
        prompt: str,
        schema: type[BaseModel],
        images: Sequence[bytes] = (),
    ) -> BaseModel: ...
