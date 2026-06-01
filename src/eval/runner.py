from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import Settings, load_settings
from domain.field_catalog import FieldSpec, build_catalog
from domain.scoring import DocumentScore, MatrixReport, PipelineScore
from eval.eval_set import ExpectedRecord, load_eval_set
from eval.scorer import score_document
from logger import dump_report, dump_rubric, make_logger
from registry import ANALYSIS_STRATEGIES, EXTRACTION_STRATEGIES, Pipeline, build_matrix

log = make_logger("eval.runner")


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
    import strategies  # noqa: F401 — populates EXTRACTION_STRATEGIES / ANALYSIS_STRATEGIES

    pipelines = build_matrix(settings)
    if not pipelines:
        log.warning("no strategies registered; register extraction/analysis strategies first", {})
        return

    rubric_path = dump_rubric({
        "registered_extraction_strategies": list(EXTRACTION_STRATEGIES),
        "registered_analysis_strategies": list(ANALYSIS_STRATEGIES),
        "pipelines": [
            {"name": p.name, "extraction": p.extraction.name, "analysis": p.analysis.name}
            for p in pipelines
        ],
    })
    log.info("rubric written", {"path": str(rubric_path)})

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
