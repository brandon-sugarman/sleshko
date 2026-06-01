from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from config import Settings
from domain.extraction_result import ExtractionResult
from ports import AnalysisStrategy, ExtractionStrategy

# Exposed so runner and other modules can check registration without re-importing.

ExtractionFactory = Callable[[Settings], ExtractionStrategy]
AnalysisFactory = Callable[[Settings], AnalysisStrategy]

EXTRACTION_STRATEGIES: dict[str, ExtractionFactory] = {}
ANALYSIS_STRATEGIES: dict[str, AnalysisFactory] = {}


def register_extraction(name: str, factory: ExtractionFactory) -> None:
    EXTRACTION_STRATEGIES[name] = factory


def register_analysis(name: str, factory: AnalysisFactory) -> None:
    ANALYSIS_STRATEGIES[name] = factory


@dataclass(frozen=True)
class Pipeline:
    """One extraction strategy paired with one analysis strategy.

    `label` distinguishes otherwise-identical strategy pairings that run under
    different Gemini configs in the same matrix (e.g. "flash/off" vs "pro/dyn").
    """

    extraction: ExtractionStrategy
    analysis: AnalysisStrategy
    label: str = ""

    @property
    def name(self) -> str:
        base = f"{self.extraction.name} + {self.analysis.name}"
        return f"[{self.label}] {base}" if self.label else base

    def run(self, doc_name: str, pdf_bytes: bytes) -> ExtractionResult:
        document = self.extraction.extract(doc_name, pdf_bytes)
        result = self.analysis.analyze(document)
        # Stamp the full "extraction + analysis" name so DocumentScore is traceable.
        if result.pipeline != self.name:
            return ExtractionResult(doc_name=result.doc_name, pipeline=self.name, fields=result.fields)
        return result


def build_matrix(
    settings: Settings,
    extraction_names: list[str] | None = None,
    analysis_names: list[str] | None = None,
) -> list[Pipeline]:
    """Cartesian product of selected extraction × analysis strategies. With no
    selection, builds every registered pairing.
    """

    ext = extraction_names or list(EXTRACTION_STRATEGIES)
    ana = analysis_names or list(ANALYSIS_STRATEGIES)
    return [
        Pipeline(EXTRACTION_STRATEGIES[e](settings), ANALYSIS_STRATEGIES[a](settings))
        for e in ext
        for a in ana
    ]
