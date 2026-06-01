"""Thin entry point for the sample-output dumper — logic lives in src/.

Runs the active strategy matrix over PDFs that have no eval-set ground truth
and writes the extracted fields per (config, pairing, PDF) for manual
comparison against the source document. No scoring.

Run using:
    uv run python dump_samples.py                 # all non-eval PDFs
    uv run python dump_samples.py doc_1.pdf        # named PDF(s)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make src/ and the repo root importable when running as `python dump_samples.py`
# (mirrors main.py; pytest uses pyproject.toml [tool.pytest.ini_options] instead).
_repo_root = Path(__file__).resolve().parent
for _p in (_repo_root / "src", _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sample_outputs_runner import main  # noqa: E402

if __name__ == "__main__":
    main()
