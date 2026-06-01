from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MatchKind(StrEnum):
    correct = "correct"
    wrong = "wrong"
    false_positive = "false_positive"
    false_negative = "false_negative"
    missing = "missing"


@dataclass(frozen=True)
class FieldComparison:
    """expected/predicted are post-normalization values (int or str)."""

    field: str
    expected: int | str
    predicted: int | str | None
    kind: MatchKind

    @property
    def expected_nonzero(self) -> bool:
        return self.expected not in (0, "")


@dataclass(frozen=True)
class DocumentScore:
    doc_name: str
    pipeline: str
    comparisons: tuple[FieldComparison, ...]

    def _count(self, kind: MatchKind) -> int:
        return sum(1 for c in self.comparisons if c.kind is kind)

    @property
    def nonzero_total(self) -> int:
        return sum(1 for c in self.comparisons if c.expected_nonzero)

    @property
    def nonzero_correct(self) -> int:
        return sum(1 for c in self.comparisons if c.expected_nonzero and c.kind is MatchKind.correct)

    @property
    def nonzero_recall(self) -> float:
        return self.nonzero_correct / self.nonzero_total if self.nonzero_total else 1.0

    @property
    def false_positives(self) -> int:
        return self._count(MatchKind.false_positive)

    @property
    def exact_accuracy(self) -> float:
        total = len(self.comparisons)
        return self._count(MatchKind.correct) / total if total else 1.0


@dataclass(frozen=True)
class PipelineScore:
    """A pipeline's results aggregated across all documents."""

    pipeline: str
    per_doc: tuple[DocumentScore, ...]

    @property
    def nonzero_recall(self) -> float:
        correct = sum(d.nonzero_correct for d in self.per_doc)
        total = sum(d.nonzero_total for d in self.per_doc)
        return correct / total if total else 1.0

    @property
    def false_positives(self) -> int:
        return sum(d.false_positives for d in self.per_doc)

    @property
    def exact_accuracy(self) -> float:
        correct = sum(d._count(MatchKind.correct) for d in self.per_doc)
        total = sum(len(d.comparisons) for d in self.per_doc)
        return correct / total if total else 1.0


@dataclass(frozen=True)
class MatrixReport:
    """Every pipeline scored. Ranked by non-zero recall (the primary metric)."""

    scores: tuple[PipelineScore, ...]

    @property
    def ranked(self) -> tuple[PipelineScore, ...]:
        return tuple(
            sorted(self.scores, key=lambda s: (s.nonzero_recall, -s.false_positives), reverse=True)
        )
