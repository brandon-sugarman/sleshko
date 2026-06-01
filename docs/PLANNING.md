# K-1 Extraction Pipeline — Architecture

This document is the source of truth for the design. `STRATEGIES.md` is the
*menu* of extraction/analysis techniques; this document is the *architecture*
that lets us implement, compose, and benchmark any of them.

---

## 1. The thesis

`eval_set.csv` has ~200 target fields across 3 PDFs, but only **8–21 non-zero
fields per document**. The win condition is therefore not "OCR everything
perfectly" — it is:

> **Find the sparse non-zero K-1 line items reliably, and don't hallucinate
> values into the ~180 fields that are zero.**

This reframes the whole project around two metrics:

- **Non-zero recall** — of the values that are actually present, how many did we find?
- **False positives** — how often did we emit a non-zero/non-empty value where the answer is 0/blank?

Key Guidance:

- Use whatever you want to extract; you **don't** have to use the preset pydantic model.
- **Accuracy is the biggest** thing.
- **Non-zero accuracy is most important; watch false positives.**
- **Don't just put everything in `main.py`.**
- **Overengineering can be bad** — e.g. don't hand-craft brittle regex to fit the eval.
- Bonus thought: **bounding boxes / layout mechanics.**

---

## 2. Two composable layers

```
                 ┌───────────────────────────────────────────────┐
   PDF bytes ──► │  ExtractionStrategy                            │ ──► ExtractedDocument (IR)
                 │  "turn the PDF into something analysable"      │
                 │  acroform · native-text · coordinates ·        │
                 │  rendered-image · OCR · ...                    │
                 └───────────────────────────────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────────┐
   IR ─────────► │  AnalysisStrategy                              │ ──► ExtractionResult (flat field→value)
                 │  "turn the IR into schema fields"              │
                 │  deterministic field-map · text+LLM (chunked) ·│
                 │  vision-LLM · agentic field-by-field · ...     │
                 └───────────────────────────────────────────────┘
```

A **Pipeline** is one `ExtractionStrategy` paired with one `AnalysisStrategy`.
The two layers are independent: any extraction can feed any analysis, as long as
the analysis only consumes IR fields the extraction actually produced (the IR is
"fill what's meaningful", so analyzers declare/expect what they read).

---

## 3. The input regimes (measured, not assumed)

| | doc_1 | doc_2 | doc_3 |
|---|---|---|---|
| Pages | 4 | 2 | 7 |
| AcroForm fields | 111 | 111 | **0 (flattened)** |
| Native text layer | yes | yes | yes |
| EIN present in form fields | `23-333333` | `12-3456789` | n/a |

doc_1 / doc_2 are the **official IRS fillable 1065 Schedule K-1** — identical
field template (`f1_34`→line 1, `Line13=H`+`f1_55`→line 13H, etc.). In both,
the K-1 cover page is page 1 and is deterministically extractable at
near-100% fidelity.

doc_3 is flattened and multi-sectioned: page 1 is a mailing/transmittal sheet,
page 2 is a cover letter, and the actual K-1 cover page is page 3, followed by
statement and footnote material.

The attached pages are not uniform across files: doc_1/doc_2 mostly contain
supporting statement breakdowns, while doc_3 includes formal narrative
"Schedule K-1 Footnotes" pages plus a generic IRS instruction/code page.

---

## 4. The extraction IR — `ExtractedDocument`

