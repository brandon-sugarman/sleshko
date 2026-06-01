"""Thin entry point — all logic lives in src/eval/runner.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Make src/ and the repo root importable when running as `python main.py`
# (pytest uses pyproject.toml [tool.pytest.ini_options] pythonpath instead).
# Run using `uv run python main.py`
_repo_root = Path(__file__).resolve().parent
for _p in (_repo_root / "src", _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from eval.runner import main  # noqa: E402

if __name__ == "__main__":
    main()
