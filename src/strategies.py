"""Strategy manifest — import this module to populate the registry.

Add one register_* call per new strategy here. The eval runner imports this
module once before calling build_matrix(), so every registered pair becomes a
leaderboard row automatically.

See docs/PLANNING.md §8 for the worked example and extension rules.
"""

from __future__ import annotations

from analysis import acroform_cover
from extraction import acroform
from registry import register_analysis, register_extraction

register_extraction(acroform.AcroFormExtractor.name, acroform.build)
register_analysis(acroform_cover.AcroFormCoverAnalyzer.name, acroform_cover.build)
