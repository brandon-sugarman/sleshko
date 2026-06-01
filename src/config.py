from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_MAX_ATTEMPTS = 3
DEFAULT_RENDER_DPI = 200
DEFAULT_PYDANTIC_CHUNK_SIZE = 50


@dataclass(frozen=True)
class Settings:
    pdfs_dir: Path
    eval_set_path: Path
    gemini_model: str
    gemini_max_attempts: int
    render_dpi: int
    pydantic_chunk_size: int


def load_settings(repo_root: Path = _REPO_ROOT) -> Settings:
    """Factory for default configuration. All tunables live here; strategy code
    never inlines model names, DPI, retry counts, or paths.

    The Gemini API key is read from the environment by GeminiClient, not stored
    in Settings.
    """
    return Settings(
        pdfs_dir=repo_root / "pdfs",
        eval_set_path=repo_root / "eval_set.csv",
        gemini_model=DEFAULT_GEMINI_MODEL,
        gemini_max_attempts=DEFAULT_GEMINI_MAX_ATTEMPTS,
        render_dpi=DEFAULT_RENDER_DPI,
        pydantic_chunk_size=DEFAULT_PYDANTIC_CHUNK_SIZE,
    )
