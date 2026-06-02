from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import NamedTuple

from config import Settings, load_settings
from domain.field_catalog import FieldSpec, build_catalog
from domain.scoring import DocumentScore, MatrixReport, PipelineScore
from eval.eval_set import ExpectedRecord, load_eval_set
from eval.scorer import score_document
from infra.gemini_client import (
    THINKING_DYNAMIC,
    THINKING_LEVEL_HIGH,
    THINKING_LEVEL_LOW,
    THINKING_OFF,
)
from logger import dump_mismatches, dump_pipeline_snapshot, dump_report, make_logger
from registry import ANALYSIS_STRATEGIES, EXTRACTION_STRATEGIES, Pipeline, build_matrix

log = make_logger("eval.runner")


class GeminiConfig(NamedTuple):
    """One benchmarked Gemini configuration. `label` disambiguates pipelines
    that share a strategy pairing but differ only by model/reasoning.

    `thinking_budget` is used by gemini-2.5-* models, `thinking_level` by
    gemini-3.x. Set only the one valid for the family; the client ignores the
    other (sending both to gemini-3.x is a 400).
    """

    label: str
    model: str
    thinking_budget: int | None = None
    thinking_level: str | None = None


# Gemini configs benchmarked against every active strategy pairing.
GEMINI_CONFIGS: list[GeminiConfig] = [
    GeminiConfig("flash/off", "gemini-2.5-flash", thinking_budget=THINKING_OFF),
    GeminiConfig("flash/dyn", "gemini-2.5-flash", thinking_budget=THINKING_DYNAMIC),
    GeminiConfig("pro/dyn", "gemini-2.5-pro", thinking_budget=THINKING_DYNAMIC),
    GeminiConfig("3.1pro/high", "gemini-3.1-pro-preview", thinking_level=THINKING_LEVEL_HIGH),
    GeminiConfig("3.1pro/low", "gemini-3.1-pro-preview", thinking_level=THINKING_LEVEL_HIGH),
    GeminiConfig("3.5flash/high", "gemini-3.5-flash", thinking_level=THINKING_LEVEL_HIGH),
    GeminiConfig("3flash/low", "gemini-3-flash-preview", thinking_level=THINKING_LEVEL_LOW),
]

# Meaningful (extraction, analysis) pairings benchmarked by the matrix. The full
# cartesian product includes invalid combos (e.g. text-only IR feeding native-PDF
# analysis), so the active set is curated here. Shared with sample_outputs_runner
# so the manual-inspection dumps stay in sync with what the eval benchmarks.
ACTIVE_PAIRS: list[tuple[str, str]] = [
    # ("pymupdf_full", "hybrid_max_fidelity"),       # 100% exact, but overfit to 3 docs
    ("pymupdf_full", "gemini_vision_acroform"),    # vision + acroform cover overrides — best generalizable
    ("pymupdf_full", "gemini_vision"),             # pure vision baseline for comparison
    # ("pymupdf_full", "acroform_gemini_selective"), # strong but more false+
    # ("pymupdf_full", "gemini_pdf"), #mid, lower recall
    # ("acroform", "acroform_cover"), #weak recall
    # ("pymupdf_text", "gemini_text"), #worst recall
]


def _load_pdfs(pdfs_dir: Path, doc_names: list[str]) -> dict[str, bytes]:
    return {name: (pdfs_dir / name).read_bytes() for name in doc_names}


def _score_pipeline(
    pipeline: Pipeline,
    pdfs: dict[str, bytes],
    expected: dict[str, ExpectedRecord],
    catalog: dict[str, FieldSpec],
) -> PipelineScore:
    per_doc: list[DocumentScore] = []
    for doc_name, pdf_bytes in pdfs.items():
        try:
            result = pipeline.run(doc_name, pdf_bytes)
            per_doc.append(score_document(result, expected[doc_name], catalog))
        except Exception as exc:
            log.error(
                "pipeline failed — scored as zero",
                {"pipeline": pipeline.name, "doc": doc_name, "error": str(exc)},
            )
            per_doc.append(DocumentScore(doc_name=doc_name, pipeline=pipeline.name, comparisons=()))
    return PipelineScore(pipeline=pipeline.name, per_doc=tuple(per_doc))


