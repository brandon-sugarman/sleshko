from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from config import Settings, load_settings
from domain.extraction_result import ExtractionResult
from domain.field_catalog import FieldSpec, build_catalog
from eval.eval_set import load_eval_set
from registry import build_matrix

_PIPELINE_EXTRACTION = "pymupdf_full"
_PIPELINE_ANALYSIS = "hybrid_max_fidelity"


def main(argv: list[str] | None = None) -> None:
    settings = load_settings()
    import strategies  # noqa: F401 - populates strategy registries

    requested = list(argv if argv is not None else sys.argv[1:])
    pdf_paths = _resolve_pdf_paths(settings, requested)
    pipeline = build_matrix(settings, [_PIPELINE_EXTRACTION], [_PIPELINE_ANALYSIS])[0]
    catalog = list(build_catalog())

    output_dir = _make_output_dir()
    index: list[dict[str, Any]] = []
    for pdf_path in pdf_paths:
        result = pipeline.run(pdf_path.name, pdf_path.read_bytes())
        payload = _build_payload(result, catalog)
        output_path = output_dir / f"{pdf_path.stem}.{_PIPELINE_ANALYSIS}.json"
        output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        index.append({"pdf": pdf_path.name, "output": str(output_path), "fields_emitted": len(result.fields)})

    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"wrote {len(index)} sample output files to {output_dir}")


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


def _make_output_dir() -> Path:
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).resolve().parent.parent / "logs" / f"sample_outputs_{run_ts}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


if __name__ == "__main__":
    main()
