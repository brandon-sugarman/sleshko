from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_MAX_ATTEMPTS = 3
DEFAULT_PYDANTIC_CHUNK_SIZE = 50

# Per-page vision extraction renders pages at this DPI and lets the model size
# its own reasoning budget (-1 = dynamic) — accuracy matters more than latency
# because the pages are extracted in parallel.
DEFAULT_VISION_DPI = 200
DEFAULT_VISION_THINKING_BUDGET = -1


@dataclass(frozen=True)
class Settings:
    pdfs_dir: Path
    eval_set_path: Path
    gemini_model: str
    gemini_max_attempts: int
    pydantic_chunk_size: int
    vision_dpi: int
    vision_thinking_budget: int


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
        pydantic_chunk_size=DEFAULT_PYDANTIC_CHUNK_SIZE,
        vision_dpi=DEFAULT_VISION_DPI,
        vision_thinking_budget=DEFAULT_VISION_THINKING_BUDGET,
    )
