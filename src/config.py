from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
DEFAULT_GEMINI_MAX_ATTEMPTS = 3
DEFAULT_PYDANTIC_CHUNK_SIZE = 50

# Per-page vision extraction renders pages at this DPI — accuracy matters more
# than latency because the pages are extracted in parallel.
DEFAULT_VISION_DPI = 200

# thinking_budget for Gemini reasoning: 0 disables it, -1 lets the model size
# its own budget (dynamic). Dynamic favors accuracy; the eval runner overrides
# it per config to compare cost vs. accuracy. Applies to gemini-2.5-* only.
DEFAULT_GEMINI_THINKING_BUDGET = -1

DEFAULT_GEMINI_THINKING_LEVEL: str | None = None


@dataclass(frozen=True)
class GeminiSettings:
    """Gemini-only tunables, grouped so extraction/analysis strategies that
    don't call Gemini stay decoupled from provider configuration.

    `thinking_budget` is honored by gemini-2.5-* models; `thinking_level` by
    gemini-3.x models. The two are mutually exclusive at the API, so the
    GeminiClient selects one based on the model family rather than sending both.
    """

    model: str
    max_attempts: int
    thinking_budget: int
    thinking_level: str | None = None


@dataclass(frozen=True)
class Settings:
    pdfs_dir: Path
    eval_set_path: Path
    pydantic_chunk_size: int
    vision_dpi: int
    gemini: GeminiSettings


def load_settings(
    repo_root: Path = _REPO_ROOT,
    gemini_model: str | None = None,
    gemini_thinking_budget: int | None = None,
    gemini_thinking_level: str | None = None,
) -> Settings:
    """Factory for default configuration. All tunables live here; strategy code
    never inlines model names, DPI, retry counts, or paths.

    `gemini_model`, `gemini_thinking_budget`, and `gemini_thinking_level`
    override the defaults so the eval runner can benchmark model/reasoning
    configurations across model families. The Gemini API key is read from the
    environment by GeminiClient, not stored in Settings.
    """
    return Settings(
        pdfs_dir=repo_root / "pdfs",
        eval_set_path=repo_root / "eval_set.csv",
        pydantic_chunk_size=DEFAULT_PYDANTIC_CHUNK_SIZE,
        vision_dpi=DEFAULT_VISION_DPI,
        gemini=GeminiSettings(
            model=gemini_model if gemini_model is not None else DEFAULT_GEMINI_MODEL,
            max_attempts=DEFAULT_GEMINI_MAX_ATTEMPTS,
            thinking_budget=(
                gemini_thinking_budget
                if gemini_thinking_budget is not None
                else DEFAULT_GEMINI_THINKING_BUDGET
            ),
            thinking_level=(
                gemini_thinking_level
                if gemini_thinking_level is not None
                else DEFAULT_GEMINI_THINKING_LEVEL
            ),
        ),
    )
