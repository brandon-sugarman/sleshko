from __future__ import annotations

import json
import logging
from typing import Any

_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    _CONFIGURED = True


class _StructuredLogger:
    """Thin wrapper so application code logs structured data, not interpolated
    strings (AGENTS §5). One `log = make_logger("tag")` per module.
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