The shared contract between the two layers. Extractors fill **only what's
meaningful** for their technique (mirrors the prior service's `Locator`):

```
ExtractedDocument
  doc_name: str
  producer: str                 # which extraction strategy made this
  pages: tuple[ExtractedPage]
  notes: tuple[str]

ExtractedPage
  page: int
  text: str                     # native-text / OCR extractors
  words: tuple[Word]            # coordinate extractors (text + bbox)
  form_fields: tuple[FormField] # acroform extractor
  rendered: RenderedPage | None # vision extractors (PNG bytes + dpi)
```

- Text extractor fills `text` (and `words`).
- AcroForm extractor fills `form_fields`.
- Vision/render extractor fills `rendered`.
- A "rich" extractor may fill several at once (e.g. PyMuPDF gives text + words + form_fields cheaply).

Analysis strategies read whichever facet they need. If a pairing is
nonsensical (vision analyzer + a text-only IR with no `rendered`), the analyzer
returns an empty/defaulted result and the harness records it — a real datapoint,
not a crash.

---

## 5. The output — `ExtractionResult`

Canonical artifact is a **flat mapping of `field_name → FieldValue`**, where
`FieldValue` carries the value plus provenance (`acroform:f1_34`,
`llm:cover_chunk_0`, `default_zero`). We do **not** require producing
`k1_cover_page` / `k1_federal_footnotes` instances

The pydantic models are still useful, in two narrow roles:

1. **Field catalog** (`domain/field_catalog.py`) — introspected for the field
   universe and each field's type (int vs str/"logic"). This drives the
   absent→0 rule for integers and absent→"" for text.
2. **LLM structured-output schema** — an analysis strategy *may* use the
   provided `create_chunked_models` (50 fields/chunk) as the response schema for
   a Gemini call. That's an internal implementation choice of that strategy, not
   part of the pipeline's output contract.

`eval_set.csv` defines the **gradable** key set (a subset of the catalog — it
omits the `*_logic` string fields and some tail footnote fields). Catalog =
types; eval set = what gets scored.

---

## 6. The tester (eval harness) — the centerpiece

Goal: **run all my strategies simultaneously, pairing extraction with analysis,
and see performance side by side.**

```
src/eval/
  eval_set.py   # load eval_set.csv → {doc_name: {field: raw_value}}
  normalize.py  # value normalization (commas, parens→neg, $, blank→0, EIN, case)
  scorer.py     # ExtractionResult × expected → DocumentScore
  runner.py     # StrategyMatrix: every Pipeline × every PDF → scores (concurrent)
  report.py     # render the matrix as a console/markdown table, ranked
```

### Metrics (ranked by importance)

1. **Non-zero accuracy / recall** *(primary)*: over fields
   whose expected value is non-zero/non-empty, fraction predicted correctly.
2. **False positives** *(secondary)*: count of fields where expected is 0/blank but
   we predicted non-zero/non-empty. Punishes hallucination; an all-zeros analyzer
   scores 0 false positives but also ~0 non-zero recall — the two metrics together
   make a degenerate strategy obvious.
3. **Exact accuracy** *(tertiary)*: fraction of all gradable fields matched
   exactly after normalization. Flattered by the many trivially-zero fields, so
   reported but never the headline.

> **NOTE — non-zero accuracy is the metric that matters most for this challenge,
> and false positives are how a lazy "predict 0 everywhere" strategy is exposed.**
> The report ranks pipelines by non-zero accuracy.

### Normalization (applied to both sides before comparison)

commas removed · parentheses → negative · `$` stripped · blank/None → 0 (int
fields) · decimals cast to int where the field is an int · case-insensitive for
names/strings · EIN normalized to `digits-dash`. Lives in one module so the
rules are auditable and the interviewer can see exactly what "correct" means.

### Match classification

`correct · wrong · false_positive · false_negative · missing` — per field, so
`report.py` can print a per-field mismatch table for any pipeline on demand.

---

## 7. Folder layout & module responsibilities

Absolute imports from the `src/` root (e.g. `from domain.document import ...`).
No barrel/`__init__` re-exports; Python namespace packages. <200 lines/file.
Folders only where volume justifies them (`domain`, `eval`); single concerns
stay single files. No speculative folders.

```
src/
  domain/                  # pure value types — no I/O, no strategy deps  (folder: 4–5 modules)
    document.py            # ExtractedDocument, ExtractedPage, Word, FormField, RenderedPage, BBox
    extraction_result.py   # FieldValue, ExtractionResult
    field_catalog.py       # FieldSpec, build_catalog() — introspects the K-1 pydantic models
    scoring.py             # MatchKind, FieldComparison, DocumentScore, PipelineScore, MatrixReport
  eval/                    # the tester (folder: 5 modules) — see §6
    eval_set.py · normalize.py · scorer.py · runner.py · report.py
  ports.py                 # ExtractionStrategy, AnalysisStrategy, LlmClient Protocols ("the boundaries")
  registry.py              # name→factory maps + Pipeline + build_matrix(); add a strategy in ONE line
  config.py                # Settings + load_settings() factory; all tunables, no magic numbers
  logger.py                # make_logger(tag) — the only logging entry point
```

Eventually these ones they have strategies:
```
src/extraction/   # promoted to a folder when the first ExtractionStrategy lands
src/analysis/     # promoted to a folder when the first AnalysisStrategy lands
```

`Pipeline` (an extraction+analysis pair with a `.run()` and a `.name`) is a tiny
composition type; it lives in `registry.py` next to `build_matrix()` rather than
in its own folder.

Boundary direction: `domain` depends on nothing. `ports` depends on `domain`.
`registry`, `eval`, and concrete strategies depend on `ports` + `domain`. The
Gemini SDK lives only behind the `LlmClient` adapter (added with the first LLM
strategy), never imported by domain/ports.

---

