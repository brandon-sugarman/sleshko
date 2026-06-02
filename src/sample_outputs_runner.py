"""

Run via the dump_samples.py entry point at the repo root:
    uv run python dump_samples.py                 # all non-eval PDFs
    uv run python dump_samples.py some_doc.pdf     # named PDF(s)
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from config import Settings, load_settings
from domain.extraction_result import ExtractionResult
from domain.field_catalog import FieldSpec, build_catalog
from eval.eval_set import load_eval_set
from eval.runner import ACTIVE_PAIRS, GEMINI_CONFIGS
from registry import (
    ANALYSIS_STRATEGIES,
    EXTRACTION_STRATEGIES,
    Pipeline,
    build_matrix,
)


def main(argv: list[str] | None = None) -> None:
    base_settings = load_settings()
    import strategies  # noqa: F401 - populates strategy registries

    requested = list(argv if argv is not None else sys.argv[1:])
    pdf_paths = _resolve_pdf_paths(base_settings, requested)
    pipelines = _build_pipelines()
    catalog = list(build_catalog())

    output_dir = _make_output_dir()
    index: list[dict[str, Any]] = []
    for pdf_path in pdf_paths:
        pdf_bytes = pdf_path.read_bytes()
        for pipeline in pipelines:
            result = pipeline.run(pdf_path.name, pdf_bytes)
            payload = _build_payload(result, catalog)
            output_path = output_dir / f"{pdf_path.stem}.{_slug(pipeline.name)}.json"
            output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            index.append({
                "pdf": pdf_path.name,
                "pipeline": pipeline.name,
                "output": str(output_path),
                "fields_emitted": len(result.fields),
            })

    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"wrote {len(index)} sample output files to {output_dir}")


def _build_pipelines() -> list[Pipeline]:
    """Every Gemini config x active pairing, matching the eval runner."""
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
    return pipelines


def _resolve_pdf_paths(settings: Settings, requested: list[str]) -> list[Path]:
    if requested:
        return [_resolve_pdf_path(settings.pdfs_dir, item) for item in requested]

    eval_docs = set(load_eval_set(settings.eval_set_path))
    paths = sorted(path for path in settings.pdfs_dir.glob("*.pdf") if path.name not in eval_docs)
    if paths:
        return paths
    return sorted(settings.pdfs_dir.glob("*.pdf"))


def _build_payload(result: ExtractionResult, catalog: list[FieldSpec]) -> dict[str, Any]:
    sections: dict[str, dict[str, Any]] = {"cover_page": {}, "footnotes": {}}
    flat_fields: dict[str, Any] = {}
    for spec in catalog:
        emitted = result.get(spec.name)
        value = emitted.value if emitted is not None else spec.zero_default
        field_payload = {
            "value": value,
            "type": spec.type.value,
            "emitted": emitted is not None,
            "source": emitted.source if emitted is not None else "default",
        }
        sections[spec.section][spec.name] = field_payload
        flat_fields[spec.name] = value

    return {
        "doc_name": result.doc_name,
        "pipeline": result.pipeline,
        "fields_emitted": len(result.fields),
        "pydantic_model_shape": sections,
        "flat_field_values": flat_fields,
    }


def _resolve_pdf_path(pdfs_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = pdfs_dir / path
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _slug(pipeline_name: str) -> str:
    """Make a pipeline name safe for a filename (drops '[', ']', '/', spaces)."""
    cleaned = pipeline_name.replace("[", "").replace("]", "").replace(" + ", "+")
    return cleaned.replace("/", "-").replace(" ", "_")


def _make_output_dir() -> Path:
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).resolve().parent.parent / "logs" / f"sample_outputs_{run_ts}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


if __name__ == "__main__":
    main()