def run_matrix(settings: Settings, pipelines: list[Pipeline]) -> MatrixReport:
    """Run every pipeline over every document in the eval set and score each.

    Pipelines run concurrently; the documents within a pipeline run in sequence
    (a single pipeline may hold non-thread-safe LLM/session state).
    """

    expected = load_eval_set(settings.eval_set_path)
    catalog = {spec.name: spec for spec in build_catalog()}
    pdfs = _load_pdfs(settings.pdfs_dir, list(expected))

    log.info("matrix start", {"pipelines": len(pipelines), "documents": len(pdfs)})
    with ThreadPoolExecutor() as pool:
        scores = list(pool.map(lambda p: _score_pipeline(p, pdfs, expected, catalog), pipelines))
    return MatrixReport(scores=tuple(scores))


def main() -> None:
    # Mismatch headers and extracted K-1 values contain non-ASCII (em-dashes,
    # accented names). The default Windows console is cp1252/surrogateescape,
    # which raises on those when stdout is redirected to a file; force UTF-8 so
    # the report prints cleanly. The dumped .txt files are already UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    settings = load_settings()
    import strategies  # noqa: F401 - populates EXTRACTION_STRATEGIES / ANALYSIS_STRATEGIES

    # Benchmark every active pairing under each Gemini config. The strategy
    # clients are built from per-config settings; run_matrix's `settings` only
    # supplies the model-independent eval-set and PDF paths.
    pipelines: list[Pipeline] = []
    for gc in GEMINI_CONFIGS:
        cfg = load_settings(
            gemini_model=gc.model,
            gemini_thinking_budget=gc.thinking_budget,
            gemini_thinking_level=gc.thinking_level,
        )
        for ext, ana in ACTIVE_PAIRS:
            if ext in EXTRACTION_STRATEGIES and ana in ANALYSIS_STRATEGIES:
                pipeline = build_matrix(cfg, [ext], [ana])[0]
                pipelines.append(replace(pipeline, label=gc.label))
    if not pipelines:
        log.warning("no strategies registered; register extraction/analysis strategies first", {})
        return

    snapshot_path = dump_pipeline_snapshot({
        "registered_extraction_strategies": list(EXTRACTION_STRATEGIES),
        "registered_analysis_strategies": list(ANALYSIS_STRATEGIES),
        "gemini_configs": [
            {
                "label": gc.label,
                "model": gc.model,
                "thinking_budget": gc.thinking_budget,
                "thinking_level": gc.thinking_level,
            }
            for gc in GEMINI_CONFIGS
        ],
        "pipelines": [
            {"name": p.name, "label": p.label, "extraction": p.extraction.name, "analysis": p.analysis.name}
            for p in pipelines
        ],
    })
    log.info("pipeline snapshot written", {"path": str(snapshot_path)})

    report = run_matrix(settings, pipelines)
    from eval.report import render_console, render_doc_scores, render_mismatches

    leaderboard = render_console(report)
    per_doc = render_doc_scores(report)
    full_report = leaderboard + "\n\n" + per_doc

    report_path = dump_report(full_report)
    log.info("report written", {"path": str(report_path)})

    # Per-field expected/predicted for every miss — the "what did it actually get
    # wrong" view, ranked best-pipeline-first to match the leaderboard ordering.
    mismatches = "\n\n".join(render_mismatches(s) for s in report.ranked)
    mismatches_path = dump_mismatches(mismatches)
    log.info("mismatches written", {"path": str(mismatches_path)})

    print(leaderboard)
    print()
    print(per_doc)
    print()
    print(mismatches)


if __name__ == "__main__":
    main()
