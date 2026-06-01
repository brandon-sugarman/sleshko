from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from config import Settings, load_settings
from domain.field_catalog import FieldSpec, build_catalog
from domain.scoring import DocumentScore, MatrixReport, PipelineScore
from eval.eval_set import ExpectedRecord, load_eval_set
from eval.scorer import score_document
from infra.gemini_client import THINKING_DYNAMIC, THINKING_OFF
from logger import dump_pipeline_snapshot, dump_report, make_logger
from registry import ANALYSIS_STRATEGIES, EXTRACTION_STRATEGIES, Pipeline, build_matrix

log = make_logger("eval.runner")

# Gemini configs benchmarked against every active strategy pairing. Each tuple
# is (label, model, thinking_budget); the label disambiguates pipelines that
# share a strategy pairing but differ only by Gemini config.
GEMINI_CONFIGS: list[tuple[str, str, int]] = [
    ("flash/off", "gemini-2.5-flash", THINKING_OFF),
    # ("flash/dyn", "gemini-2.5-flash", THINKING_DYNAMIC),
    ("pro/dyn", "gemini-2.5-pro", THINKING_DYNAMIC),
]

# Meaningful (extraction, analysis) pairings benchmarked by the matrix. The full
# cartesian product includes invalid combos (e.g. text-only IR feeding native-PDF
# analysis), so the active set is curated here. Shared with sample_outputs_runner
# so the manual-inspection dumps stay in sync with what the eval benchmarks.
ACTIVE_PAIRS: list[tuple[str, str]] = [
    ("pymupdf_full", "hybrid_max_fidelity"), #best, 100% exact, but overfits
    ("pymupdf_full", "gemini_vision"), #strongest and most realistic, NZ 95.9% recall
    ("pymupdf_full", "acroform_gemini_selective"), #strong, more false+
    ("pymupdf_full", "gemini_pdf"), #mid, lower recall
    ("acroform", "acroform_cover"), #weak recall
    ("pymupdf_text", "gemini_text"), #worst recall
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
        result = pipeline.run(doc_name, pdf_bytes)
        per_doc.append(score_document(result, expected[doc_name], catalog))
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
    settings = load_settings()
    import strategies  # noqa: F401 - populates EXTRACTION_STRATEGIES / ANALYSIS_STRATEGIES

    # Benchmark every active pairing under each Gemini config. The strategy
    # clients are built from per-config settings; run_matrix's `settings` only
    # supplies the model-independent eval-set and PDF paths.
    pipelines: list[Pipeline] = []
    for label, model, budget in GEMINI_CONFIGS:
        cfg = load_settings(gemini_model=model, gemini_thinking_budget=budget)
        for ext, ana in ACTIVE_PAIRS:
            if ext in EXTRACTION_STRATEGIES and ana in ANALYSIS_STRATEGIES:
                pipeline = build_matrix(cfg, [ext], [ana])[0]
                pipelines.append(replace(pipeline, label=label))
    if not pipelines:
        log.warning("no strategies registered; register extraction/analysis strategies first", {})
        return

    snapshot_path = dump_pipeline_snapshot({
        "registered_extraction_strategies": list(EXTRACTION_STRATEGIES),
        "registered_analysis_strategies": list(ANALYSIS_STRATEGIES),
        "gemini_configs": [
            {"label": label, "model": model, "thinking_budget": budget}
            for label, model, budget in GEMINI_CONFIGS
        ],
        "pipelines": [
            {"name": p.name, "label": p.label, "extraction": p.extraction.name, "analysis": p.analysis.name}
            for p in pipelines
        ],
    })
    log.info("pipeline snapshot written", {"path": str(snapshot_path)})

    report = run_matrix(settings, pipelines)
    from eval.report import render_console, render_doc_scores

    leaderboard = render_console(report)
    per_doc = render_doc_scores(report)
    full_report = leaderboard + "\n\n" + per_doc

    report_path = dump_report(full_report)
    log.info("report written", {"path": str(report_path)})

    print(leaderboard)
    print()
    print(per_doc)


if __name__ == "__main__":
    main()
