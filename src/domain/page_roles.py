"""Classify K-1 package pages so vision analysis skips obvious boilerplate.

K-1 PDFs interleave the real Schedule K-1 form and its attached statements with
cover letters, transmittal sheets, generic IRS instruction pages, and multi-page
FAQs. Sending boilerplate to an LLM wastes tokens and invites hallucinated
values, so vision analysis prefers to skip it.

The filter is deliberately *exclusion-based*: a page is kept unless it is clearly
boilerplate. This generalizes to unfamiliar layouts — a data page in a format we
have never seen is included by default rather than dropped for lacking an
expected keyword. Selection is only a precision/cost optimization anyway: the
per-page prompt still self-rejects any page that turns out to carry no amounts.
"""

from __future__ import annotations

import re

# Phrases that mark a page as boilerplate. These are issuer-agnostic: cover
# letters, FAQs, and IRS instruction pages across filers share this vocabulary.
_BOILERPLATE_MARKERS = (
    "dear unitholder",
    "dear limited partner",
    "dear shareholder",
    "frequently asked questions",
    "tax reporting package",
    "income tax reporting package",
    "table of contents",
)

# Generic IRS instruction/code pages are tables of "Code | Report on ..." rows.
_INSTRUCTION_MARKERS = (
    "code\nreport on",
    "see the partner's instructions",
    "list of codes and references",
)

_QA_LINE_RE = re.compile(r"\n\s*[QA][\.\)]\s")
_MIN_QA_LINES_FOR_FAQ = 4


def is_boilerplate_page(text: str) -> bool:
    """True if a page is clearly a letter, FAQ, transmittal, or instruction page."""
    low = text.lower()
    if any(marker in low for marker in _BOILERPLATE_MARKERS):
        return True
    if any(marker in low for marker in _INSTRUCTION_MARKERS):
        return True
    return len(_QA_LINE_RE.findall(text)) >= _MIN_QA_LINES_FOR_FAQ


def select_data_pages(page_texts: dict[int, str]) -> list[int]:
    """Return zero-based indices of pages worth extracting, sorted.

    Keeps every page that is not clearly boilerplate. If that leaves nothing
    (e.g. a single-page scan with no text layer to classify), falls back to all
    pages so the LLM still gets a chance rather than the pipeline emitting zero.
    """
    kept = sorted(idx for idx, text in page_texts.items() if not is_boilerplate_page(text))
    return kept or sorted(page_texts)
