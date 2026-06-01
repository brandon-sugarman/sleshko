from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

_CONFIGURED = False
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    _LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console handler — human-readable
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root.addHandler(console)

    # File sink — one timestamped file per run, kept in logs/
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _LOG_DIR / f"run_{run_ts}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root.addHandler(file_handler)

    _CONFIGURED = True


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
