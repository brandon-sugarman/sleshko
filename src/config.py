from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    pdfs_dir: Path
    eval_set_path: Path


def load_settings(repo_root: Path = _REPO_ROOT) -> Settings:
    return Settings(
        pdfs_dir=repo_root / "pdfs",
        eval_set_path=repo_root / "eval_set.csv",
    )
