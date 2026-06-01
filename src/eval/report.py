from __future__ import annotations

from domain.scoring import DocumentScore, MatchKind, MatrixReport, PipelineScore

_COL_PIPELINE = 44
_HEADER = (
    f"{'PIPELINE':<{_COL_PIPELINE}}"
    f"{'NZ RECALL':>12}"
    f"{'FALSE+':>9}"
    f"{'EXACT':>9}"
    f"{'GRADE':>8}"
)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _grade(nonzero_recall: float, false_positives: int) -> str:
    """Letter grade based on non-zero recall (primary) and false positives (penalty)."""
    fp_penalty = min(false_positives * 0.02, 0.20)
    score = max(0.0, nonzero_recall - fp_penalty)
    if score >= 0.92:
        return "A"
    if score >= 0.80:
        return "B"
    if score >= 0.65:
        return "C"
    if score >= 0.50:
        return "D"
    return "F"


def render_console(report: MatrixReport) -> str:
    """Leaderboard ranked by non-zero recall (primary metric), then fewest false positives."""

    lines = [_HEADER, "-" * len(_HEADER)]
    for score in report.ranked:
        g = _grade(score.nonzero_recall, score.false_positives)
        lines.append(
            f"{score.pipeline:<{_COL_PIPELINE}}"
            f"{_pct(score.nonzero_recall):>12}"
            f"{score.false_positives:>9}"
            f"{_pct(score.exact_accuracy):>9}"
            f"{g:>8}"
        )
    return "\n".join(lines)


def render_doc_scores(report: MatrixReport) -> str:
    """Per-document breakdown for every pipeline — shows where coverage is weak."""

    lines: list[str] = []
    for pipeline_score in report.ranked:
        lines.append(f"\n=== {pipeline_score.pipeline} ===")
        lines.append(
            f"  {'DOCUMENT':<36}"
            f"{'NZ RECALL':>12}"
            f"{'FALSE+':>9}"
            f"{'EXACT':>9}"
            f"{'GRADE':>8}"
        )
        lines.append("  " + "-" * 74)
        for doc in pipeline_score.per_doc:
            g = _grade(doc.nonzero_recall, doc.false_positives)
            lines.append(
                f"  {doc.doc_name:<36}"
                f"{_pct(doc.nonzero_recall):>12}"
                f"{doc.false_positives:>9}"
                f"{_pct(doc.exact_accuracy):>9}"
                f"{g:>8}"
            )
        # Aggregate row
        g = _grade(pipeline_score.nonzero_recall, pipeline_score.false_positives)
        lines.append("  " + "-" * 74)
        lines.append(
            f"  {'TOTAL':<36}"
            f"{_pct(pipeline_score.nonzero_recall):>12}"
            f"{pipeline_score.false_positives:>9}"
            f"{_pct(pipeline_score.exact_accuracy):>9}"
            f"{g:>8}"
        )
    return "\n".join(lines)


def render_mismatches(score: PipelineScore) -> str:
    """Per-field misses for one pipeline — the debugging view."""

    lines: list[str] = [f"# Mismatches — {score.pipeline}"]
    for doc in score.per_doc:
        lines.append(f"\n## {doc.doc_name}")
        lines.extend(_mismatch_lines(doc))
    return "\n".join(lines)


def _mismatch_lines(doc: DocumentScore) -> list[str]:
    misses = [c for c in doc.comparisons if c.kind is not MatchKind.correct]
    if not misses:
        return ["  (all correct)"]
    return [
        f"  [{c.kind.value:>14}] {c.field}: expected={c.expected!r} predicted={c.predicted!r}"
        for c in misses
    ]
