from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

_CONFIGURED = False
_LOGS_ROOT = Path(__file__).resolve().parent.parent / "logs"
_RUN_DIR: Path = _LOGS_ROOT  # updated in _configure to the per-run subfolder


def _configure() -> None:
    global _CONFIGURED, _RUN_DIR
    if _CONFIGURED:
        return

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _RUN_DIR = _LOGS_ROOT / f"run_{run_ts}"
    _RUN_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console handler — human-readable
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root.addHandler(console)

    # File sink — one file per run inside the run subfolder
    log_path = _RUN_DIR / "run.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root.addHandler(file_handler)

    _CONFIGURED = True


def dump_pipeline_snapshot(data: dict[str, Any]) -> Path:
    """Write *data* as pipeline_snapshot.json inside the current run folder."""
    _configure()
    snapshot_path = _RUN_DIR / "pipeline_snapshot.json"
    snapshot_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return snapshot_path


def dump_report(text: str) -> Path:
    """Write the console report as report.txt inside the current run folder."""
    _configure()
    report_path = _RUN_DIR / "report.txt"
    report_path.write_text(text, encoding="utf-8")
    return report_path


def dump_mismatches(text: str) -> Path:
    """Write the per-field mismatch breakdown as mismatches.txt in the run folder."""
    _configure()
    mismatches_path = _RUN_DIR / "mismatches.txt"
    mismatches_path.write_text(text, encoding="utf-8")
    return mismatches_path


class _StructuredLogger:
    """Thin wrapper so application code logs structured data, not interpolated
    strings. One `log = make_logger("tag")` per module.

    Usage: log.info("message", {"key": value})
    """

    def __init__(self, tag: str) -> None:
        self._log = logging.getLogger(tag)

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._emit(logging.INFO, message, data)

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._emit(logging.WARNING, message, data)

    def error(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._emit(logging.ERROR, message, data)

    def _emit(self, level: int, message: str, data: dict[str, Any] | None) -> None:
        suffix = f" {json.dumps(data, default=str)}" if data else ""
        self._log.log(level, "%s%s", message, suffix)


def make_logger(tag: str) -> _StructuredLogger:
    _configure()
    return _StructuredLogger(tag)
